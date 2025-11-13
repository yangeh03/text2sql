# -*- coding: utf-8 -*-
"""
配置与消融：
- 统一从 .env 与 CLI 读取，CLI 覆盖 .env。
- 主要用于：选择 LLM 后端、开关工具/反思/验证等模块、资源限制。
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _to_bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class Settings:
    provider: str = os.getenv("PROVIDER", "ollama")  # ollama | openai_compatible
    api_key: str = os.getenv("OPENAI_API_KEY", "ollama")
    base_url: str = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    model: str = os.getenv("MODEL_NAME", "llama3.1")

    # ablations / modules
    enable_reflection: bool = _to_bool(os.getenv("ENABLE_REFLECTION"), False)
    enable_validation: bool = _to_bool(os.getenv("ENABLE_VALIDATION"), False)
    enable_memory: bool = _to_bool(os.getenv("ENABLE_MEMORY"), False)

    # 语义验证（反向翻译）相关开关与阈值
    # ENABLE_SEMANTIC_VALIDATE: 是否在执行验证前进行“SQL→自然语言反向翻译 + 语义一致性判定”
    # SEMANTIC_SCORE_THRESHOLD: 语义判定通过的分数阈值（0~1），仅供实现时参考（当前由 LLM 判定返回 pass/score）
    # SEMANTIC_GATE_MODE: 语义闸门模式
    #   - before_exec: 通过后继续走 validate_sql（默认，不改变原有流程）
    #   - finalize_on_pass: 通过后直接 finalize（课堂 Demo/快速模式，可选）
    enable_semantic_validate: bool = _to_bool(os.getenv("ENABLE_SEMANTIC_VALIDATE"), False)
    semantic_score_threshold: float = float(os.getenv("SEMANTIC_SCORE_THRESHOLD", "0.7"))
    semantic_gate_mode: str = os.getenv("SEMANTIC_GATE_MODE", "before_exec")

    # resource/safety
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "60"))

    # sql safety
    sql_max_rows: int = int(os.getenv("SQL_MAX_ROWS", "200"))
    sql_hard_limit_inject: bool = _to_bool(os.getenv("SQL_HARD_LIMIT_INJECT"), True)


SETTINGS = Settings()


# ============================================================
# 评测配置参数
# ============================================================
@dataclass
class EvalConfig:
    """评测配置（支持 Spider 和 BIRD 数据集）"""
    # 数据集类型：'spider' 或 'bird'（仅用于标识）
    dataset_type: str = "spider"
    
    # 数据文件路径
    # data_file: str = "spider_data/train_spider.json"
    data_file: str = "spider_data/test.json"
    # Schema文件路径
    # schema_file: str = "spider_data/tables.json"
    schema_file: str = "spider_data/test_tables.json"
    # 输出SQL文件路径
    output_file: str = "outputs/predictions.sql"
    # 数据库文件目录路径
    # database_dir: str = "spider_data/database"
    database_dir: str = "spider_data/test_database"
    
    # 最多处理的样本数（None表示全部）
    max_samples: int | None = None
    # 最大修订次数
    max_revisions: int = 3


# 默认配置实例（Spider）
EVAL_CONFIG = EvalConfig()

# BIRD 数据集配置示例（取消注释以使用）
# EVAL_CONFIG = EvalConfig(
#     dataset_type="bird",
#     data_file="bird_data/dev.json",
#     schema_file="bird_data/dev_tables.json",
#     database_dir="bird_data/dev_databases",
#     max_samples=3,
#     max_revisions=3
# )
