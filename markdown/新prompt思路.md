# 新 Prompt 思路（课堂 Pre 可讲）

## 总览：多智能体 + 结构化输出 + 纠错闭环
- 目标：提升 Text-to-SQL 的可解释性、鲁棒性与可维护性。
- 方法：将“理解→规划→生成→评审→修复→一致性验证”串成闭环；各阶段输出强约束（JSON/单行 SQL），降低幻觉与解析失败。

## 可落地的创新点
- 计划先行（隐式 CoT）
  - 先在心中完成 NL→Schema→Plan 的链式思考，再输出结果；最终只输出结构化产物（计划或 SQL），不暴露推理内容。
- Schema Linking 双阶段
  - 第一步：基于问题与完整 Schema 识别相关表（含中间/桥接表），强调 PK/FK 与连接键覆盖。
  - 第二步（可选）：对 Schema Agent 输出做校正，补充缺失的 FK/PK/连接键，避免别名/列不全导致的 JOIN 错误。
- 子问题分解（Subproblem Agent）
  - 将需求拆为 JSON 结构的子问题，显式标注 SELECT/JOIN/WHERE/GROUP BY/HAVING/ORDER BY/LIMIT 等子句需求。
- 查询计划生成（Query Plan Agent）
  - 返回自然语言步骤（仅计划，不写 SQL），固定顺序：FROM→JOIN→WHERE→GROUP BY→HAVING→ORDER BY→LIMIT，确保每步明确到“表.列”。
- 严格 SQL 生成（SQL Agent）
  - 严格遵循计划与 Schema；单行 SQL、歧义列加前缀、避免 SELECT *、优先使用示例值。
- 结构化评审（Critic）
  - 最小 JSON 输出：valid 布尔或错误列表；支持基于“错误分类学（taxonomy）”的细粒度错误类型，例如：
    - schema.mismatch、join.logic_error、filter.condition_error、aggregation.grouping_error、select.output_error、syntax.structural_error、intent.semantic_error。
- 纠错计划（Correction Plan Agent）
  - 仅产出纠错步骤（不直接写 SQL）；基于 taxonomy 给出“根因→修复计划”。
- 按计划修复（Correction SQL Agent）
  - 严格遵循最新纠错计划生成新 SQL；或在紧急路径下直接“从错到对”。
- 历史记忆（Scratchpad）
  - 汇总历次失败（问题/Schema/错误/错 SQL/计划），面向“最后一次失败”生成更稳妥的纠错计划与 SQL。
- 计划体检（Plan Sanity Agent）
  - 对计划进行结构一致性审查：JOIN 键完整性、聚合与分组搭配、子句顺序、是否存在多余表/列。
- 局部修复+合成（Repair Agents）
  - 按错误类型出多个局部修复，再由“合成器”整合为统一 SQL，保留所有修复、消除冲突。
- 语义一致性闭环
  - SQL 反向翻译为 JSON（意图/表/列/过滤/聚合/分组/排序/limit），与原问题做“语义裁判”；将 mismatch 文本拼接进入修订提示，驱动再次修复。

## 与现有 prompts.py 的映射（已适配/可增强）
- SYSTEM_PROMPT（已增强）
  - 增加隐式思考→Schema 映射→固定子句顺序→仅输出单行 SQL；强调 PK/FK 与连接键、示例值优先、聚合与分组配套、出错精修。
- PREPROCESS_PROMPT（已增强）
  - 明确 get_database_schema 需列/PK/FK；schema_linker 需考虑中间/桥接表；content_retriever 无值返回 []；强调严格输出格式。
- SCHEMA_LINKER_PROMPT_TEMPLATE（已增强）
  - 覆盖完成查询所需表，聚焦连接键；避免过度扩展；仅返回表名 JSON 数组。
- CONTENT_RETRIEVER_PROMPT_TEMPLATE（已增强）
  - 提取并规范化关键值（字符串原样、日期 YYYY-MM-DD、数值为数字）；仅 JSON、无值返回 []。
- GENERATE_SQL_PROMPT（已增强）
  - 严格使用 Schema、歧义列加前缀、避免 SELECT *、固定子句顺序、只输出单行 SQL。
- REVISE_SQL_PROMPT（已增强）
  - 引入 taxonomy 风格的错误标签与修复要点，指导精准修复，输出单行 SQL。
- BACK_TRANSLATE/SEMANTIC_JUDGE（保持）
  - 建议在修订阶段拼接“语义差异提示”文本（已有 `SEMANTIC_MISMATCH_HINT` 可复用）。

## 可选扩展（不破坏接口）
- 新增可选常量：Plan Sanity / Critic-Taxonomy / Correction Plan / Repair-Combine 的提示词模板，按需调用。
- 引入 scratchpad，将失败历史喂给纠错计划与修复代理，提升收敛速度。
- 在执行失败或语义不一致时自动触发：back-translate→semantic judge→mismatch hint→revise。

## 课堂 Pre 可讲要点
- 为什么计划先行：可解释、可调试、能显式约束 JOIN/聚合/排序的结构正确性。
- 为什么强约束输出：降低幻觉与解析失败，便于系统编排与自动评测。
- taxonomy 驱动纠错：定位“错在哪/如何改”，利于自动回归与分析报告。
- 闭环稳定性：生成→执行→评审→修复→一致性判断的持续改进能力。
- 工程兼容性：仅改提示词内容，不改接口与占位符，现有代码零侵入适配。

> 注：本总结基于仓库可见的 `new_prompt.md` 与 NL2SQL 多智能体最佳实践提炼；若需纳入 `prompt.pdf` 的具体要点，请提供其可读文本或关键段落，我可再补充对齐。
