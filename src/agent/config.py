# -*- coding: utf-8 -*-
"""
Configuration and ablation settings:
- Unified reading from .env and CLI (CLI overrides .env).
- Mainly used to choose the LLM backend, toggle tools/reflection/validation modules, and set resource limits.
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
    model: str = os.getenv("MODEL_NAME", "qwen3:8b")

    # resource/safety
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "60"))

    # sql safety
    sql_max_rows: int = int(os.getenv("SQL_MAX_ROWS", "200"))
    sql_hard_limit_inject: bool = _to_bool(os.getenv("SQL_HARD_LIMIT_INJECT"), True)


SETTINGS = Settings()


# ============================================================
# Evaluation configuration parameters
# ============================================================
@dataclass
class EvalConfig:
    """Evaluation configuration (supports Spider and BIRD datasets)."""
    # Dataset type: 'spider' or 'bird' (for identification only)
    dataset_type: str = "spider"

    # Data file path
    data_file: str = "spider_data/test.json"
    # Schema file path
    schema_file: str = "spider_data/test_tables.json"
    # Output SQL file path
    output_file: str = "outputs/spider_test_predictions.sql"
    # Database directory path
    database_dir: str = "spider_data/test_database"

    # Maximum number of samples to process (None means all)
    max_samples: int | None = 1
    # Maximum number of revisions
    max_revisions: int = 3


# Default configuration instance (Spider)
EVAL_CONFIG = EvalConfig()

# BIRD dataset configuration example (uncomment to use)
# EVAL_CONFIG = EvalConfig(
#     dataset_type="bird",
#     data_file="bird_data/dev.json",
#     schema_file="bird_data/dev_tables.json",
#     database_dir="bird_data/dev_databases",
#     max_samples=3,
#     max_revisions=3
# )
