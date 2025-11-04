# -*- coding: utf-8 -*-
"""
用 LangGraph 搭建 Text-to-SQL ReAct Agent：
- preprocess: 获取schema、模式链接、检索示例值
- generate_sql: 生成SQL草稿
- validate_sql: 执行SQL并验证
- revise_sql: 根据错误修正SQL
"""
from __future__ import annotations
import json
from typing import Any, Dict, List
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from .config import SETTINGS
from .llm import chat
from .prompts import (SYSTEM_PROMPT, PREPROCESS_TOOLS, EXECUTION_TOOLS,
                     PREPROCESS_PROMPT, GENERATE_SQL_PROMPT, REVISE_SQL_PROMPT)
from .tools import get_database_schema, schema_linker, content_retriever, sql_executor


class AgentState(BaseModel):
    # 输入
    question: str
    db_id: str
    
    # 数据库模式信息
    db_schema: str = ""  # 完整的 CREATE TABLE 语句
    relevant_schema: str = ""  # 模式链接后筛选的相关表和列
    retrieved_values: List[str] = Field(default_factory=list)  # 示例值
    
    # SQL 生成与验证
    sql_draft: str = ""  # 当前 SQL 草稿
    execution_result: Dict[str, Any] = Field(default_factory=dict)  # 执行结果或错误
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)  # 修订历史
    final_sql: str = ""  # 最终接受的 SQL
    
    # 控制与诊断
    max_revisions: int = 3  # 最大修订次数
    messages: List[Dict[str, Any]] = Field(default_factory=list)  # 与 LLM 的消息历史
    step_trace: List[str] = Field(default_factory=list)  # 步骤日志
    
    # 路径配置
    data_dir: str = "data/database"  # 数据库文件目录
    
    # 兼容旧字段（可选，用于迁移）
    schema_info: Dict[str, Any] = Field(default_factory=dict)  # Spider schema信息（保留用于工具）




def preprocess_node(state: AgentState) -> AgentState:
    """预处理阶段：获取schema、模式链接、检索示例值"""
    if True:
        print("\n📋 预处理阶段 - Preprocess")
    
    # Step 1: 获取完整数据库模式
    if True:
        print("  🔧 获取数据库模式...")
    result = get_database_schema(state.db_id, state.schema_info)
    if result["status"] == "ok":
        state.db_schema = result["db_schema"]
        if True:
            print(f"  ✓ 成功获取 {result.get('table_count', 0)} 个表的模式")
    else:
        state.step_trace.append(f"Error: {result.get('error')}")
        return state
    
    # Step 2: 模式链接
    if True:
        print("  🔧 模式链接，筛选相关表...")
    result = schema_linker(state.question, state.db_schema, state.schema_info)
    if result["status"] == "ok":
        state.relevant_schema = result["relevant_schema"]
        if True:
            print(f"  ✓ 筛选出相关表: {result.get('relevant_tables', [])}")
            print(f"  理由: {result.get('rationale', '')}")
    
    # Step 3: 检索示例值
    if True:
        print("  🔧 检索示例值...")
    result = content_retriever(state.question, state.relevant_schema, state.db_id, data_dir=state.data_dir)
    if result["status"] == "ok":
        state.retrieved_values = result["retrieved_values"]
        if True:
            print(f"  ✓ 检索到 {len(state.retrieved_values)} 个示例值")
            if state.retrieved_values:
                print(f"  示例: {state.retrieved_values[:3]}")

    # Step 4:额外信息获取（Additional Info via RAG）
    # 检示例、领域知识、公式/格式提示，辅助 NL→SQL 对齐（可拓展）
    
    state.step_trace.append("preprocess_completed")
    return state


def generate_sql_node(state: AgentState) -> AgentState:
    """SQL生成阶段：基于预处理结果生成SQL"""
    if True:
        print("\n🔨 SQL生成阶段 - Generate SQL")
    
    # 构建生成提示
    prompt = GENERATE_SQL_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        retrieved_values=", ".join(state.retrieved_values) if state.retrieved_values else "无"
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # 调用LLM生成SQL
    resp = chat(messages=messages, tools=None, temperature=0.1)
    sql = resp.get("content", "").strip()
    
    # 清理SQL（移除markdown代码块标记）
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
        print(f"  ✓ 生成SQL: {sql}")
    
    return state


def validate_sql_node(state: AgentState) -> AgentState:
    """SQL验证阶段：执行SQL并记录结果"""
    if True:
        print("\n✅ SQL验证阶段 - Validate SQL")
    
    if not state.sql_draft:
        state.execution_result = {"status": "error", "error": "没有SQL可执行"}
        return state
    
    # 执行SQL
    result = sql_executor(state.db_id, state.sql_draft, data_dir=state.data_dir)
    state.execution_result = result
    
    # 记录到修订历史
    state.revision_history.append({
        "sql": state.sql_draft,
        "result": result,
        "iteration": len(state.revision_history) + 1
    })
    
    if True:
        if result["status"] == "ok":
            print(f"  ✓ 执行成功，返回 {result.get('rowcount', 0)} 行")
        else:
            print(f"  ✗ 执行失败: {result.get('error', '')}")
    
    state.step_trace.append(f"validation: {result['status']}")
    return state


def revise_sql_node(state: AgentState) -> AgentState:
    """SQL修订阶段：根据错误修正SQL"""
    if True:
        print(f"\n🔧 SQL修订阶段 - Revise SQL (第 {len(state.revision_history)} 次)")
    
    error_msg = state.execution_result.get("error", "未知错误")
    
    # 构建修订提示
    prompt = REVISE_SQL_PROMPT.format(
        sql_draft=state.sql_draft,
        error=error_msg
    )
    
    # 添加上下文
    full_prompt = (
        f"问题: {state.question}\n\n"
        f"相关表结构:\n{state.relevant_schema or state.db_schema}\n\n"
        f"{prompt}"
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": full_prompt}
    ]
    
    # 调用LLM修订SQL
    resp = chat(messages=messages, tools=None, temperature=0.1)
    sql = resp.get("content", "").strip()
    
    # 清理SQL
    if sql.startswith("```sql"):
        sql = sql[6:]
    if sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    sql = sql.strip()
    
    state.sql_draft = sql
    state.step_trace.append(f"sql_revised: {sql[:100]}")
    
    if True:
        print(f"  ✓ 修订后SQL: {sql}")
    
    return state


def decide_next_step(state: AgentState) -> str:
    """条件路由：决定下一步是修订、结束还是继续"""
    result = state.execution_result
    
    # 检查是否达到最大修订次数
    if len(state.revision_history) >= state.max_revisions:
        if True:
            print(f"\n⚠️  已达到最大修订次数 ({state.max_revisions})，接受当前SQL")
        return "finalize"
    
    # 如果执行失败，进行修订
    if result.get("status") == "error":
        return "revise"
    
    # 如果返回空结果，也尝试修订（但只修订一次）
    if result.get("status") == "ok" and result.get("rowcount", 0) == 0:
        # 检查是否已经修订过空结果
        if len(state.revision_history) == 1:
            if True:
                print("\n⚠️  结果为空，尝试修订...")
            return "revise"
        else:
            # 已经修订过，接受空结果
            if True:
                print("\n✓ 接受空结果（可能是正确的）")
            return "finalize"
    
    # 如果成功且有数据，接受
    if result.get("status") == "ok" and result.get("rowcount", 0) > 0:
        if True:
            print("\n✅ SQL验证成功，接受结果")
        return "finalize"
    
    # 默认结束
    return "finalize"


def finalize_node(state: AgentState) -> AgentState:
    """最终化节点：设置 final_sql"""
    state.final_sql = state.sql_draft
    return state


def build_graph():
    """构建LangGraph状态图：preprocess -> generate -> validate -> (revise -> validate)* -> finalize -> end"""
    g = StateGraph(AgentState)
    
    # 添加节点
    g.add_node("preprocess", preprocess_node)
    g.add_node("generate_sql", generate_sql_node)
    g.add_node("validate_sql", validate_sql_node)
    g.add_node("revise_sql", revise_sql_node)
    g.add_node("finalize", finalize_node)
    
    # 定义边
    g.add_edge(START, "preprocess")
    g.add_edge("preprocess", "generate_sql")
    g.add_edge("generate_sql", "validate_sql")
    
    # 条件路由：validate后决定是修订还是结束
    g.add_conditional_edges(
        "validate_sql",
        decide_next_step,
        {
            "revise": "revise_sql",
            "finalize": "finalize"
        }
    )
    
    # 修订后回到验证
    g.add_edge("revise_sql", "validate_sql")
    
    # finalize 后结束
    g.add_edge("finalize", END)
    
    return g.compile()
