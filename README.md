# Talk2DB: 基于 LangGraph 的 Text-to-SQL Agent

本仓库是 DSAA6000R Group 8 的课程项目实现，对应报告见 [pre/Group8_Report.pdf](pre/Group8_Report.pdf)。项目围绕 `Talk2DB` 框架展开，目标是提升 Text-to-SQL 在复杂查询上的稳定性与语义正确性。

与基础的 ReAct 式 SQL 修订流程相比，Talk2DB 在生成前加入了查询规划，在生成后加入了语义反向验证与执行检查，形成一个更完整的闭环：

`schema linking / content retrieval -> subproblem decomposition -> query planning -> SQL generation -> SQL2Text semantic validation -> execution checking -> self-correction`

## 项目亮点

- 查询规划：先做子问题分解和结构化 Query Plan，再生成 SQL。
- 语义回查：将 SQL 反向翻译成自然语言，检查是否与原问题语义一致。
- 执行校验：在真实 SQLite 数据库上执行生成结果，利用错误信息驱动修订。
- 多阶段闭环：采用 LangGraph 状态图串联预处理、生成、验证与纠错。
- 兼容多后端：通过 OpenAI SDK 统一接入 Ollama 和 OpenAI-compatible API。
- 支持多个数据集：当前代码支持 Spider 和 BIRD 两种数据集配置。

## 方法概览

根据报告，Talk2DB 的核心由三部分组成：

### 1. 生成前上下文构建

- `get_database_schema`：构造完整数据库 schema。
- `schema_linker`：筛选与问题相关的表和列。
- `content_retriever`：抽取示例值，帮助模型更准确地写过滤条件。
- `subproblem`：将复杂问题分解为 SQL 子任务。
- `sql_plan`：基于子任务、schema 和示例值生成结构化查询计划。

### 2. SQL 生成

- `generate_sql` 节点基于 query plan 和相关 schema 生成初始 SQL。

### 3. 双重验证与纠错

- `semantic_validator`：将 SQL 反向翻译为自然语言，检查语义一致性。
- `sql_executor`：在目标 SQLite 数据库上运行 SQL，检查执行错误或空结果。
- `correction_plan` + `correction_sql`：根据语义问题或执行错误生成纠错计划，并迭代修正 SQL。

当前实现对应的主流程为：

`preprocess -> subproblem -> sql_plan -> generate_sql -> validate_sql -> correction_plan -> correction_sql -> validate_sql -> finalize`

## 仓库结构

```text
.
├── README.md
├── ARCHITECTURE.md
├── pre/
│   └── Group8_Report.pdf
├── src/agent/
│   ├── config.py
│   ├── graph.py
│   ├── llm.py
│   ├── main.py
│   ├── prompts.py
│   ├── tools.py
│   └── utils.py
├── outputs/
│   └── ...
├── result/
│   └── ...  # 历史评测结果与消融实验产物
├── spider_data/
└── bird_data/
```

关键文件说明：

- `src/agent/graph.py`：LangGraph 状态机定义。
- `src/agent/tools.py`：schema 获取、schema linking、内容检索、语义验证、SQL 执行。
- `src/agent/prompts.py`：各阶段 Prompt 模板。
- `src/agent/config.py`：LLM 与评测配置。
- `src/agent/main.py`：评测入口。
- `ARCHITECTURE.md`：更详细的架构说明。

## Report 中的实验结论

报告在 Spider development set 上给出了如下消融结果。下面的数值直接整理自 `Group8_Report.pdf` Table 1：

| Variant | 说明 | EX(All) | EM(All) | EX 提升 |
| --- | --- | ---: | ---: | ---: |
| Baseline (ReAct only) | 仅保留基础自修订流程 | 0.593 | 0.580 | - |
| Talk2DB w/o BackTranslate | 保留 Query Plan，移除 SQL2Text 回查 | 0.620 | 0.553 | +4.55% |
| Talk2DB w/o Query Plan | 保留回查，移除 Query Plan | 0.700 | 0.640 | +18.04% |
| Talk2DB (Full) | Query Plan + Back-Verification + Execution Checking | 0.720 | 0.673 | +21.42% |

报告中的主要结论：

- Query Planning 和 Subproblem Decomposition 对复杂查询帮助最明显。
- SQL2Text Back-Verification 能进一步减少“能执行但语义不对”的情况。
- 完整框架相比基线在 EX 上有显著提升。

## Report 中的实验设置

以下信息整理自报告正文，用于帮助理解论文式结果的来源：

- 数据集：Spider development set。
- 评测方式：zero-shot，不做任务特定微调。
- 基座模型：Qwen2.5-7B。
- 框架：LangGraph。
- 设备环境：MacBook Pro M4, macOS 15.6。
- 修订预算：最多 3 轮迭代修订。

说明：以上是报告中的实验设置；当前仓库的默认运行配置以 `src/agent/config.py` 和 `.env` 为准。

## 环境准备

建议使用 Python 3.10 及以上版本。

```bash
git clone <your-repo-url>
cd text2sql-1

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

## LLM 配置

### 方案 A：Ollama

```bash
ollama pull qwen2.5:7b
```

`.env` 示例：

```env
PROVIDER=ollama
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL_NAME=qwen2.5:7b
```

### 方案 B：OpenAI-compatible API

```env
PROVIDER=openai_compatible
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
```

说明：

- 当前仓库通过 `openai` SDK 统一发起请求。
- 建议总是显式配置 `.env`，不要依赖代码中的兜底默认值。

## 数据准备

仓库中的 `spider_data/` 和 `bird_data/` 当前只是占位目录，需要你自行下载数据集并放到对应位置。

### Spider

需要至少准备以下内容：

```text
spider_data/
├── test.json
├── test_tables.json
└── test_database/
    └── <db_id>/
        └── <db_id>.sqlite
```

数据集下载地址：

- Spider: https://yale-lily.github.io/spider

### BIRD

一个典型目录结构如下：

```text
bird_data/
├── dev.json
├── dev_tables.json
└── dev_databases/
    └── <db_id>/
        └── <db_id>.sqlite
```

数据集下载地址：

- BIRD: https://bird-bench.github.io/

## 运行方式

### 1. 配置评测参数

编辑 `src/agent/config.py` 中的 `EVAL_CONFIG`。当前默认配置是 Spider：

```python
EVAL_CONFIG = EvalConfig(
    dataset_type="spider",
    data_file="spider_data/test.json",
    schema_file="spider_data/test_tables.json",
    output_file="outputs/spider_test_predictions.sql",
    database_dir="spider_data/test_database",
    max_samples=1,
    max_revisions=3,
)
```

如果要切到 BIRD，可改为：

```python
EVAL_CONFIG = EvalConfig(
    dataset_type="bird",
    data_file="bird_data/dev.json",
    schema_file="bird_data/dev_tables.json",
    database_dir="bird_data/dev_databases",
    output_file="outputs/bird_dev_predictions.sql",
    max_samples=3,
    max_revisions=3,
)
```

### 2. 启动评测

```bash
python src/agent/main.py
```

程序会：

- 读取数据集与 schema。
- 对每个问题运行完整 LangGraph 流程。
- 将最终 SQL 写入 `EVAL_CONFIG.output_file` 指定的位置。

### 3. 查看结果

- 预测 SQL 输出路径由 `EVAL_CONFIG.output_file` 决定。
- `result/` 目录保存了历史实验产物。
- `outputs/reports/` 下保留了仓库中的示例报告摘要文件。

## 复现与使用注意事项

- 当前仓库没有内置 `tests/` 目录，因此不能使用 `python tests/test.py` 这样的命令。
- 当前仓库也没有内置官方 Spider/BIRD 评测脚本；如果要计算标准 EM/EX，需要额外接入官方 evaluator。
- 报告中的主结果来自 Spider development set；而当前代码默认示例配置指向 `spider_data/test.json`。复现实验前请先确认数据切分是否一致。
- 如果数据库文件缺失，`content_retriever` 和 `sql_executor` 无法发挥完整作用。
- SQL 执行器只允许 `SELECT` 查询，并会自动注入 `LIMIT` 以控制返回行数。

## 已知局限

根据报告中的分析，目前框架仍有以下主要限制：

- 在多跳 Join、桥接表较多的 schema 上，查询规划仍可能不足。
- SQL2Text 验证对细粒度逻辑差异还不够敏感，例如 `>` vs `>=`、`IN` vs `NOT IN`。
- 在特别复杂的问题上，可能因为超时或修订预算限制而退化为较弱的结果。

## 补充文档

- 课程报告：[pre/Group8_Report.pdf](pre/Group8_Report.pdf)
- 架构说明：[ARCHITECTURE.md](ARCHITECTURE.md)
