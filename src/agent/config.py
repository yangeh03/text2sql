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
    max_samples: int | None = 3
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
