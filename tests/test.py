# -*- coding: utf-8 -*-
"""
测试脚本：验证重构后的系统是否正常工作
"""
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.graph import build_graph, AgentState
from src.agent.config import EVAL_CONFIG
from src.agent.utils import load_schemas


def test_basic_workflow():
    """测试基本工作流程"""
    print("="*80)
    print(f"测试1: 基本工作流程 - 简单查询 ({EVAL_CONFIG.dataset_type.upper()} 数据集)")
    print("="*80)
    
    # 加载schema
    schema_dict = load_schemas(EVAL_CONFIG.schema_file, EVAL_CONFIG.dataset_type)
    
    # 构建图
    graph = build_graph()
    
    # 测试用例
    test_case = {
        "question": "How many singers are there?",
        "db_id": "concert_singer",
    }
    
    schema_info = schema_dict.get(test_case["db_id"], {})
    
    initial_state = AgentState(
        question=test_case["question"],
        db_id=test_case["db_id"],
        schema_info=schema_info,
        data_dir=EVAL_CONFIG.database_dir,
        max_revisions=3
    )
    
    final_state = graph.invoke(initial_state)
    
    # LangGraph 返回的是字典格式的状态
    final_sql = final_state.get("final_sql", "")
    revision_history = final_state.get("revision_history", [])
    execution_result = final_state.get("execution_result", {})
    
    print(f"\n✅ 最终SQL: {final_sql}")
    print(f"📝 修订历史: {len(revision_history)} 次")
    
    assert final_sql, "应该生成SQL"
    assert execution_result.get('status') == 'ok', "SQL应该执行成功"
    
    print("\n✅ 测试1通过！\n")


def test_revision_workflow():
    """测试修订工作流程"""
    print("="*80)
    print(f"测试2: 修订工作流程 - 复杂查询 ({EVAL_CONFIG.dataset_type.upper()} 数据集)")
    print("="*80)
    
    # 加载schema
    schema_dict = load_schemas(EVAL_CONFIG.schema_file, EVAL_CONFIG.dataset_type)
    
    # 构建图
    graph = build_graph()
    
    # 测试用例 - 可能需要JOIN的查询
    test_case = {
        "question": "What are the names of singers who have had concerts?",
        "db_id": "concert_singer",
    }
    
    schema_info = schema_dict.get(test_case["db_id"], {})
    
    initial_state = AgentState(
        question=test_case["question"],
        db_id=test_case["db_id"],
        schema_info=schema_info,
        data_dir=EVAL_CONFIG.database_dir,
        max_revisions=3
    )
    
    final_state = graph.invoke(initial_state)
    
    # LangGraph 返回的是字典格式的状态
    final_sql = final_state.get("final_sql", "")
    revision_history = final_state.get("revision_history", [])
    
    print(f"\n✅ 最终SQL: {final_sql}")
    print(f"📝 修订历史: {len(revision_history)} 次")
    
    # 显示修订历史
    if revision_history:
        print("\n修订历史:")
        for i, rev in enumerate(revision_history, 1):
            print(f"  [{i}] SQL: {rev['sql'][:80]}...")
            print(f"      结果: {rev['result'].get('status')} - {rev['result'].get('message', rev['result'].get('error', ''))}")
    
    assert final_sql, "应该生成SQL"
    
    print("\n✅ 测试2通过！\n")


def test_multiple_databases():
    """测试多个数据库"""
    print("="*80)
    print(f"测试3: 多数据库测试 ({EVAL_CONFIG.dataset_type.upper()} 数据集)")
    print("="*80)
    
    # 加载schema
    schema_dict = load_schemas(EVAL_CONFIG.schema_file, EVAL_CONFIG.dataset_type)
    
    # 构建图
    graph = build_graph()
    
    # 测试不同的数据库
    test_cases = [
        {
            "question": "How many singers?",
            "db_id": "concert_singer",
        },
        {
            "question": "List all stadium names.",
            "db_id": "concert_singer",  # 这个数据库也有stadium表
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        print(f"DB: {test_case['db_id']}")
        print(f"问题: {test_case['question']}")
        
        schema_info = schema_dict.get(test_case["db_id"], {})
        
        initial_state = AgentState(
            question=test_case["question"],
            db_id=test_case["db_id"],
            schema_info=schema_info,
            data_dir=EVAL_CONFIG.database_dir,
            max_revisions=3
        )
        
        final_state = graph.invoke(initial_state)
        
        final_sql = final_state.get("final_sql", "")
        
        print(f"✅ 生成SQL: {final_sql}")
        
        assert final_sql, f"测试用例{i}应该生成SQL"
    
    print("\n✅ 测试3通过！\n")


if __name__ == "__main__":
    print("\n🧪 开始运行测试...\n")
    print(f"📊 使用数据集: {EVAL_CONFIG.dataset_type.upper()}")
    print(f"📁 Schema文件: {EVAL_CONFIG.schema_file}")
    print(f"📁 数据库目录: {EVAL_CONFIG.database_dir}\n")
    
    try:
        test_basic_workflow()
        test_revision_workflow()
        test_multiple_databases()
        
        print("="*80)
        print("🎉 所有测试通过！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
