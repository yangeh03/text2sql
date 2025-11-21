# Text-to-SQL Agent - LangGraph 实现

本项目实现了基于 **LangGraph 状态机** 的 Text-to-SQL 智能体，采用 **预处理 → 生成 → 验证 → 修订** 的闭环工作流。

## 🎯 核心特性

- ✅ **验证-修订闭环**：自动执行SQL并根据错误修订，最多3次迭代
- 🧠 **语义一致性检查**：基于反向翻译（SQL→Text）的语义验证，提前发现逻辑错误
- 🎨 **状态驱动架构**：使用 LangGraph 状态图，流程清晰易扩展
- 🛡️ **安全执行**：只读SQL执行、行数限制、超时控制
- 🔍 **可观测性**：完整的修订历史、步骤追踪、ReAct 输出
- 🚀 **本地/云端模型**：支持 Ollama 和 OpenAI 兼容 API

> 💡 **设计理念**：通过执行引导（Execution-Guided）和自动修订提升 SQL 生成质量

---

## 📖 工作流程

系统采用七节点流程图（**已重构为多阶段推理架构**）：

```
START 
  ↓
preprocess (预处理)
  ├─ 获取完整数据库 schema (CREATE TABLE 语句)
  ├─ 模式链接：筛选相关表和列
  └─ 检索示例值：从数据库抽取实体值
  ↓
subproblem (子问题分解) 🆕
  └─ 使用 LLM 将问题分解为多个 SQL 子句
  ↓
sql_plan (SQL计划生成) 🆕
  └─ 使用 COT 思维链生成查询计划
  └─ 输出必须包含 FINAL_PLAN: 段
  ↓
generate_sql (生成SQL)
  └─ 基于计划和 schema 生成 SQL 草稿
  ↓
validate_sql (验证SQL)
  ├─ 语义验证：SQL→Text反向翻译，检查语义一致性
  └─ 执行验证：在真实数据库上执行 SQL
  ↓
[条件路由]
  ├─ 语义/执行成功且有数据 → finalize (完成)
  ├─ 语义/执行失败或空结果 → correction_plan (纠错计划) 🆕
  └─ 达到最大修订次数 → finalize (强制完成)
  ↓
correction_plan (纠错计划生成) 🆕
  ├─ 使用 COT 分析错误类型
  ├─ 识别错误分类（schema/join/filter/aggregation等）
  └─ 输出必须包含 CORRECTION_PLAN: 段
  ↓
correction_sql (纠错SQL生成) 🆕
  └─ 严格按照纠错计划修正 SQL
  ↓
validate_sql (重新验证)
  └─ 循环直到成功或达到最大次数
  ↓
finalize (最终化)
  └─ 设置 final_sql
  ↓
END
```

### 修订策略

- **两阶段纠错**：`correction_plan`（分析错误）→ `correction_sql`（修正SQL）
- **错误分类体系**：
  - `schema.mismatch`：表名、列名不存在或模糊
  - `join.logic_error`：JOIN条件错误、外键错误、多余的表
  - `filter.condition_error`：WHERE/HAVING子句错误
  - `aggregation.grouping_error`：聚合函数或GROUP BY错误
  - `select.output_error`：SELECT列错误（多余、缺失、顺序错误）
  - `syntax.structural_error`：语法错误或缺少必需子句
  - `intent.semantic_error`：语法正确但不符合用户意图
- **终止保护**：最多修订 3 次，避免无限循环

---

## 🚀 快速开始

### 1. 环境准备

建议 Python 版本 >= 3.10

```bash
# 克隆项目
git clone <your-repo-url>
cd data-agent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env  # 然后编辑 .env
```

### 2. 配置 LLM 后端

**选项 A：本地 Ollama（推荐）**

```bash
# 安装 Ollama: https://ollama.com
ollama pull qwen2.5:7b

# 在 .env 中配置：
PROVIDER=ollama
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL_NAME=qwen2.5:7b
```

**选项 B：OpenAI 兼容 API**

```env
PROVIDER=openai_compatible
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
```

### 3. 数据准备
**Spider 数据集**
1. 下载 Spider 数据集：[Spider 官网](https://yale-lily.github.io/spider)
2. 解压到 `spider_data/` 目录
  
**BIRD 数据集**
1. 下载 BIRD 数据集：[BIRD 官网](https://bird-bench.github.io/)
2. 解压到 `bird_data/` 目录

### 4. 运行测试

```bash
# 运行集成测试（推荐先运行）
python tests/test.py

# 预期输出：
# 🧪 开始运行测试...
# ✅ 测试1通过！
# ✅ 测试2通过！
# ✅ 测试3通过！
# 🎉 所有测试通过！
```

### 5. 运行评测

**配置数据集**

编辑 `src/agent/config.py` 中的 `EVAL_CONFIG`：

**Spider 数据集（默认）：**
```python
# 默认配置实例（Spider）
EVAL_CONFIG = EvalConfig()
```

**切换到 BIRD 数据集：**
取消注释 BIRD 配置：
```python
# BIRD 数据集配置示例（取消注释以使用）
EVAL_CONFIG = EvalConfig(
    dataset_type="bird",
    data_file="bird_data/dev.json",
    schema_file="bird_data/dev_tables.json",
    database_dir="bird_data/dev_databases",
    max_samples=3,
    max_revisions=3
)
```

**运行评测：**

```bash
python src/agent/main.py
```

**调整处理样本数：**
```python
EVAL_CONFIG = EvalConfig(
    max_samples=100,  # 处理 100 个样本
    # max_samples=None,  # 处理全部样本
)
```

---

## 📊 示例输出

```
================================================================================
[1/5] DB: concert_singer
问题: How many singers do we have?

📋 预处理阶段 - Preprocess
  🔧 获取数据库模式...
  ✓ 成功获取 4 个表的模式
  🔧 模式链接，筛选相关表...
  ✓ 筛选出相关表: ['singer', 'singer_in_concert']
  理由: 基于问题关键词匹配到相关表：singer, singer_in_concert
  🔧 检索示例值...
  ✓ 检索到 10 个示例值
  示例: ['Joe Sharp', 'Timbaland', 'Justin Brown']

🔨 SQL生成阶段 - Generate SQL
  ✓ 生成SQL: SELECT COUNT(*) FROM singer

✅ SQL验证阶段 - Validate SQL
  ✓ 执行成功，返回 1 行

✅ SQL验证成功，接受结果
  ✅ 生成SQL: SELECT COUNT(*) FROM singer
  📝 修订次数: 1
```

带修订的示例：

```
📋 预处理阶段 - Preprocess
  ✓ 成功获取 schema 和示例值

� SQL生成阶段 - Generate SQL
  ✓ 生成SQL: SELECT Name FROM singer WHERE Country = 'USA'

✅ SQL验证阶段 - Validate SQL
  ✗ 执行失败: no such column: Name

� SQL修订阶段 - Revise SQL (第 1 次)
  ✓ 修订后SQL: SELECT name FROM singer WHERE country = 'USA'

✅ SQL验证阶段 - Validate SQL
  ✓ 执行成功，返回 3 行

✅ SQL验证成功，接受结果
  📝 修订次数: 2
```

---

## 🏗️ 架构设计

### 项目结构

```
data-agent/
├── src/
│   └── agent/
│       ├── __init__.py           # 包初始化文件
│       ├── main.py               # 主程序入口
│       ├── graph.py              # LangGraph 状态图（核心流程）
│       ├── tools.py              # 四个核心工具实现
│       ├── prompts.py            # 提示词和工具规范
│       ├── llm.py                # LLM 客户端封装
│       ├── config.py             # 配置管理（LLM + 评测配置）
│       └── utils.py              # 工具函数（加载数据等）
├── tests/
│   └── test.py               # 集成测试
├── spider_data/              # Spider 数据集
│   ├── dev.json              # 开发集（1034条样本）
│   ├── dev_gold.sql          # 开发集标准答案
│   ├── train_spider.json     # 训练集（Spider部分）
│   ├── train_others.json     # 训练集（其他数据源）
│   ├── train_gold.sql        # 训练集标准答案
│   ├── test.json             # 测试集
│   ├── test_gold.sql         # 测试集标准答案
│   ├── tables.json           # 数据库 schema 定义
│   ├── test_tables.json      # 测试集数据库 schema
│   ├── README.txt            # Spider 数据集说明
│   ├── database/             # 训练/开发集 SQLite 数据库文件
│   │   ├── academic/
│   │   │   └── academic.sqlite
│   │   ├── concert_singer/
│   │   │   └── concert_singer.sqlite
│   │   ├── ... (共140+个数据库)
│   └── test_database/        # 测试集 SQLite 数据库文件
│       ├── academic/
│       └── ... (共20+个数据库)
├── bird_data/                # BIRD 数据集
│   ├── dev.json              # 开发集（1533条样本）
│   ├── dev_tables.json       # 数据库 schema 定义
│   ├── dev_tied_append.json  # 附加评测数据
│   ├── dev.sql               # 开发集标准答案
│   └── dev_databases/        # SQLite 数据库文件
│       ├── california_schools/
│       │   ├── california_schools.sqlite
│       │   └── database_description/  # 数据库描述文档
│       ├── formula_1/
│       │   ├── formula_1.sqlite
│       │   └── database_description/
│       └── ... (共11个数据库)
├── outputs/
│   └── predictions.sql       # 生成的 SQL 预测结果
├── .env.example              # 环境变量配置模板
├── .env                      # 环境变量配置（需自行创建）
├── .gitignore                # Git 忽略文件配置
├── README.md                 # 项目说明文档（本文件）
└── requirements.txt          # Python 依赖包列表
```

### 核心组件

#### 1. 状态模型 (AgentState)

```python
class AgentState(BaseModel):
    # 输入
    question: str                    # 自然语言问题
    db_id: str                       # 数据库 ID
    
    # 数据库信息
    db_schema: str                   # 完整 CREATE TABLE 语句
    relevant_schema: str             # 筛选后的相关表
    retrieved_values: list[str]      # 示例值
    
    # 计划与推理
    subproblems: str                 # 子问题分解
    sql_plan: str                    # SQL查询计划
    correction_plan: str             # 纠错计划
    
    # SQL 生成与验证
    sql_draft: str                   # 当前 SQL 草稿
    sql_nl_explanation: str          # SQL自然语言解释
    semantic_validation: dict        # 语义验证结果
    execution_result: dict           # 执行结果或错误
    revision_history: list[dict]     # 修订历史
    correction_history: list[dict]   # 纠错历史
    final_sql: str                   # 最终 SQL
    
    # 控制
    max_revisions: int = 3           # 最大修订次数
```

#### 2. 五个核心工具

| 工具 | 功能 | 实现方式 | 输入 | 输出 |
|------|------|----------|------|------|
| `get_database_schema` | 获取完整 schema | 基于规则 | db_id | CREATE TABLE 语句 |
| `schema_linker` | 筛选相关表 | **基于LLM** | question, schema | 相关表的 schema |
| `content_retriever` | 检索示例值 | **基于LLM+数据库** | question, schema, db_id | 关键值+示例值列表 |
| `semantic_validator` | 语义验证 | **基于LLM** | question, sql | 语义一致性报告 |
| `sql_executor` | 执行 SQL | 基于 SQLite | db_id, sql_query | 执行结果或错误 |

**💡 智能增强**：
- `schema_linker` 使用 LLM 智能识别问题相关的表，而非简单的关键词匹配
- `content_retriever` 先用 LLM 提取问题中的关键值，再从数据库检索示例数据
- 所有工具都有降级策略，确保在 LLM 失败时仍能正常工作

#### 3. LangGraph 节点

- **preprocess**: 调用前三个工具，准备 SQL 生成所需信息
- **subproblem**: 🆕 将问题分解为SQL子问题（WHERE, JOIN, GROUP BY等）
- **sql_plan**: 🆕 使用COT生成查询计划（含FINAL_PLAN段）
- **generate_sql**: 基于计划和 schema 生成 SQL
- **validate_sql**: 语义验证（SQL→Text）+ 执行验证
- **correction_plan**: 🆕 使用COT分析错误（结合纠错历史）并生成纠错计划（含CORRECTION_PLAN段）
- **correction_sql**: 🆕 按纠错计划修正SQL并记录历史
- **finalize**: 设置最终 SQL
- **decide_next_step**: 条件路由（修订 vs 结束）

---

## ⚙️ 配置说明

### 环境变量 (.env)

```env
# LLM 提供商
PROVIDER=ollama                          # ollama | openai_compatible
MODEL_NAME=qwen2.5:7b                    # 模型名称
OPENAI_BASE_URL=http://localhost:11434/v1 # API 端点
OPENAI_API_KEY=ollama                    # API 密钥

# 性能配置
MAX_TOKENS=1024                          # 最大生成 token 数
REQUEST_TIMEOUT=60                       # 请求超时（秒）

# SQL 安全配置
SQL_MAX_ROWS=200                         # 最大返回行数
SQL_HARD_LIMIT_INJECT=true               # 自动添加 LIMIT
```

### 推荐模型

| 模型 | 推理质量 | 速度 | 场景 |
|------|----------|------|------|
| qwen2.5:7b | ⭐⭐⭐⭐ | 🚀🚀🚀 | 开发调试 |
| qwen2.5:14b | ⭐⭐⭐⭐⭐ | 🚀🚀 | 高质量评测 |
| gpt-4o-mini | ⭐⭐⭐⭐⭐ | 🚀🚀🚀 | 生产环境 |

---

## 📚 相关资源

- **[Spider 官网](https://yale-lily.github.io/spider)** - Spider Text-to-SQL 数据集
- **[BIRD 官网](https://bird-bench.github.io/)** - BIRD Text-to-SQL 数据集
- **[LangGraph 文档](https://python.langchain.com/docs/langgraph)** - LangGraph 框架文档

---

## 🎯 项目特色

### 创新点

1. **验证-修订闭环**：不是一次性生成 SQL，而是通过执行验证并自动修订
2. **状态驱动架构**：使用 LangGraph 状态机，流程清晰、易于扩展
3. **智能模式链接**：使用 LLM 智能识别相关表，提升准确率
4. **混合内容检索**：LLM 提取关键值 + 数据库检索示例数据
5. **安全执行**：只读 SQL、行数限制、超时控制，保护数据库安全
6. **完整观测性**：修订历史、步骤追踪、ReAct 输出，便于调试

### 适用场景

- **Text-to-SQL 研究**：探索执行引导的 SQL 生成方法
- **多数据集评测**：支持 Spider 和 BIRD 数据集的高质量评测工具
- **LangGraph 学习**：学习如何设计状态机驱动的智能体
- **生产应用**：可靠的 Text-to-SQL 系统基础


---

## 📄 许可证

MIT License

---

## TODOLIST
- 配置fast llm 和 main llm  -->节省token
- 中文提示词转英文
