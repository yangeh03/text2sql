# -*- coding: utf-8 -*-
SYSTEM_PROMPT = (
    "你是Text-to-SQL智能体，将自然语言问题转换为SQL查询。\n\n"
    "重要规则：\n"
    "1. 只使用schema中存在的表名和列名，不要臆断\n"
    "2. 生成的SQL必须是单行格式，不要使用换行符\n"
    "3. 优先使用提供的示例值来构建WHERE条件\n"
    "4. 仔细检查JOIN条件和外键关系\n"
    "5. 如果遇到错误，根据错误信息精确修复\n"
)

# 预处理阶段工具
PREPROCESS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_database_schema",
            "description": "获取完整的数据库模式（CREATE TABLE语句）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schema_linker",
            "description": "从完整模式中筛选与问题相关的表和列",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "content_retriever",
            "description": "从数据库中检索示例值，帮助构建准确的WHERE条件",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# SQL执行工具
EXECUTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "sql_executor",
            "description": "执行SQL查询并返回结果或错误信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "要执行的SQL查询语句"}
                },
                "required": ["sql"],
            },
        },
    },
]

# 节点级提示词
PREPROCESS_PROMPT = (
    "请依次执行以下步骤来准备SQL生成所需的信息：\n"
    "1. 调用 get_database_schema 获取完整数据库模式\n"
    "2. 调用 schema_linker 筛选相关表\n"
    "3. 调用 content_retriever 检索示例值\n"
)

# Schema Linker 提示词模板
SCHEMA_LINKER_PROMPT_TEMPLATE = (
    "给定一个自然语言问题和完整的数据库schema，请识别与问题相关的表。\n\n"
    "问题：{question}\n\n"
    "完整数据库Schema：\n{db_schema}\n\n"
    "请仔细分析问题中的关键词（如：表名、列名、实体名），并识别相关的表。\n"
    "只返回相关表名的列表，格式为JSON数组，例如：[\"table1\", \"table2\"]\n"
    "不要包含任何其他解释或文字，只返回JSON数组。"
)

# Content Retriever 提示词模板
CONTENT_RETRIEVER_PROMPT_TEMPLATE = (
    "给定一个自然语言问题和相关的数据库schema，从问题中识别潜在的关键值（如人名、地名、机构名、产品名、特定时间、数字阈值等）。\n\n"
    "问题：{question}\n\n"
    "相关Schema：\n{relevant_schema}\n\n"
    "请提取问题中的关键值（如人名、地名、机构名、产品名、特定时间、数字阈值等）。\n"
    "只返回关键值的列表，格式为JSON数组，例如：[\"value1\", \"value2\"]\n"
    "如果问题中没有明确的关键值，返回空数组：[]\n"
    "不要包含任何其他解释或文字，只返回JSON数组。"
)

GENERATE_SQL_PROMPT = (
    "基于以下信息生成SQL查询：\n"
    "- 问题：{question}\n"
    "- 相关表结构：\n{relevant_schema}\n"
    "- 示例值：{retrieved_values}\n\n"
    "请生成准确的SQL查询（单行格式，不要换行）。只输出SQL语句，不要其他解释。"
)

REVISE_SQL_PROMPT = (
    "之前的SQL执行失败了：\n"
    "SQL: {sql_draft}\n"
    "错误: {error}\n\n"
    "请根据错误信息修正SQL。常见问题：\n"
    "- 'no such column': 检查列名是否正确，是否需要表前缀\n"
    "- 'no such table': 检查表名拼写\n"
    "- 'ambiguous column': 需要添加表名前缀\n"
    "- 空结果: 检查WHERE条件是否过严，JOIN是否正确\n\n"
    "只输出修正后的SQL语句（单行格式）。"
)

# ===============================
# 反向翻译与语义判定（新增）
# ===============================

# BACK_TRANSLATE_PROMPT：将 SQL 翻译回自然语言，并以 JSON 结构化输出，便于后续自动对齐
# 要求：只返回 JSON，不要任何解释性文本
BACK_TRANSLATE_PROMPT = (
    "请将下面的 SQL 查询翻译成自然语言的结构化描述，并只用 JSON 格式返回。\n"
    "请严格使用以下字段：intent(查询意图)、tables(涉及表名数组)、columns(涉及列名数组)、filters(过滤条件数组，原样字符串)、"
    "agg(聚合函数数组，如COUNT/SUM等)、group_by(分组列数组)、order_by(排序列及方向数组)、limit(限制行数或null)。\n\n"
    "SQL：{sql}\n\n"
    "可参考的相关表结构（可能不完整，仅供理解）：\n{schema}\n\n"
    "注意：\n"
    "- 只返回一个合法的 JSON，不要任何额外文本。\n"
    "- 所有字段必须存在，即使为空也要给出空数组或 null。\n"
)

# SEMANTIC_JUDGE_PROMPT：给定原始问题与反向翻译的 JSON，判断语义是否一致
# 输出：只返回 JSON，格式为 {"pass": bool, "score": float, "reason": str}
SEMANTIC_JUDGE_PROMPT = (
    "请根据原始问题与 SQL 的反向翻译描述，判断两者的语义是否一致。\n"
    "只返回 JSON，格式为 {{\"pass\": bool, \"score\": float, \"reason\": string}}，其中：\n"
    "- pass: 是否通过语义一致性检查（True/False）\n"
    "- score: 一致性得分（0~1），1表示完全一致\n"
    "- reason: 若不一致，请给出差异的关键点（如目标表/聚合/过滤条件/分组/排序等）\n\n"
    "原始问题：{question}\n\n"
    "SQL反向翻译的描述(JSON)：\n{bt}\n\n"
    "注意：\n"
    "- 只返回一个合法的 JSON，不要任何额外文本。\n"
)

# 在修订阶段提示语义差异的模板（可选拼接）
SEMANTIC_MISMATCH_HINT = (
    "\n[语义差异提示] 你的 SQL 当前表达的意图为：{bt_intent}；需要回答的问题是：{question}。\n"
    "请重点修正以下不一致之处：{reason}\n"
)