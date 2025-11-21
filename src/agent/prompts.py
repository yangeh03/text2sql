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

# ============================================================
# 新增：子问题分解提示词
# ============================================================
SUBPROBLEM_PROMPT = (
    "你是一个子问题分解专家。给定一个自然语言问题和相关的数据库schema，"
    "请将问题分解为多个SQL子问题。\n\n"
    "问题：{question}\n\n"
    "相关Schema：\n{relevant_schema}\n\n"
    "请分析问题，识别需要哪些SQL子句（如 WHERE, GROUP BY, JOIN, ORDER BY, HAVING, LIMIT等）。\n"
    "返回一个JSON对象，格式如下：\n"
    '{{\'subproblems\': ['
    '{{\'clause\': \'SELECT\', \'expression\': \'...\'}}, '
    '{{\'clause\': \'JOIN\', \'expression\': \'...\'}}, ...'
    ']}}\n\n'
    "只返回有效的JSON，不要包含markdown标记或额外解释。"
)

# ============================================================
# 新增：SQL计划提示词（COT + FINAL_PLAN）
# ============================================================
SQL_PLAN_PROMPT = (
    "你是一个SQL查询计划专家。请使用思维链（Chain-of-Thought）方式，"
    "为给定问题创建详细的SQL查询计划。\n\n"
    "问题：{question}\n\n"
    "相关Schema：\n{relevant_schema}\n\n"
    "示例值：{retrieved_values}\n\n"
    "子问题分解：\n{subproblems}\n\n"
    "请遵循以下步骤：\n"
    "1. **分析问题**：深入理解用户意图，识别关键信息和约束条件。\n"
    "2. **映射到Schema**：确定需要的表、列以及它们之间的JOIN关系。\n"
    "3. **制定计划**：创建步骤清晰的查询计划，每步对应SQL的一部分。\n\n"
    "重要提示：\n"
    "- 计划必须使用自然语言\n"
    "- 明确提及每步使用的表名和列名\n"
    "- 不要写最终的SQL查询\n"
    "- 所有必要的表必须在FROM和JOIN步骤中出现\n"
    "- GROUP BY, HAVING, ORDER BY, LIMIT等子句必须按正确顺序出现\n\n"
    "在你的推理过程后，必须在末尾添加一个明确的段落，以'FINAL_PLAN:'开头，"
    "总结你的查询计划（简洁的要点形式）。"
)

# ============================================================
# 新增：纠错计划提示词（COT + CORRECTION_PLAN）
# ============================================================
CORRECTION_PLAN_PROMPT = (
    "你是一个高级SQL调试专家。你的任务是分析失败的SQL查询，"
    "使用思维链（Chain-of-Thought）创建清晰的纠错计划。不要直接写修正后的SQL。\n\n"
    "原始问题：{question}\n\n"
    "相关Schema：\n{relevant_schema}\n\n"
    "失败的SQL：\n{sql_draft}\n\n"
    "执行错误：\n{error}\n\n"
    "{semantic_issues}"
    "{correction_history}"
    "你是错误分类专家，了解以下错误类型：\n"
    "- schema.mismatch: 表名、列名不存在或使用模糊\n"
    "- join.logic_error: JOIN条件错误、外键错误、多余的表\n"
    "- filter.condition_error: WHERE/HAVING子句错误\n"
    "- aggregation.grouping_error: 聚合函数或GROUP BY错误\n"
    "- select.output_error: SELECT列错误（多余、缺失、顺序错误）\n"
    "- syntax.structural_error: 语法错误或缺少必需子句\n"
    "- intent.semantic_error: 语法正确但不符合用户意图\n\n"
    "推理过程：\n"
    "1. **定位不匹配**：比较问题、失败的SQL和Schema，找到错误来源\n"
    "2. **识别错误类型**：根据上述分类确定错误类型\n"
    "3. **形成假设**：用一句话说明根本原因（注意列名细节，如'name' vs 'song_name'）\n"
    "4. **创建计划**：写出步骤清晰的修正计划\n"
    "5. **学习历史**：如果有纠错历史，避免重复之前的错误\n"
    "6. **语义问题**：如果有语义验证问题，重点关注SQL的意图是否符合问题\n\n"
    "在你的推理过程后，必须在末尾添加一个明确的段落，以'CORRECTION_PLAN:'开头，"
    "总结你的纠错计划（简洁的步骤形式）。"
)

# ============================================================
# 新增：基于纠错计划生成修正SQL
# ============================================================
CORRECTION_SQL_PROMPT = (
    "你是一个专业的SQL修正专家。根据提供的纠错计划，生成修正后的SQL查询。\n\n"
    "原始问题：{question}\n\n"
    "相关Schema：\n{relevant_schema}\n\n"
    "错误的SQL：\n{sql_draft}\n\n"
    "纠错计划：\n{correction_plan}\n\n"
    "请严格按照纠错计划修正SQL。\n"
    "只输出最终的SQL查询语句（单行格式），不要包含任何解释或额外字符。"
)

# ============================================================
# 新增：SQL语义验证提示词（SQL→Text反向翻译 + 语义一致性判断）
# ============================================================
SEMANTIC_VALIDATE_PROMPT = (
    "你是一个SQL语义验证专家。你的任务是：\n"
    "1. 将给定的SQL查询翻译成自然语言解释\n"
    "2. 判断SQL的语义是否与原始问题一致\n\n"
    "原始问题：{question}\n\n"
    "相关Schema：\n{relevant_schema}\n\n"
    "生成的SQL：\n{sql_draft}\n\n"
    "请执行以下步骤：\n"
    "1. **SQL→Text翻译**：用自然语言解释这个SQL查询的含义，包括：\n"
    "   - 查询哪些表\n"
    "   - 选择哪些字段\n"
    "   - 有什么过滤条件（WHERE）\n"
    "   - 有什么聚合或分组（GROUP BY, HAVING）\n"
    "   - 有什么排序或限制（ORDER BY, LIMIT）\n\n"
    "2. **语义一致性判断**：比较SQL的语义和原始问题，识别以下问题：\n"
    "   - **字段错误**：返回的字段是否符合问题要求\n"
    "   - **条件错误**：WHERE条件是否过严或过松\n"
    "   - **JOIN错误**：表连接是否正确，是否缺少或多余表\n"
    "   - **聚合错误**：聚合函数（COUNT/SUM/AVG等）是否正确\n"
    "   - **排序错误**：ORDER BY是否符合问题要求\n"
    "   - **限制错误**：LIMIT是否合理\n\n"
    "请以JSON格式返回结果，包含以下字段：\n"
    "- explanation: SQL的自然语言解释（字符串）\n"
    "- semantic_match: 语义是否匹配（true或false）\n"
    "- issues: 问题列表（数组，每项包含type和description字段）\n\n"
    "示例格式：\n"
    '{{"explanation": "这个SQL查询singer表，统计所有歌手的数量", "semantic_match": true, "issues": []}}\n\n'
    "注意：只返回纯JSON对象，不要包含任何markdown标记（如```json或```）或其他解释文字。"
)
