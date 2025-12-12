# -*- coding: utf-8 -*-
"""
Build a Text-to-SQL agent with LangGraph:
- preprocess: get schema, perform schema linking, retrieve example values
- subproblem: decompose the question into subproblems
- sql_plan: SQL query plan (COT)
- generate_sql: generate SQL draft
- validate_sql: execute and validate SQL
- correction_plan: correction plan (COT)
- correction_sql: corrected SQL
"""
from __future__ import annotations
import json
from typing import Any, Dict, List
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from .config import SETTINGS
from .llm import chat
from .prompts import (SYSTEM_PROMPT,
                     GENERATE_SQL_PROMPT,
                     SUBPROBLEM_PROMPT, SQL_PLAN_PROMPT, 
                     CORRECTION_PLAN_PROMPT, CORRECTION_SQL_PROMPT,
                     SEMANTIC_VALIDATE_PROMPT)
from .tools import get_database_schema, schema_linker, content_retriever, semantic_validator, sql_executor


class AgentState(BaseModel):
    # Inputs
    question: str
    db_id: str

    # Database schema information
    db_schema: str = ""  # Full CREATE TABLE statements.
    relevant_schema: str = ""  # Relevant tables/columns after schema linking.
    retrieved_values: List[str] = Field(default_factory=list)  # Example values.

    # New: subproblem decomposition and planning
    subproblems: str = ""  # Subproblem decomposition result (JSON string).
    sql_plan: str = ""  # SQL query plan (COT reasoning + FINAL_PLAN section).
    correction_plan: str = ""  # Correction plan (COT reasoning + CORRECTION_PLAN section).

    # SQL generation and validation
    sql_draft: str = ""  # Current SQL draft.
    sql_nl_explanation: str = ""  # SQL→Text natural language explanation (back-translation).
    semantic_validation: Dict[str, Any] = Field(default_factory=dict)  # Semantic validation result.
    execution_result: Dict[str, Any] = Field(default_factory=dict)  # Execution result or error.
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)  # Revision history.
    correction_history: List[Dict[str, Any]] = Field(default_factory=list)  # Correction history (error, plan, corrected SQL).
    final_sql: str = ""  # Final accepted SQL.

    # Control and diagnostics
    max_revisions: int = 3  # Maximum number of revisions.
    messages: List[Dict[str, Any]] = Field(default_factory=list)  # Message history with the LLM.
    step_trace: List[str] = Field(default_factory=list)  # Step-level trace.

    # Paths
    data_dir: str = "data/database"  # Directory of database files.

    # Backwards-compatible field (kept for tools/migration)
    schema_info: Dict[str, Any] = Field(default_factory=dict)  # Spider schema info.




def preprocess_node(state: AgentState) -> AgentState:
    """Preprocessing: get schema, perform schema linking, retrieve example values."""
    if True:
        print("\n📋 Preprocessing stage - Preprocess")

    # Step 1: get full database schema
    if True:
        print("  🔧 Getting database schema...")
    result = get_database_schema(state.db_id, state.schema_info)
    if result["status"] == "ok":
        state.db_schema = result["db_schema"]
        if True:
            print(f"  ✓ Successfully retrieved schema for {result.get('table_count', 0)} tables")
    else:
        state.step_trace.append(f"Error: {result.get('error')}")
        return state
    
    # Step 2: schema linking
    if True:
        print("  🔧 Performing schema linking to select relevant tables...")
    result = schema_linker(state.question, state.db_schema, state.schema_info)
    if result["status"] == "ok":
        state.relevant_schema = result["relevant_schema"]
        if True:
            print(f"  ✓ Selected relevant tables: {result.get('relevant_tables', [])}")
            print(f"  Rationale: {result.get('rationale', '')}")

    # Step 3: retrieve example values
    if True:
        print("  🔧 Retrieving example values...")
    result = content_retriever(state.question, state.relevant_schema, state.db_id, data_dir=state.data_dir)
    if result["status"] == "ok":
        state.retrieved_values = result["retrieved_values"]
        if True:
            print(f"  ✓ Retrieved {len(state.retrieved_values)} example values")
            if state.retrieved_values:
                print(f"  Examples: {state.retrieved_values[:3]}")

    # Step 4: additional info (via RAG or other mechanisms)
    # Domain knowledge, formulas/format hints to assist NL→SQL alignment (extensible).

    state.step_trace.append("preprocess_completed")
    return state


def subproblem_node(state: AgentState) -> AgentState:
    """Subproblem decomposition: break the question into SQL-friendly subproblems."""
    if True:
        print("\n🔍 Subproblem decomposition stage - Subproblem Decomposition")

    # Build subproblem decomposition prompt
    prompt = SUBPROBLEM_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # Call LLM to decompose into subproblems
    resp = chat(messages=messages, tools=None, temperature=0.1)
    content = resp.get("content", "").strip()
    
    # Clean JSON output (remove markdown markers)
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    state.subproblems = content
    state.step_trace.append(f"subproblems_identified")

    if True:
        print(f"  ✓ Subproblem decomposition completed")
        # Try to parse and show subproblem count
        try:
            import json
            subprob_data = json.loads(content)
            if "subproblems" in subprob_data:
                print(f"  Identified {len(subprob_data['subproblems'])} subproblems")
        except:
            pass
    
    return state


def sql_plan_node(state: AgentState) -> AgentState:
    """SQL planning stage: use COT to generate a query plan."""
    if True:
        print("\n📝 SQL planning stage - SQL Plan (COT)")

    # Build SQL plan prompt
    prompt = SQL_PLAN_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        retrieved_values=", ".join(state.retrieved_values) if state.retrieved_values else "none",
        subproblems=state.subproblems or "none"
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # Call LLM to generate the plan
    resp = chat(messages=messages, tools=None, temperature=0.1)
    plan = resp.get("content", "").strip()
    
    state.sql_plan = plan
    state.step_trace.append(f"sql_plan_created")

    if True:
        print(f"  ✓ SQL plan generated")
        # Extract and display FINAL_PLAN section
        if "FINAL_PLAN:" in plan:
            final_plan_start = plan.index("FINAL_PLAN:")
            final_plan = plan[final_plan_start:final_plan_start+200]
            print(f"  Plan summary: {final_plan[:150]}...")
    
    return state


def generate_sql_node(state: AgentState) -> AgentState:
    """SQL generation stage: generate SQL based on plan and preprocessing."""
    if True:
        print("\n🔨 SQL generation stage - Generate SQL")

    # Build generation prompt (now based on the SQL plan)
    prompt = GENERATE_SQL_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        retrieved_values=", ".join(state.retrieved_values) if state.retrieved_values else "none"
    )
    
    # If there is a SQL plan, prepend it to the prompt
    if state.sql_plan:
        prompt = f"SQL query plan:\n{state.sql_plan}\n\n{prompt}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # Call LLM to generate SQL
    resp = chat(messages=messages, tools=None, temperature=0.1)
    sql = resp.get("content", "").strip()
    
    # Clean SQL (strip markdown code fences)
    if sql.startswith("```sql"):
        sql = sql[6:]
    if sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    sql = sql.strip()
    
    state.sql_draft = sql
    state.step_trace.append(f"sql_generated: {sql[:100]}")

    if True:
        print(f"  ✓ Generated SQL: {sql}")
    
    return state


def validate_sql_node(state: AgentState) -> AgentState:
    """SQL validation: semantic validation + execution validation (two phases)."""
    if True:
        print("\n✅ SQL validation stage - Validate SQL")

    if not state.sql_draft:
        state.execution_result = {"status": "error", "error": "No SQL to execute"}
        return state
    
    # ========== Phase 1: semantic validation (tool call) ==========
    if True:
        print("  🔍 Semantic validation...")
    
    semantic_result = semantic_validator(
        question=state.question,
        sql_draft=state.sql_draft,
        relevant_schema=state.relevant_schema or state.db_schema
    )
    
    # Handle semantic validation result
    if semantic_result["status"] == "ok":
        state.sql_nl_explanation = semantic_result.get("explanation", "")
        state.semantic_validation = {
            "semantic_match": semantic_result.get("semantic_match", True),
            "issues": semantic_result.get("issues", [])
        }

        if True:
            if state.semantic_validation["semantic_match"]:
                print(f"  ✓ Semantic validation passed")
                if state.sql_nl_explanation:
                    print(f"  SQL explanation: {state.sql_nl_explanation[:100]}...")
            else:
                print(f"  ✗ Semantic validation failed")
                if state.sql_nl_explanation:
                    print(f"  SQL explanation: {state.sql_nl_explanation[:100]}...")
                print(f"  Issues found: {len(state.semantic_validation['issues'])}")
                for issue in state.semantic_validation["issues"][:3]:
                    print(f"    - [{issue.get('type', 'unknown')}] {issue.get('description', '')}")
    else:
        # Semantic validator failed; degrade to pass-through
        if True:
            print(f"  ⚠️  Semantic validator call failed, defaulting to pass: {semantic_result.get('error', '')}")
        state.semantic_validation = {
            "semantic_match": True,
            "issues": []
        }

    state.step_trace.append(f"semantic_validation: {state.semantic_validation['semantic_match']}")

    # If semantic validation failed, skip execution and go to correction
    if not state.semantic_validation.get("semantic_match", True):
        if True:
            print(f"  ⚠️  Semantic validation failed, skipping execution")
        state.execution_result = {
            "status": "error",
            "error": "Semantic mismatch",
            "semantic_issues": state.semantic_validation.get("issues", [])
        }
        # Record into revision history
        state.revision_history.append({
            "sql": state.sql_draft,
            "result": state.execution_result,
            "iteration": len(state.revision_history) + 1,
            "validation_type": "semantic"
        })
        state.step_trace.append(f"validation: semantic_failed")
        return state

    # ========== Phase 2: execution validation ==========
    if True:
        print(f"\n  🔧 Execution validation...")

    # Execute SQL
    result = sql_executor(state.db_id, state.sql_draft, data_dir=state.data_dir)
    state.execution_result = result

    # Record into revision history
    state.revision_history.append({
        "sql": state.sql_draft,
        "result": result,
        "iteration": len(state.revision_history) + 1,
            "validation_type": "execution"
        })

    if True:
        if result["status"] == "ok":
            print(f"  ✓ Execution succeeded, returned {result.get('rowcount', 0)} rows")
        else:
            print(f"  ✗ Execution failed: {result.get('error', '')}")

    state.step_trace.append(f"validation: {result['status']}")
    return state


def correction_plan_node(state: AgentState) -> AgentState:
    """Correction-plan stage: use COT to analyze errors and generate a plan."""
    if True:
        print(f"\n🔧 Correction-plan stage - Correction Plan (iteration {len(state.revision_history)})")

    error_msg = state.execution_result.get("error", "Unknown error")

    # Build semantic-issues text
    semantic_issues_text = ""
    if state.semantic_validation.get("issues"):
        semantic_issues_text = "\n\n**Issues found by semantic validation:**\n"
        for issue in state.semantic_validation["issues"]:
            semantic_issues_text += f"- [{issue.get('type', 'unknown')}] {issue.get('description', '')}\n"
        if state.sql_nl_explanation:
            semantic_issues_text += f"\nNatural language explanation of the SQL: {state.sql_nl_explanation}\n"

    # Build correction-history text
    history_text = ""
    if state.correction_history:
        history_text = "\n\n**Previous correction history (learn from it and avoid repeating mistakes):**\n"
        for i, record in enumerate(state.correction_history, 1):
            history_text += f"\n--- Correction #{i} ---\n"
            history_text += f"Erroneous SQL: {record.get('sql', '')}\n"
            history_text += f"Error message: {record.get('error', '')}\n"
            history_text += f"Correction plan: {record.get('plan', '')[:200]}...\n"
            if record.get('corrected_sql'):
                history_text += f"Corrected SQL: {record.get('corrected_sql', '')}\n"

    # Build correction-plan prompt
    prompt = CORRECTION_PLAN_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        sql_draft=state.sql_draft,
        error=error_msg,
        semantic_issues=semantic_issues_text,
        correction_history=history_text
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    # Call LLM to generate the correction plan
    resp = chat(messages=messages, tools=None, temperature=0.1)
    plan = resp.get("content", "").strip()
    
    state.correction_plan = plan
    state.step_trace.append(f"correction_plan_created")

    if True:
        print(f"  ✓ Correction plan generated")
        # Extract and display CORRECTION_PLAN section
        if "CORRECTION_PLAN:" in plan:
            correction_plan_start = plan.index("CORRECTION_PLAN:")
            correction_plan = plan[correction_plan_start:correction_plan_start+200]
            print(f"  Plan summary: {correction_plan[:150]}...")
    
    return state


def correction_sql_node(state: AgentState) -> AgentState:
    """Correction-SQL stage: generate corrected SQL based on the correction plan."""
    if True:
        print(f"\n🔨 Correction-SQL stage - Correction SQL")

    # Preserve current correction context (before generating new SQL)
    old_sql = state.sql_draft
    old_error = state.execution_result.get("error", "Unknown error")

    # Build correction-SQL prompt
    prompt = CORRECTION_SQL_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        sql_draft=state.sql_draft,
        correction_plan=state.correction_plan
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    # Call LLM to generate corrected SQL
    resp = chat(messages=messages, tools=None, temperature=0.1)
    sql = resp.get("content", "").strip()
    
    # Clean SQL
    if sql.startswith("```sql"):
        sql = sql[6:]
    if sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    sql = sql.strip()
    
    # Record correction history
    state.correction_history.append({
        "iteration": len(state.correction_history) + 1,
        "sql": old_sql,
        "error": old_error,
        "plan": state.correction_plan,
        "corrected_sql": sql
    })

    state.sql_draft = sql
    state.step_trace.append(f"sql_corrected: {sql[:100]}")

    if True:
        print(f"  ✓ Corrected SQL: {sql}")
        print(f"  📝 Recorded {len(state.correction_history)} correction iterations")
    
    return state


def decide_next_step(state: AgentState) -> str:
    """Conditional routing: decide whether to revise, finalize, or stop."""
    result = state.execution_result

    # Check whether maximum revision count has been reached
    if len(state.revision_history) >= state.max_revisions:
        if True:
            print(f"\n⚠️  Reached maximum number of revisions ({state.max_revisions}); accepting current SQL")
        return "finalize"

    # If execution failed, go to correction
    if result.get("status") == "error":
        return "correction_plan"  # From previous 'revise' to 'correction_plan'.

    # If result set is empty, try a single correction
    if result.get("status") == "ok" and result.get("rowcount", 0) == 0:
        # Check whether we already revised once for empty result
        if len(state.revision_history) == 1:
            if True:
                print("\n⚠️  Result is empty, trying a correction...")
            return "correction_plan"  # From previous 'revise' to 'correction_plan'.
        else:
            # Already revised, accept the empty result
            if True:
                print("\n✓ Accepting empty result (may be correct)")
            return "finalize"

    # If execution succeeded and has rows, accept
    if result.get("status") == "ok" and result.get("rowcount", 0) > 0:
        if True:
            print("\n✅ SQL validation succeeded; accepting result")
        return "finalize"

    # Default: finalize
    return "finalize"


def finalize_node(state: AgentState) -> AgentState:
    """Finalize node: set final_sql from the last draft."""
    state.final_sql = state.sql_draft
    return state


def build_graph():
    """Build and compile the LangGraph state machine.

    Flow:
        preprocess -> subproblem -> sql_plan -> generate_sql -> validate_sql
        -> (correction_plan -> correction_sql -> validate_sql)* -> finalize -> END
    """
    g = StateGraph(AgentState)

    # Add nodes
    g.add_node("preprocess", preprocess_node)
    g.add_node("subproblem", subproblem_node)
    g.add_node("sql_plan", sql_plan_node)
    g.add_node("generate_sql", generate_sql_node)
    g.add_node("validate_sql", validate_sql_node)
    g.add_node("correction_plan", correction_plan_node)
    g.add_node("correction_sql", correction_sql_node)
    g.add_node("finalize", finalize_node)

    # Main flow edges
    g.add_edge(START, "preprocess")
    g.add_edge("preprocess", "subproblem")
    g.add_edge("subproblem", "sql_plan")
    g.add_edge("sql_plan", "generate_sql")
    g.add_edge("generate_sql", "validate_sql")

    # Conditional routing after validation: either correct or finalize
    g.add_conditional_edges(
        "validate_sql",
        decide_next_step,
        {
            "correction_plan": "correction_plan",
            "finalize": "finalize"
        }
    )

    # Correction loop: correction_plan -> correction_sql -> validate_sql
    g.add_edge("correction_plan", "correction_sql")
    g.add_edge("correction_sql", "validate_sql")

    # Finalize then END
    g.add_edge("finalize", END)

    return g.compile()
