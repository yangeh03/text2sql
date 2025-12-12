# -*- coding: utf-8 -*-
"""
Implementations of all tools:
1. get_database_schema - Get the full database schema.
2. schema_linker - Schema linking, select relevant tables (LLM-based).
3. content_retriever - Retrieve example values (LLM-based, plus DB lookup).
4. semantic_validator - SQL semantic validation (SQL→Text back-translation).
5. sql_executor - Execute SQL queries.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
import re


def get_database_schema(db_id: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 1: Get the full database schema (CREATE TABLE statements).

    Input: db_id - database ID.
    Output: { status: "ok", db_schema: str } or { status: "error", error: str }.
    """
    try:
        if not db_id or not schema_info:
            return {"status": "error", "error": "Missing db_id or schema_info"}
        
        # Extract table and column information
        tables = schema_info.get('table_names_original', [])
        columns = schema_info.get('column_names_original', [])
        column_types = schema_info.get('column_types', [])
        primary_keys = schema_info.get('primary_keys', [])
        foreign_keys = schema_info.get('foreign_keys', [])

        if not tables:
            return {"status": "error", "error": "Database schema is empty"}
        
        # Build CREATE TABLE statements
        create_statements = []
        for table_idx, table_name in enumerate(tables):
            cols = []
            for col_idx, (col_table_idx, col_name) in enumerate(columns):
                if col_table_idx == table_idx:
                    col_type = column_types[col_idx] if col_idx < len(column_types) else "TEXT"
                    is_pk = col_idx in primary_keys
                    pk_marker = " PRIMARY KEY" if is_pk else ""
                    cols.append(f"  {col_name} {col_type}{pk_marker}")
            
            # Add foreign key constraints
            fk_constraints = []
            for fk_pair in foreign_keys:
                if len(fk_pair) == 2:
                    from_col_idx, to_col_idx = fk_pair
                    if from_col_idx < len(columns) and to_col_idx < len(columns):
                        from_table_idx, from_col = columns[from_col_idx]
                        to_table_idx, to_col = columns[to_col_idx]
                        if from_table_idx == table_idx:
                            ref_table = tables[to_table_idx]
                            fk_constraints.append(f"  FOREIGN KEY ({from_col}) REFERENCES {ref_table}({to_col})")
            
            all_definitions = cols + fk_constraints
            create_stmt = f"CREATE TABLE {table_name} (\n" + ",\n".join(all_definitions) + "\n);"
            create_statements.append(create_stmt)
        
        db_schema = "\n\n".join(create_statements)

        return {
            "status": "ok",
            "db_schema": db_schema,
            "table_count": len(tables)
        }

    except Exception as e:
        return {"status": "error", "error": f"Failed to get database schema: {str(e)}"}


def schema_linker(question: str, db_schema: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 2: Schema linking - select relevant tables and columns from the full schema (LLM-based).

    Uses the LLM and SCHEMA_LINKER_PROMPT_TEMPLATE to identify relevant tables and columns,
    and returns a pruned schema string (only the relevant CREATE TABLE statements).

    Input: question - natural language question, db_schema - full schema.
    Output: { status: "ok", relevant_schema: str, relevant_tables: list, rationale: str }.
    """
    try:
        if not question or not db_schema:
            return {"status": "error", "error": "Question or schema is empty"}

        # Import LLM and prompt
        from .llm import chat
        from .prompts import SCHEMA_LINKER_PROMPT_TEMPLATE

        # Build prompt
        prompt = SCHEMA_LINKER_PROMPT_TEMPLATE.format(
            question=question,
            db_schema=db_schema
        )
        
        # Call LLM
        messages = [{"role": "user", "content": prompt}]
        response = chat(messages, temperature=0.1)
        
        # Parse LLM output
        content = response.get("content", "").strip()
        
        # Try to parse JSON array
        try:
            # Extract JSON array (may be embedded in other text)
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                relevant_tables = json.loads(json_match.group())
            else:
                # If no explicit JSON array, try parsing the whole content
                relevant_tables = json.loads(content)
            
            # Ensure the result is a list
            if not isinstance(relevant_tables, list):
                relevant_tables = []
        except (json.JSONDecodeError, ValueError):
            # On parse failure, use a fallback strategy
            tables = schema_info.get('table_names_original', [])
            question_lower = question.lower()
            relevant_tables = []
            
            for table in tables:
                table_words = table.lower().replace('_', ' ').split()
                if any(word in question_lower for word in table_words):
                    relevant_tables.append(table)
            
            if not relevant_tables:
                relevant_tables = tables[:3]
        
        # If still no tables matched, use a default subset
        if not relevant_tables:
            tables = schema_info.get('table_names_original', [])
            relevant_tables = tables[:3]
            rationale = "LLM did not identify relevant tables; using the first few tables as candidates."
        else:
            rationale = f"LLM identified relevant tables: {', '.join(relevant_tables)}"

        # Extract CREATE TABLE statements for relevant tables
        relevant_schema_parts = []
        for line_block in db_schema.split("\n\n"):
            for table in relevant_tables:
                if f"CREATE TABLE {table}" in line_block:
                    relevant_schema_parts.append(line_block)
                    break
        
        relevant_schema = "\n\n".join(relevant_schema_parts) if relevant_schema_parts else db_schema

        return {
            "status": "ok",
            "relevant_schema": relevant_schema,
            "relevant_tables": relevant_tables,
            "rationale": rationale
        }

    except Exception as e:
        # Fallback: return full schema
        tables = schema_info.get('table_names_original', [])
        return {
            "status": "ok",
            "relevant_schema": db_schema,
            "relevant_tables": tables,
            "rationale": f"Schema linking failed; falling back to full schema: {str(e)}"
        }


def content_retriever(question: str, relevant_schema: str, db_id: str, 
                     data_dir: str = "data/database") -> Dict[str, Any]:
    """
    Tool 3: Retrieve example values from the database (LLM-based).

    Uses the LLM with CONTENT_RETRIEVER_PROMPT_TEMPLATE to identify key values in the question,
    then retrieves those values and related example data from the database.

    Input: question, relevant_schema, db_id.
    Output: { status: "ok", retrieved_values: list[str] }.
    """
    try:
        # Import LLM and prompt
        from .llm import chat
        from .prompts import CONTENT_RETRIEVER_PROMPT_TEMPLATE

        # 1. Use LLM to identify key values in the question
        prompt = CONTENT_RETRIEVER_PROMPT_TEMPLATE.format(
            question=question,
            relevant_schema=relevant_schema
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = chat(messages, temperature=0.1)

        # Parse LLM output
        content = response.get("content", "").strip()
        
        # Try to parse JSON array
        key_values = []
        try:
            # Extract JSON array
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                key_values = json.loads(json_match.group())
            else:
                key_values = json.loads(content)

            if not isinstance(key_values, list):
                key_values = []
        except (json.JSONDecodeError, ValueError):
            # On parse failure, extract quoted tokens from the question as key values
            key_values = re.findall(r'["\']([^"\']+)["\']', question)

        # 2. Retrieve example values from the database
        db_path = Path(data_dir) / db_id / f"{db_id}.sqlite"
        
        if not db_path.exists():
            return {
                "status": "ok",
                "retrieved_values": key_values if key_values else [],
                "message": "Database file does not exist; returning key values identified by the LLM."
            }

        # Connect to DB and retrieve example values
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        retrieved_values = []

        # Extract table names from the relevant schema
        table_pattern = r'CREATE TABLE (\w+)'
        tables = re.findall(table_pattern, relevant_schema)

        # For each table, execute a simple SELECT DISTINCT query
        for table in tables[:2]:  # limit to first 2 tables
            try:
                # Get the first text-like column
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                # Find the first text-like column
                text_col = None
                for col in columns:
                    col_name, col_type = col[1], col[2]
                    if 'TEXT' in col_type.upper() or 'VARCHAR' in col_type.upper() or 'CHAR' in col_type.upper():
                        text_col = col_name
                        break

                if text_col:
                    cursor.execute(f"SELECT DISTINCT {text_col} FROM {table} LIMIT 5")
                    # Ensure all values are converted to strings
                    values = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
                    retrieved_values.extend(values)
            except Exception:
                continue
        
        conn.close()

        # Merge LLM-recognized key values and DB-retrieved values
        all_values = key_values + retrieved_values
        all_values = [str(v) for v in all_values]
        unique_values = list(dict.fromkeys(all_values))  # de-duplicate while preserving order

        return {
            "status": "ok",
            "retrieved_values": unique_values[:10],  # return at most 10 example values
            "message": f"LLM identified {len(key_values)} key values; DB lookup returned {len(retrieved_values)} example values"
        }

    except Exception as e:
        return {
            "status": "ok",
            "retrieved_values": [],
            "message": f"Failed to retrieve example values: {str(e)}"
        }


def sql_executor(db_id: str, sql_query: str, 
                data_dir: str = "data/database",
                max_rows: int = 100,
                timeout: int = 10) -> Dict[str, Any]:
    """
    Tool 4: Execute an SQL query.

    Input: db_id, sql_query.
    Output: success -> { status: "ok", rows: list[tuple], rowcount: int }
            failure -> { status: "error", error: str }.
    """
    try:
        # Safety check: only allow SELECT queries
        sql_upper = sql_query.strip().upper()
        if not sql_upper.startswith('SELECT'):
            return {
                "status": "error",
                "error": "Only SELECT queries are allowed"
            }

        # Forbid dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        if any(keyword in sql_upper for keyword in dangerous_keywords):
            return {
                "status": "error",
                "error": "Query contains forbidden keywords"
            }

        # Build DB path
        db_path = Path(data_dir) / db_id / f"{db_id}.sqlite"
        
        if not db_path.exists():
            return {
                "status": "error",
                "error": f"Database file does not exist: {db_path}"
            }

        # Execute query
        conn = sqlite3.connect(str(db_path), timeout=timeout)
        cursor = conn.cursor()

        # Add LIMIT clause if the original query does not have one
        if 'LIMIT' not in sql_upper:
            sql_query = f"{sql_query.rstrip(';')} LIMIT {max_rows}"

        cursor.execute(sql_query)
        rows = cursor.fetchall()

        conn.close()

        return {
            "status": "ok",
            "rows": rows,
            "rowcount": len(rows),
            "message": f"Query succeeded, returned {len(rows)} rows"
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "error": f"SQL execution error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Execution failed: {str(e)}"
        }


def semantic_validator(question: str, sql_draft: str, relevant_schema: str) -> Dict[str, Any]:
    """
    Tool 5: SQL semantic validation (SQL→Text back-translation + semantic consistency check).

    Inspired by the GBV-SQL paper, this tool checks whether the
    semantics of the generated SQL match the natural language question
    via back-translation.

    Input: question - natural language question,
           sql_draft - generated SQL,
           relevant_schema - relevant database schema.
    Output: { status: "ok", explanation: str, semantic_match: bool, issues: list }.
    """
    try:
        # Import LLM client and prompts
        from .llm import chat
        from .prompts import SEMANTIC_VALIDATE_PROMPT, SYSTEM_PROMPT
        
        # Build semantic validation prompt
        prompt = SEMANTIC_VALIDATE_PROMPT.format(
            question=question,
            relevant_schema=relevant_schema,
            sql_draft=sql_draft
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM for semantic validation
        response = chat(messages=messages, tools=None, temperature=0.1)
        content = response.get("content", "").strip()
        
        # Clean JSON output (remove markdown markers)
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse semantic validation result
        try:
            validation_result = json.loads(content)
            return {
                "status": "ok",
                "explanation": validation_result.get("explanation", ""),
                "semantic_match": validation_result.get("semantic_match", True),
                "issues": validation_result.get("issues", [])
            }
        except (json.JSONDecodeError, ValueError) as e:
            # If parsing fails, assume semantic match
            return {
                "status": "ok",
                "explanation": content[:200] if content else "",
                "semantic_match": True,
                "issues": [],
                "parse_error": f"JSON parse failed: {str(e)}"
            }
    
    except Exception as e:
        # Semantic validation failed; treat as error but keep fields
        return {
            "status": "error",
            "error": f"Semantic validation failed: {str(e)}",
            "semantic_match": True,
            "issues": []
        }
