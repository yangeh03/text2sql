# -*- coding: utf-8 -*-
"""
用 LangGraph 搭建 Text-to-SQL Agent：
- preprocess: 获取schema、模式链接、检索示例值
- subproblem: 子问题分解
- sql_plan: SQL查询计划（COT）
- generate_sql: 生成SQL草稿
- validate_sql: 执行SQL并验证
- correction_plan: 纠错计划（COT）
- correction_sql: 修正SQL
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
    # 输入
    question: str
    db_id: str
    
    # 数据库模式信息
    db_schema: str = ""  # 完整的 CREATE TABLE 语句
    relevant_schema: str = ""  # 模式链接后筛选的相关表和列
    retrieved_values: List[str] = Field(default_factory=list)  # 示例值
    
    # 新增：子问题分解和计划
    subproblems: str = ""  # 子问题分解结果（JSON格式）
    sql_plan: str = ""  # SQL查询计划（COT推理 + FINAL_PLAN段）
    correction_plan: str = ""  # 纠错计划（COT推理 + CORRECTION_PLAN段）
    
    # SQL 生成与验证
    sql_draft: str = ""  # 当前 SQL 草稿
    sql_nl_explanation: str = ""  # SQL→Text的自然语言解释（反向翻译）
    semantic_validation: Dict[str, Any] = Field(default_factory=dict)  # 语义验证结果
    execution_result: Dict[str, Any] = Field(default_factory=dict)  # 执行结果或错误
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)  # 修订历史
    correction_history: List[Dict[str, Any]] = Field(default_factory=list)  # 纠错历史（包含错误、计划、修正SQL）
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


def subproblem_node(state: AgentState) -> AgentState:
    """子问题分解阶段：将自然语言问题分解为SQL子问题"""
    if True:
        print("\n🔍 子问题分解阶段 - Subproblem Decomposition")
    
    # 构建子问题分解提示
    prompt = SUBPROBLEM_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # 调用LLM分解子问题
    resp = chat(messages=messages, tools=None, temperature=0.1)
    content = resp.get("content", "").strip()
    
    # 清理JSON（移除markdown标记）
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
        print(f"  ✓ 子问题分解完成")
        # 尝试解析并显示子问题
        try:
            import json
            subprob_data = json.loads(content)
            if "subproblems" in subprob_data:
                print(f"  识别到 {len(subprob_data['subproblems'])} 个子问题")
        except:
            pass
    
    return state


def sql_plan_node(state: AgentState) -> AgentState:
    """SQL计划阶段：使用COT生成查询计划"""
    if True:
        print("\n📝 SQL计划阶段 - SQL Plan (COT)")
    
    # 构建SQL计划提示
    prompt = SQL_PLAN_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        retrieved_values=", ".join(state.retrieved_values) if state.retrieved_values else "无",
        subproblems=state.subproblems or "无"
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # 调用LLM生成计划
    resp = chat(messages=messages, tools=None, temperature=0.1)
    plan = resp.get("content", "").strip()
    
    state.sql_plan = plan
    state.step_trace.append(f"sql_plan_created")
    
    if True:
        print(f"  ✓ SQL计划生成完成")
        # 提取并显示FINAL_PLAN段
        if "FINAL_PLAN:" in plan:
            final_plan_start = plan.index("FINAL_PLAN:")
            final_plan = plan[final_plan_start:final_plan_start+200]
            print(f"  计划摘要: {final_plan[:150]}...")
    
    return state


def generate_sql_node(state: AgentState) -> AgentState:
    """SQL生成阶段：基于计划和预处理结果生成SQL"""
    if True:
        print("\n🔨 SQL生成阶段 - Generate SQL")
    
    # 构建生成提示（现在基于SQL计划）
    prompt = GENERATE_SQL_PROMPT.format(
        question=state.question,
        relevant_schema=state.relevant_schema or state.db_schema,
        retrieved_values=", ".join(state.retrieved_values) if state.retrieved_values else "无"
    )
    
    # 如果有SQL计划，将其添加到提示中
    if state.sql_plan:
        prompt = f"SQL查询计划：\n{state.sql_plan}\n\n{prompt}"
    
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
    """SQL验证阶段：语义验证 + 执行验证（两阶段验证）"""
    if True:
        print("\n✅ SQL验证阶段 - Validate SQL")
    
    if not state.sql_draft:
        state.execution_result = {"status": "error", "error": "没有SQL可执行"}
        return state
    
    # ========== 第1阶段：语义验证（工具调用）==========
    if True:
        print("  🔍 语义验证...")
    
    semantic_result = semantic_validator(
        question=state.question,
        sql_draft=state.sql_draft,
        relevant_schema=state.relevant_schema or state.db_schema
    )
    
    # 处理语义验证结果
    if semantic_result["status"] == "ok":
        state.sql_nl_explanation = semantic_result.get("explanation", "")
        state.semantic_validation = {
            "semantic_match": semantic_result.get("semantic_match", True),
            "issues": semantic_result.get("issues", [])
        }
        
        if True:
            if state.semantic_validation["semantic_match"]:
                print(f"  ✓ 语义验证通过")
                if state.sql_nl_explanation:
                    print(f"  SQL解释: {state.sql_nl_explanation[:100]}...")
            else:
                print(f"  ✗ 语义验证失败")
                if state.sql_nl_explanation:
                    print(f"  SQL解释: {state.sql_nl_explanation[:100]}...")
                print(f"  发现问题: {len(state.semantic_validation['issues'])} 个")
                for issue in state.semantic_validation["issues"][:3]:
                    print(f"    - [{issue.get('type', 'unknown')}] {issue.get('description', '')}")
    else:
        # 语义验证工具调用失败，降级为通过
        if True:
            print(f"  ⚠️  语义验证工具调用失败，默认通过: {semantic_result.get('error', '')}")
        state.semantic_validation = {
            "semantic_match": True,
            "issues": []
        }
    
    state.step_trace.append(f"semantic_validation: {state.semantic_validation['semantic_match']}")
    
    # 如果语义验证失败，跳过执行验证，直接进入纠错
    if not state.semantic_validation.get("semantic_match", True):
        if True:
            print(f"  ⚠️  语义验证失败，跳过执行验证")
        state.execution_result = {
            "status": "error",
            "error": "语义不匹配",
            "semantic_issues": state.semantic_validation.get("issues", [])
        }
        # 记录到修订历史
        state.revision_history.append({
            "sql": state.sql_draft,
            "result": state.execution_result,
            "iteration": len(state.revision_history) + 1,
            "validation_type": "semantic"
        })
        state.step_trace.append(f"validation: semantic_failed")
        return state
    
    # ========== 第2阶段：执行验证 ==========
    if True:
        print(f"\n  🔧 执行验证...")
    
    # 执行SQL
    result = sql_executor(state.db_id, state.sql_draft, data_dir=state.data_dir)
    state.execution_result = result
    
    # 记录到修订历史
    state.revision_history.append({
        "sql": state.sql_draft,
        "result": result,
        "iteration": len(state.revision_history) + 1,
        "validation_type": "execution"
    })
    
    if True:
        if result["status"] == "ok":
            print(f"  ✓ 执行成功，返回 {result.get('rowcount', 0)} 行")
        else:
            print(f"  ✗ 执行失败: {result.get('error', '')}")
    
    state.step_trace.append(f"validation: {result['status']}")
    return state


def correction_plan_node(state: AgentState) -> AgentState:
    """纠错计划阶段：使用COT分析错误并生成修正计划"""
    if True:
        print(f"\n🔧 纠错计划阶段 - Correction Plan (第 {len(state.revision_history)} 次)")
    
    error_msg = state.execution_result.get("error", "未知错误")
    
    # 构建语义问题字符串
    semantic_issues_text = ""
    if state.semantic_validation.get("issues"):
        semantic_issues_text = "\n\n**语义验证发现的问题：**\n"
        for issue in state.semantic_validation["issues"]:
            semantic_issues_text += f"- [{issue.get('type', 'unknown')}] {issue.get('description', '')}\n"
        if state.sql_nl_explanation:
            semantic_issues_text += f"\nSQL的自然语言解释: {state.sql_nl_explanation}\n"
    
    # 构建纠错历史记录字符串
    history_text = ""
    if state.correction_history:
        history_text = "\n\n**以下是之前的纠错历史（请从中学习，避免重复错误）：**\n"
        for i, record in enumerate(state.correction_history, 1):
            history_text += f"\n--- 第 {i} 次纠错 ---\n"
            history_text += f"错误SQL: {record.get('sql', '')}\n"
            history_text += f"错误信息: {record.get('error', '')}\n"
            history_text += f"纠错计划: {record.get('plan', '')[:200]}...\n"
            if record.get('corrected_sql'):
                history_text += f"修正后SQL: {record.get('corrected_sql', '')}\n"
    
    # 构建纠错计划提示
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
    
    # 调用LLM生成纠错计划
    resp = chat(messages=messages, tools=None, temperature=0.1)
    plan = resp.get("content", "").strip()
    
    state.correction_plan = plan
    state.step_trace.append(f"correction_plan_created")
    
    if True:
        print(f"  ✓ 纠错计划生成完成")
        # 提取并显示CORRECTION_PLAN段
        if "CORRECTION_PLAN:" in plan:
            correction_plan_start = plan.index("CORRECTION_PLAN:")
            correction_plan = plan[correction_plan_start:correction_plan_start+200]
            print(f"  计划摘要: {correction_plan[:150]}...")
    
    return state


def correction_sql_node(state: AgentState) -> AgentState:
    """纠错SQL阶段：基于纠错计划生成修正后的SQL"""
    if True:
        print(f"\n🔨 纠错SQL阶段 - Correction SQL")
    
    # 记录当前纠错历史（在生成新SQL之前）
    old_sql = state.sql_draft
    old_error = state.execution_result.get("error", "未知错误")
    
    # 构建纠错SQL提示
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
    
    # 调用LLM生成修正后的SQL
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
    
    # 记录纠错历史
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
        print(f"  ✓ 修正后SQL: {sql}")
        print(f"  📝 已记录第 {len(state.correction_history)} 次纠错历史")
    
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
        return "correction_plan"  # 修改：从revise改为correction_plan
    
    # 如果返回空结果，也尝试修订（但只修订一次）
    if result.get("status") == "ok" and result.get("rowcount", 0) == 0:
        # 检查是否已经修订过空结果
        if len(state.revision_history) == 1:
            if True:
                print("\n⚠️  结果为空，尝试修订...")
            return "correction_plan"  # 修改：从revise改为correction_plan
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
    """构建LangGraph状态图：
    preprocess -> subproblem -> sql_plan -> generate_sql -> validate_sql 
    -> (correction_plan -> correction_sql -> validate_sql)* -> finalize -> end
    """
    g = StateGraph(AgentState)
    
    # 添加节点
    g.add_node("preprocess", preprocess_node)
    g.add_node("subproblem", subproblem_node)  # 新增
    g.add_node("sql_plan", sql_plan_node)  # 新增
    g.add_node("generate_sql", generate_sql_node)
    g.add_node("validate_sql", validate_sql_node)
    g.add_node("correction_plan", correction_plan_node)  # 新增：替换revise_sql
    g.add_node("correction_sql", correction_sql_node)  # 新增
    g.add_node("finalize", finalize_node)
    
    # 定义边：主流程
    g.add_edge(START, "preprocess")
    g.add_edge("preprocess", "subproblem")  # 新增
    g.add_edge("subproblem", "sql_plan")  # 新增
    g.add_edge("sql_plan", "generate_sql")  # 修改：从preprocess改为sql_plan
    g.add_edge("generate_sql", "validate_sql")
    
    # 条件路由：validate后决定是修订还是结束
    g.add_conditional_edges(
        "validate_sql",
        decide_next_step,
        {
            "correction_plan": "correction_plan",  # 修改：从revise改为correction_plan
            "finalize": "finalize"
        }
    )
    
    # 修订流程：correction_plan -> correction_sql -> validate
    g.add_edge("correction_plan", "correction_sql")  # 新增
    g.add_edge("correction_sql", "validate_sql")  # 修改：从revise_sql改为correction_sql
    
    # finalize 后结束
    g.add_edge("finalize", END)
    
    return g.compile()
