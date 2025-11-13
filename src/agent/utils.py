# -*- coding: utf-8 -*-
"""
工具函数：
- 加载数据集（支持 Spider 和 BIRD）
- 加载 schema
- 其他辅助功能
"""
from __future__ import annotations
import json
import re
from typing import Dict, Any, Tuple


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


# ============================================================
# 通用工具：安全解析 JSON（用于解析 LLM 返回的文本）
# ============================================================
def safe_parse_json(text: str) -> Tuple[Any, bool]:
    """
    安全地从文本中解析 JSON。

    场景：LLM 往往会在 JSON 外包裹解释性文本或 Markdown 代码块，本函数尝试多种方式提取合法 JSON。

    Args:
        text: 可能包含 JSON 的字符串

    Returns:
        (obj, ok):
            - obj: 解析得到的 Python 对象（dict/list/其他），或原始字符串备选
            - ok: 解析是否成功

    解析策略：
        1) 直接 json.loads
        2) 提取首个 "```json ... ```" 代码块内容再 loads
        3) 用正则匹配最外层 {...} 或 [...] 子串再 loads
        4) 失败时返回原文本与 False
    """
    if not isinstance(text, str):
        return text, True

    s = text.strip()
    # 方案1：直接解析
    try:
        return json.loads(s), True
    except Exception:
        pass

    # 方案2：截取 ```json 代码块
    code_block = re.search(r"```json\s*(.*?)```", s, flags=re.DOTALL | re.IGNORECASE)
    if code_block:
        snippet = code_block.group(1).strip()
        try:
            return json.loads(snippet), True
        except Exception:
            pass

    # 方案3：匹配第一个 JSON 对象/数组
    brace = re.search(r"\{[\s\S]*\}", s)
    bracket = re.search(r"\[[\s\S]*\]", s)
    # 优先选择更靠前的匹配
    candidate = None
    if brace and bracket:
        candidate = brace if brace.start() < bracket.start() else bracket
    else:
        candidate = brace or bracket
    if candidate:
        snippet = candidate.group(0)
        try:
            return json.loads(snippet), True
        except Exception:
            pass

    # 方案4：失败，返回原文
    return s, False
