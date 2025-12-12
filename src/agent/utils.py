# -*- coding: utf-8 -*-
"""
Utility functions:
- Load datasets (supports Spider and BIRD).
- Load schema information.
- Other helper functionality.
"""
from __future__ import annotations
import json
from typing import Dict, Any


def load_dataset(data_path: str, dataset_type: str = "spider") -> list:
    """
    Load a dataset (supports Spider and BIRD).

    Args:
        data_path: Path to the data file.
        dataset_type: Dataset type, either 'spider' or 'bird'.

    Returns:
        List of question items.
    """
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # BIRD and Spider formats are mostly the same; some field names differ.
    # The BIRD dataset additionally contains a question_id field.
    return data


def load_schemas(schema_path: str, dataset_type: str = "spider") -> Dict[str, Any]:
    """
    Load database schema information (supports Spider and BIRD).

    Args:
        schema_path: Path to the schema file.
        dataset_type: Dataset type, either 'spider' or 'bird'.

    Returns:
        Mapping from db_id to schema_info.
    """
    with open(schema_path, 'r', encoding='utf-8') as f:
        schemas = json.load(f)

    # Convert to a mapping from db_id -> schema_info
    schema_dict = {}
    for schema in schemas:
        db_id = schema.get('db_id')
        if db_id:
            schema_dict[db_id] = schema
    
    return schema_dict
