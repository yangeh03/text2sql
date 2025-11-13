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
from .prompts import (
    SYSTEM_PROMPT,
    PREPROCESS_TOOLS,
    EXECUTION_TOOLS,
    PREPROCESS_PROMPT,
    GENERATE_SQL_PROMPT,
    REVISE_SQL_PROMPT,
    BACK_TRANSLATE_PROMPT,
    SEMANTIC_JUDGE_PROMPT,
    SEMANTIC_MISMATCH_HINT,
)
from .tools import get_database_schema, schema_linker, content_retriever, sql_executor
from .utils import safe_parse_json


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

    # 语义验证（反向翻译）相关字段（新增）
    back_translation: Dict[str, Any] = Field(default_factory=dict)  # SQL 反向翻译的结构化描述
    semantic_score: float = 0.0  # 语义一致性分数（0~1）
    semantic_pass: bool = False  # 语义是否通过
    semantic_reason: str = ""  # 若不通过，关键差异说明




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

    # Step 2: 模式链接（使用 LLM 识别相关表，若失败则降级）
    if True:
        print("  🔧 模式链接，筛选相关表...")
    result = schema_linker(state.question, state.db_schema, state.schema_info)
    if result["status"] == "ok":
        state.relevant_schema = result["relevant_schema"]
        if True:
            print(f"  ✓ 筛选出相关表: {result.get('relevant_tables', [])}")
            print(f"  理由: {result.get('rationale', '')}")

    # Step 3: 检索示例值（结合 LLM 提取的关键值与数据库真实值）
    if True:
        print("  🔧 检索示例值...")
    result = content_retriever(state.question, state.relevant_schema, state.db_id, data_dir=state.data_dir)
    if result["status"] == "ok":
        state.retrieved_values = result["retrieved_values"]
        if True:
            print(f"  ✓ 检索到 {len(state.retrieved_values)} 个示例值")
            if state.retrieved_values:
                print(f"  示例: {state.retrieved_values[:3]}")

    # Step 4: 额外信息（保留拓展位）
    # 可接入 RAG：领域知识、常见错误案例、格式与函数对齐提示

    state.step_trace.append("preprocess_completed")
    return state


def semantic_validate_node(state: AgentState) -> AgentState:
    """语义验证阶段：先将 SQL 反向翻译为自然语言，再判断与原问题的语义一致性
    
    流程：
    1) 使用 BACK_TRANSLATE_PROMPT 将 SQL → 自然语言（JSON结构化）
    2) 使用 SEMANTIC_JUDGE_PROMPT 对比原问题与反向描述，返回 {pass, score, reason}
    3) 将结果写入 state，并记录 step_trace
    
    说明：当未开启语义验证开关时（ENABLE_SEMANTIC_VALIDATE=false），本节点将跳过并保持默认通过。
    """
    print("\n🧠 语义验证阶段 - Semantic Validate")

    # 若未启用语义验证，直接跳过（保持兼容）
    if not SETTINGS.enable_semantic_validate:
        state.semantic_pass = True
        state.semantic_score = 1.0
        state.semantic_reason = "已跳过语义验证（开关关闭）"
        state.step_trace.append("semantic: skipped")
        return state

    # 准备上下文数据
    sql = state.sql_draft or ""
    schema = state.relevant_schema or state.db_schema or ""

    # 1) 反向翻译 SQL → 自然语言（结构化 JSON）
    try:
        bt_prompt = BACK_TRANSLATE_PROMPT.format(sql=sql, schema=schema)
        bt_resp = chat(messages=[{"role": "user", "content": bt_prompt}], tools=None, temperature=0.1)
        bt_obj, bt_ok = safe_parse_json(bt_resp.get("content", ""))
        if not bt_ok or not isinstance(bt_obj, (dict, list)):
            # 兜底：使用最小结构占位
            bt_obj = {
                "intent": "",
                "tables": [],
                "columns": [],
                "filters": [],
                "agg": [],
                "group_by": [],
                "order_by": [],
                "limit": None,
            }
        state.back_translation = bt_obj if isinstance(bt_obj, dict) else {"parsed": bt_obj}
    except Exception as e:
        # 失败时填充空结构，防止后续崩溃
        state.back_translation = {
            "intent": "",
            "tables": [],
            "columns": [],
            "filters": [],
            "agg": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
            "_error": f"back-translate failed: {str(e)}",
        }

    # 2) 语义一致性判定
    try:
        import json as _json
        jd_prompt = SEMANTIC_JUDGE_PROMPT.format(
            question=state.question,
            bt=_json.dumps(state.back_translation, ensure_ascii=False, indent=2),
        )
        jd_resp = chat(messages=[{"role": "user", "content": jd_prompt}], tools=None, temperature=0.0)
        jd_obj, jd_ok = safe_parse_json(jd_resp.get("content", ""))
        if isinstance(jd_obj, dict):
            state.semantic_pass = bool(jd_obj.get("pass", False))
            # score 解析为 float，不可用则给默认值
            try:
                state.semantic_score = float(jd_obj.get("score", 0.0))
            except Exception:
                state.semantic_score = 0.0
            state.semantic_reason = str(jd_obj.get("reason", ""))
        else:
            # 解析失败，默认不通过
            state.semantic_pass = False
            state.semantic_score = 0.0
            state.semantic_reason = "语义判定解析失败"
    except Exception as e:
        state.semantic_pass = False
        state.semantic_score = 0.0
        state.semantic_reason = f"语义判定出错: {str(e)}"

    print(f"  ✓ 语义判定：pass={state.semantic_pass} score={state.semantic_score:.2f}")
    if not state.semantic_pass:
        print(f"  ✗ 不通过原因：{state.semantic_reason}")

    state.step_trace.append(f"semantic: score={state.semantic_score} pass={state.semantic_pass}")
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
    
    # 构建修订提示（基础：依据执行错误）
    prompt = REVISE_SQL_PROMPT.format(sql_draft=state.sql_draft, error=error_msg)

    # 如果存在语义不一致的信息，追加“语义差异提示”帮助 LLM 精准修正
    if state.semantic_pass is False and (state.semantic_reason or state.back_translation):
        bt_intent = ""
        if isinstance(state.back_translation, dict):
            bt_intent = str(state.back_translation.get("intent", "")).strip()
        semantic_hint = SEMANTIC_MISMATCH_HINT.format(
            bt_intent=bt_intent or "",
            question=state.question,
            reason=state.semantic_reason or "",
        )
        prompt = prompt + "\n" + semantic_hint
    
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


def decide_after_generate(state: AgentState) -> str:
    """条件路由（generate_sql 之后）
    - 若开启语义验证：进入 semantic_validate
    - 否则：直接进入 validate_sql
    """
    return "semantic" if SETTINGS.enable_semantic_validate else "validate"


def decide_after_semantic(state: AgentState) -> str:
    """条件路由（semantic_validate 之后）
    - 未开启语义验证：直接进入 validate
    - 若不通过：进入 revise
    - 若通过且模式为 finalize_on_pass：直接 finalize（用于课堂 Demo 或快速出结果）
    - 否则：进入 validate
    说明：若 LLM 返回的 score 低于阈值，也视为未通过。
    """
    if not SETTINGS.enable_semantic_validate:
        return "validate"
    passed = bool(state.semantic_pass) and (state.semantic_score >= SETTINGS.semantic_score_threshold)
    if not passed:
        return "revise"
    if SETTINGS.semantic_gate_mode.strip().lower() == "finalize_on_pass":
        return "finalize"
    return "validate"


def build_graph():
    """构建LangGraph状态图：preprocess -> generate -> validate -> (revise -> validate)* -> finalize -> end"""
    g = StateGraph(AgentState)
    
    # 添加节点
    g.add_node("preprocess", preprocess_node)
    g.add_node("generate_sql", generate_sql_node)
    # 新增：语义验证节点（反向翻译 + 语义一致性判定）
    g.add_node("semantic_validate", semantic_validate_node)
    g.add_node("validate_sql", validate_sql_node)
    g.add_node("revise_sql", revise_sql_node)
    g.add_node("finalize", finalize_node)
    
    # 定义边
    g.add_edge(START, "preprocess")
    g.add_edge("preprocess", "generate_sql")

    # generate_sql 之后根据开关选择是否进入语义验证
    g.add_conditional_edges(
        "generate_sql",
        decide_after_generate,
        {
            "semantic": "semantic_validate",
            "validate": "validate_sql",
        }
    )

    # 语义验证之后的条件路由
    g.add_conditional_edges(
        "semantic_validate",
        decide_after_semantic,
        {
            "revise": "revise_sql",
            "validate": "validate_sql",
            "finalize": "finalize",
        }
    )
    
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
