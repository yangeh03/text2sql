# -*- coding: utf-8 -*-
"""
所有工具实现：
1. get_database_schema - 获取完整数据库模式
2. schema_linker - 模式链接，筛选相关表（基于LLM）
3. content_retriever - 检索示例值（基于LLM）
4. semantic_validator - SQL语义验证（SQL→Text反向翻译）
5. sql_executor - 执行SQL查询
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
import re


def get_database_schema(db_id: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 1: 获取完整数据库模式（CREATE TABLE语句）
    
    输入：db_id - 数据库ID
    输出：{ status: "ok", db_schema: str } 或 { status: "error", error: str }
    """
    try:
        if not db_id or not schema_info:
            return {"status": "error", "error": "缺少 db_id 或 schema_info"}
        
        # 提取表和列信息
        tables = schema_info.get('table_names_original', [])
        columns = schema_info.get('column_names_original', [])
        column_types = schema_info.get('column_types', [])
        primary_keys = schema_info.get('primary_keys', [])
        foreign_keys = schema_info.get('foreign_keys', [])
        
        if not tables:
            return {"status": "error", "error": "数据库模式为空"}
        
        # 构建 CREATE TABLE 语句
        create_statements = []
        for table_idx, table_name in enumerate(tables):
            cols = []
            for col_idx, (col_table_idx, col_name) in enumerate(columns):
                if col_table_idx == table_idx:
                    col_type = column_types[col_idx] if col_idx < len(column_types) else "TEXT"
                    is_pk = col_idx in primary_keys
                    pk_marker = " PRIMARY KEY" if is_pk else ""
                    cols.append(f"  {col_name} {col_type}{pk_marker}")
            
            # 添加外键约束
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
        return {"status": "error", "error": f"获取数据库模式失败: {str(e)}"}


def schema_linker(question: str, db_schema: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 2: 模式链接 - 从完整模式中筛选相关表和列（基于LLM）
    
    使用 LLM 和 SCHEMA_LINKER_PROMPT_TEMPLATE 来识别相关表和列。
    返回精简后的 schema 字符串 (只包含相关的 CREATE TABLE 语句)。
    
    输入：question - 自然语言问题, db_schema - 完整模式
    输出：{ status: "ok", relevant_schema: str, relevant_tables: list, rationale: str }
    """
    try:
        if not question or not db_schema:
            return {"status": "error", "error": "问题或模式为空"}
        
        # 导入 LLM 和提示词
        from .llm import chat
        from .prompts import SCHEMA_LINKER_PROMPT_TEMPLATE
        
        # 构建 prompt
        prompt = SCHEMA_LINKER_PROMPT_TEMPLATE.format(
            question=question,
            db_schema=db_schema
        )
        
        # 调用 LLM
        messages = [{"role": "user", "content": prompt}]
        response = chat(messages, temperature=0.1)
        
        # 解析 LLM 输出
        content = response.get("content", "").strip()
        
        # 尝试解析 JSON 数组
        try:
            # 提取 JSON 数组（可能包含在其他文本中）
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                relevant_tables = json.loads(json_match.group())
            else:
                # 如果没有找到 JSON，尝试直接解析
                relevant_tables = json.loads(content)
            
            # 确保是列表
            if not isinstance(relevant_tables, list):
                relevant_tables = []
        except (json.JSONDecodeError, ValueError):
            # 解析失败，使用降级策略
            tables = schema_info.get('table_names_original', [])
            question_lower = question.lower()
            relevant_tables = []
            
            for table in tables:
                table_words = table.lower().replace('_', ' ').split()
                if any(word in question_lower for word in table_words):
                    relevant_tables.append(table)
            
            if not relevant_tables:
                relevant_tables = tables[:3]
        
        # 如果没有匹配到任何表，使用降级策略
        if not relevant_tables:
            tables = schema_info.get('table_names_original', [])
            relevant_tables = tables[:3]
            rationale = "LLM未识别到相关表，使用前几个表作为候选"
        else:
            rationale = f"LLM识别出相关表：{', '.join(relevant_tables)}"
        
        # 从完整模式中提取相关表的 CREATE TABLE 语句
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
        # 降级：返回完整模式
        tables = schema_info.get('table_names_original', [])
        return {
            "status": "ok",
            "relevant_schema": db_schema,
            "relevant_tables": tables,
            "rationale": f"模式链接出错，降级使用完整模式: {str(e)}"
        }


def content_retriever(question: str, relevant_schema: str, db_id: str, 
                     data_dir: str = "data/database") -> Dict[str, Any]:
    """
    Tool 3: 从数据库中检索示例值（基于LLM）
    
    使用 LLM 和 CONTENT_RETRIEVER_PROMPT_TEMPLATE 识别问题中的关键值。
    然后从数据库中检索这些值及相关的示例数据。
    
    输入：question, relevant_schema, db_id
    输出：{ status: "ok", retrieved_values: list[str] }
    """
    try:
        # 导入 LLM 和提示词
        from .llm import chat
        from .prompts import CONTENT_RETRIEVER_PROMPT_TEMPLATE
        
        # 1. 使用 LLM 识别问题中的关键值
        prompt = CONTENT_RETRIEVER_PROMPT_TEMPLATE.format(
            question=question,
            relevant_schema=relevant_schema
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = chat(messages, temperature=0.1)
        
        # 解析 LLM 输出
        content = response.get("content", "").strip()
        
        # 尝试解析 JSON 数组
        key_values = []
        try:
            # 提取 JSON 数组
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                key_values = json.loads(json_match.group())
            else:
                key_values = json.loads(content)
            
            if not isinstance(key_values, list):
                key_values = []
        except (json.JSONDecodeError, ValueError):
            # 解析失败，提取引号中的词作为关键值
            key_values = re.findall(r'["\']([^"\']+)["\']', question)
        
        # 2. 从数据库中检索示例值
        db_path = Path(data_dir) / db_id / f"{db_id}.sqlite"
        
        if not db_path.exists():
            return {
                "status": "ok",
                "retrieved_values": key_values if key_values else [],
                "message": f"数据库文件不存在，返回LLM识别的关键值"
            }
        
        # 连接数据库并检索示例值
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        retrieved_values = []
        
        # 从相关模式中提取表名
        table_pattern = r'CREATE TABLE (\w+)'
        tables = re.findall(table_pattern, relevant_schema)
        
        # 对每个表执行简单的 SELECT DISTINCT 查询
        for table in tables[:2]:  # 限制查询前2个表
            try:
                # 获取表的第一个文本列
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                # 找第一个文本类型的列
                text_col = None
                for col in columns:
                    col_name, col_type = col[1], col[2]
                    if 'TEXT' in col_type.upper() or 'VARCHAR' in col_type.upper() or 'CHAR' in col_type.upper():
                        text_col = col_name
                        break
                
                if text_col:
                    cursor.execute(f"SELECT DISTINCT {text_col} FROM {table} LIMIT 5")
                    # 确保所有值都转换为字符串
                    values = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
                    retrieved_values.extend(values)
            except Exception:
                continue
        
        conn.close()
        
        # 合并 LLM 识别的关键值和数据库检索的值
        all_values = key_values + retrieved_values
        # 确保所有值都是字符串类型
        all_values = [str(v) for v in all_values]
        unique_values = list(dict.fromkeys(all_values))  # 去重但保持顺序
        
        return {
            "status": "ok",
            "retrieved_values": unique_values[:10],  # 最多返回10个示例值
            "message": f"LLM识别{len(key_values)}个关键值，数据库检索{len(retrieved_values)}个示例值"
        }
    
    except Exception as e:
        return {
            "status": "ok",
            "retrieved_values": [],
            "message": f"检索示例值失败: {str(e)}"
        }


def sql_executor(db_id: str, sql_query: str, 
                data_dir: str = "data/database",
                max_rows: int = 100,
                timeout: int = 10) -> Dict[str, Any]:
    """
    Tool 4: 执行SQL查询
    
    输入：db_id, sql_query
    输出：成功: { status: "ok", rows: list[tuple], rowcount: int }
         失败: { status: "error", error: str }
    """
    try:
        # 安全检查：只允许SELECT查询
        sql_upper = sql_query.strip().upper()
        if not sql_upper.startswith('SELECT'):
            return {
                "status": "error",
                "error": "只允许执行 SELECT 查询"
            }
        
        # 禁止危险操作
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        if any(keyword in sql_upper for keyword in dangerous_keywords):
            return {
                "status": "error",
                "error": f"查询包含禁止的关键词"
            }
        
        # 构建数据库路径
        db_path = Path(data_dir) / db_id / f"{db_id}.sqlite"
        
        if not db_path.exists():
            return {
                "status": "error",
                "error": f"数据库文件不存在: {db_path}"
            }
        
        # 执行查询
        conn = sqlite3.connect(str(db_path), timeout=timeout)
        cursor = conn.cursor()
        
        # 添加 LIMIT 限制（如果原查询没有）
        if 'LIMIT' not in sql_upper:
            sql_query = f"{sql_query.rstrip(';')} LIMIT {max_rows}"
        
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        conn.close()
        
        return {
            "status": "ok",
            "rows": rows,
            "rowcount": len(rows),
            "message": f"查询成功，返回 {len(rows)} 行"
        }
    
    except sqlite3.Error as e:
        return {
            "status": "error",
            "error": f"SQL执行错误: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"执行失败: {str(e)}"
        }


def semantic_validator(question: str, sql_draft: str, relevant_schema: str) -> Dict[str, Any]:
    """
    Tool 5: SQL语义验证（SQL→Text反向翻译 + 语义一致性判断）
    
    基于GBV-SQL论文思想，通过反向翻译检查SQL语义是否与问题一致
    
    输入：question - 自然语言问题, sql_draft - 生成的SQL, relevant_schema - 相关模式
    输出：{ status: "ok", explanation: str, semantic_match: bool, issues: list }
    """
    try:
        # 导入LLM和提示词
        from .llm import chat
        from .prompts import SEMANTIC_VALIDATE_PROMPT, SYSTEM_PROMPT
        
        # 构建语义验证提示
        prompt = SEMANTIC_VALIDATE_PROMPT.format(
            question=question,
            relevant_schema=relevant_schema,
            sql_draft=sql_draft
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        # 调用LLM进行语义验证
        response = chat(messages=messages, tools=None, temperature=0.1)
        content = response.get("content", "").strip()
        
        # 清理JSON（移除markdown标记）
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # 解析语义验证结果
        try:
            validation_result = json.loads(content)
            return {
                "status": "ok",
                "explanation": validation_result.get("explanation", ""),
                "semantic_match": validation_result.get("semantic_match", True),
                "issues": validation_result.get("issues", [])
            }
        except (json.JSONDecodeError, ValueError) as e:
            # 解析失败，假设语义一致
            return {
                "status": "ok",
                "explanation": content[:200] if content else "",
                "semantic_match": True,
                "issues": [],
                "parse_error": f"JSON解析失败: {str(e)}"
            }
    
    except Exception as e:
        # 验证失败，降级为通过
        return {
            "status": "error",
            "error": f"语义验证失败: {str(e)}",
            "semantic_match": True,
            "issues": []
        }
