# -*- coding: utf-8 -*-
"""
工具函数：
- 加载数据集（支持 Spider 和 BIRD）
- 加载 schema
- 其他辅助功能
"""
from __future__ import annotations
import json
from typing import Dict, Any


def load_dataset(data_path: str, dataset_type: str = "spider") -> list:
    """
    加载数据集（支持 Spider 和 BIRD）
    
    Args:
        data_path: 数据文件路径
        dataset_type: 数据集类型，'spider' 或 'bird'
    
    Returns:
        问题列表
    """
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # BIRD 和 Spider 的数据格式基本相同，只是字段名可能略有不同
    # BIRD 数据集包含额外的 question_id 字段
    return data


def load_schemas(schema_path: str, dataset_type: str = "spider") -> Dict[str, Any]:
    """
    加载数据库 schema 信息（支持 Spider 和 BIRD）
    
    Args:
        schema_path: Schema 文件路径
        dataset_type: 数据集类型，'spider' 或 'bird'
    
    Returns:
        db_id -> schema_info 的映射
    """
    with open(schema_path, 'r', encoding='utf-8') as f:
        schemas = json.load(f)
    
    # 转换为 db_id -> schema_info 的映射
    schema_dict = {}
    for schema in schemas:
        db_id = schema.get('db_id')
        if db_id:
            schema_dict[db_id] = schema
    
    return schema_dict


# 保持向后兼容的别名
def load_spider_data(data_path: str) -> list:
    """加载Spider数据集（向后兼容）"""
    return load_dataset(data_path, "spider")


def load_spider_schemas(schema_path: str) -> Dict[str, Any]:
    """加载Spider数据库schema信息（向后兼容）"""
    return load_schemas(schema_path, "spider")
