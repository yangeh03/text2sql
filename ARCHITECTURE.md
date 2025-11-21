# Text-to-SQL Agent — 架构设计 （详细说明）

本文档描述 `data-agent` 项目中基于 LangGraph 状态机的 Text-to-SQL 智能体的整体架构。目标是给开发者和研究人员提供清晰的组件划分、数据流、接口约定、安全与扩展点说明，便于维护与扩展。

## 一、总体概述

- **目标**：将自然语言问题（Question）转为经过语义验证和执行验证，并可能修订的 SQL，最终输出能够在真实 SQLite 数据库上执行且返回期望结果的 SQL。
- **关键思路**：预处理（获取 schema 与示例值）→ 生成 SQL → **语义验证（SQL→Text 反向翻译）** → 执行验证 → 修订（基于语义或执行错误）→ 最终化。该流程由 LangGraph 状态机驱动，形成语义验证-执行验证-修订闭环（Semantic + Execution-Guided Generation + Auto-Revision）。
- **主要约束**：只读执行、行数与时间限制、防止无限修订（最大修订次数默认 3 次）。

## 二、核心模块与文件映射

- **状态图 / 控制流**：`src/agent/graph.py`
- **工具实现（四个核心工具）**：`src/agent/tools.py`
- **LLM 封装与调用**：`src/agent/llm.py`
- **提示词与模板**：`src/agent/prompts.py`
- **配置管理**：`src/agent/config.py`
- **通用工具与数据加载**：`src/agent/utils.py`
- **入口与运行器**：`src/agent/main.py`

这些文件共同构成智能体的可执行管线。文档后文会对每个模块职责、接口与典型实现细节说明。

## 三、数据模型（AgentState）

智能体在 LangGraph 中以状态对象（如 `AgentState`）表示。关键字段包括：

- `question`：自然语言问题字符串。
- `db_id`：目标数据库标识符（例如 `concert_singer`）。
- `db_schema`：数据库完整 CREATE TABLE DDL（字符串）。
- `relevant_schema`：筛选后的与问题相关的表/字段子集（字符串或结构化对象）。
- `retrieved_values`：示例实体值列表（用于填充 prompt）。
- **`subproblems`**：子问题分解结果（JSON格式字符串），将自然语言问题拆解为多个SQL子句。
- **`sql_plan`**：SQL查询计划（含COT推理 + FINAL_PLAN段），用于指导SQL生成。
- **`sql_nl_explanation`**：SQL→Text的自然语言解释（反向翻译），用于语义验证。
- **`semantic_validation`**：语义验证结果，包含 `semantic_match`（布尔值）和 `issues`（问题列表）。
- **`correction_plan`**：纠错计划（含COT推理 + CORRECTION_PLAN段），分析错误并给出修正步骤。
- `sql_draft`：当前 SQL 草稿。
- `execution_result`：执行返回（数据或错误信息）。
- `revision_history`：修订记录（每次修订的元信息与原因）。
- **`correction_history`**：纠错历史记录（包含错误SQL、错误信息、纠错计划、修正后SQL），用于避免重复错误。
- `final_sql`：最终接受的 SQL。
- `max_revisions`：最大修订次数（默认 3）。

这种状态模型有利于可观测性（可以序列化并记录每个状态变迁）以及支持回放调试。

## 四、五个核心工具（职责与接口）

系统通过五个“工具”（tools）来实现预处理、验证与执行：

1. **get_database_schema**
   - 责任：从数据库文件或元数据加载并返回完整的 CREATE TABLE DDL（字符串）以及必要的表/列注释或元信息。
   - 输入：`db_id`
   - 输出：`db_schema`（字符串），以及可选的 schema 元数据结构。

2. **schema_linker**
   - 责任：基于 `question` 和 `db_schema`，识别并筛选出与问题相关的表与列（减少 prompt 长度，提高准确率）。
   - 输入：`question`, `db_schema`
   - 输出：`relevant_schema`（例如仅包含相关 CREATE TABLE 片段或 JSON 列表）。

3. **content_retriever**
   - 责任：从 `relevant_schema` 与数据库中检索示例值（实体、常用枚举值、边界值），用于 prompt 填充以提升 SQL 的可执行性。
   - 输入：`question`, `relevant_schema`, `db_id`
   - 输出：`retrieved_values`（字符串列表或字典）。

4. **semantic_validator**
   - 责任：在执行SQL前，通过反向翻译（SQL→Text）和语义一致性判断，提前发现SQL的语义错误。
   - 输入：`question`, `sql_draft`, `relevant_schema`
   - 输出：`{ status, explanation, semantic_match, issues }`。
   - 实现注意：使用LLM进行反向翻译，识别字段错误、条件错误、JOIN错误、聚合错误等问题。降级策略：如果工具调用失败，默认返回语义匹配以避免阻塞流程。

5. **sql_executor**
   - 责任：在目标 SQLite 数据库上执行 SQL（只读），返回结果或错误信息。
   - 输入：`db_id`, `sql_query`
   - 输出：执行结果（行数、数据样本）或错误/异常（语法错误、no such column 等）。
   - 安全约束：强制 read-only，自动注入 `LIMIT`，执行超时控制。

工具间由状态字段传递数据（LangGraph 节点之间通过 `AgentState` 共享）。

## 4.5. 语义验证工具（Semantic Validator）

基于论文《Guarding Text-to-SQL against Hallucinated and Ambiguous Questions》（GBV-SQL）中的反向翻译思想，系统引入了语义验证工具：

**实现方式**：作为工具函数（`semantic_validator`）而非独立节点，在 `validate_sql_node` 中调用，保持验证流程的紧凑性。

**职责**：在执行SQL前，通过反向翻译（SQL→Text）和语义一致性判断，提前发现SQL的语义错误。

**流程**：
1. **SQL→Text翻译**：使用LLM将生成的SQL翻译成自然语言解释
2. **语义一致性判断**：比对SQL语义和原始问题，识别以下问题类型：
   - **字段错误**：返回的字段是否符合问题要求
   - **条件错误**：WHERE条件是否过严或过松
   - **JOIN错误**：表连接是否正确，是否缺少或多余表
   - **聚合错误**：聚合函数（COUNT/SUM/AVG等）是否正确
   - **排序错误**：ORDER BY是否符合问题要求
   - **限制错误**：LIMIT是否合理

**输入**：`question`, `sql_draft`, `relevant_schema`

**输出**：
```json
{
  "explanation": "SQL的自然语言解释",
  "semantic_match": true/false,
  "issues": [
    {"type": "field/condition/join/aggregation/sort/limit", "description": "具体问题描述"}
  ]
}
```

**优势**：
- 提前发现语义错误，避免不必要的SQL执行
- 不依赖数据库执行结果，能检测出"能跑但语义错误"的SQL
- 为纠错提供更精准的问题定位

**实现方式**：
- 作为工具函数 `semantic_validator` 在 `validate_sql_node` 中调用
- 在 `validate_sql_node` 中作为第一阶段验证，调用工具获取验证结果
- 如果语义验证失败，跳过执行验证，直接进入 `correction_plan`
- 语义问题会传递给 `correction_plan_node` 用于生成更精准的纠错计划
- 降级策略：如果工具调用失败，默认返回语义匹配，不阻塞流程

## 五、流程（LangGraph 状态流）

系统采用七节点流程图（**已重构**）：

1. **START → preprocess**
   - 调用 `get_database_schema`，`schema_linker`，`content_retriever`。
   - 产出 `db_schema`, `relevant_schema`, `retrieved_values`。

2. **preprocess → subproblem**（**新增节点**）
   - 使用 LLM 将自然语言问题分解为多个SQL子问题（如 WHERE, JOIN, GROUP BY等子句）。
   - 输出 `subproblems`（JSON格式）。

3. **subproblem → sql_plan**（**新增节点**）
   - 基于子问题、schema和示例值，使用**思维链（Chain-of-Thought）**方式生成SQL查询计划。
   - 推理过程后必须包含 `FINAL_PLAN:` 段，总结查询步骤。
   - 输出 `sql_plan`。

4. **sql_plan → generate_sql**
   - 基于 `sql_plan`、`relevant_schema` 与 `retrieved_values` 生成初始 SQL。
   - 调用 LLM（`llm.py`），输出 `sql_draft`。

5. **generate_sql → validate_sql**
   - **语义验证**：使用 LLM 将 SQL 反向翻译为自然语言，判断 SQL 语义是否与原始问题一致。
   - **执行验证**：如果语义验证通过，使用 `sql_executor` 执行 `sql_draft`。
   - 根据验证结果路由：
     - 语义和执行都成功且返回非空数据 → finalize
     - 语义验证失败或执行失败 → correction_plan（最多 `max_revisions`次）

6. **validate_sql → correction_plan**（**新增节点，替换 revise_sql**）
   - 根据语义验证错误或执行错误类型，使用**思维链（COT）**分析错误原因。
   - **利用历史记录**：将 `correction_history` 传入 Prompt，让模型学习之前的错误，避免重蹈覆辙。
   - 识别错误类型：
     - 语义错误：字段错误、条件错误、JOIN错误、聚合错误、排序错误等
     - 执行错误：schema.mismatch、join.logic_error、filter.condition_error等
   - 推理过程后必须包含 `CORRECTION_PLAN:` 段，给出修正步骤。
   - 输出 `correction_plan`。

7. **correction_plan → correction_sql**（**新增节点**）
   - 严格按照 `correction_plan` 生成修正后的SQL。
   - 记录本次纠错到 `correction_history`。
   - 输出新的 `sql_draft`。
   - 回到 `validate_sql` 重新验证。

8. **finalize**
   - 将 `final_sql` 写入状态，并输出可序列化结果（包括修订历史与执行摘要）。

### 修订策略细则

**与旧版本的主要区别**：
- ❌ **删除**：`revise_sql` 节点（直接修订SQL）
- ✅ **新增**：`subproblem` 节点（问题分解）
- ✅ **新增**：`sql_plan` 节点（COT查询计划）
- ✅ **新增**：`correction_plan` + `correction_sql` 两阶段纠错（先分析错误，再修正SQL）

**纠错策略**：
- **两阶段验证**：先进行语义验证（SQL→Text 反向翻译 + 语义一致性判断），再执行验证，提前发现语义错误。
- **两阶段纠错**：先生成纠错计划（COT推理），再基于计划修正SQL，避免盲目修改。
- **错误分类**：
  - 语义错误：字段错误、条件错误、JOIN错误、聚合错误、排序错误、限制错误
  - 执行错误：schema不匹配、JOIN错误、过滤错误、聚合错误、输出错误、语法错误、语义错误
- **COT提示词要求**：
  - `sql_plan`：末尾必须有 `FINAL_PLAN:` 段
  - `correction_plan`：末尾必须有 `CORRECTION_PLAN:` 段
  - `semantic_validate`：返回JSON格式，包含 `explanation`, `semantic_match`, `issues`
- 修订次数受 `max_revisions` 限制，超过后记录失败并返回最后一次 SQL 与错误信息。

## 六、安全与限制

- **只读执行**：禁止 INSERT/UPDATE/DELETE/PRAGMA 等可能修改或泄露敏感信息的操作。
- **行数限制**：通过配置 `SQL_MAX_ROWS` 强制 `LIMIT`。
- **超时**：SQL 执行与 LLM 请求都应施加超时（如 `REQUEST_TIMEOUT`）。
- **输入清洗**：对 LLM 返回的 SQL 做白名单检查（仅允许 SELECT、WITH、LIMIT、ORDER BY、JOIN、UNION 等）并检测显式 `ATTACH`, `DROP` 等危险关键词。

## 七、配置项（`src/agent/config.py`）

- `PROVIDER`：`ollama` 或 `openai_compatible`。
- `MODEL_NAME`、`OPENAI_BASE_URL`、`OPENAI_API_KEY`：LLM 配置。
- `SQL_MAX_ROWS`、`REQUEST_TIMEOUT`、`MAX_TOKENS`：性能与安全参数。
- `MAX_REVISIONS`：修订上限。


