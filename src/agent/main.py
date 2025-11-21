# -*- coding: utf-8 -*-
"""
主程序入口：运行评测
配置参数在 config.py 的 EVAL_CONFIG 中修改
支持 Spider 和 BIRD 数据集
"""
from __future__ import annotations
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.graph import build_graph, AgentState
from src.agent.config import EVAL_CONFIG
from src.agent.utils import load_dataset, load_schemas


def run_evaluation():
    """
    运行评测（支持 Spider 和 BIRD 数据集）
    使用 EVAL_CONFIG 配置
    """
    # 读取配置
    config = EVAL_CONFIG
    
    dataset_name = config.dataset_type.upper()
    
    print("="*80)
    print(f"🚀 Text-to-SQL Agent - {dataset_name} 评测")
    print("="*80)
    print(f"📊 数据集类型: {config.dataset_type}")
    print(f"📋 数据集: {config.data_file}")
    print(f"📋 Schema: {config.schema_file}")
    print(f"📁 数据库目录: {config.database_dir}")
    print(f"💾 输出文件: {config.output_file}")
    if config.max_samples:
        print(f"⚠️  限制样本数: {config.max_samples}")
    print(f"🔄 最大修订次数: {config.max_revisions}")
    print("="*80)
    
    # 加载数据
    print(f"\n📋 加载数据集...")
    questions = load_dataset(config.data_file, config.dataset_type)
    
    print(f"📋 加载schema...")
    schemas = load_schemas(config.schema_file, config.dataset_type)
    
    if config.max_samples:
        questions = questions[:config.max_samples]
    
    print(f"📊 总共 {len(questions)} 个问题待处理\n")
    
    # 构建图
    graph = build_graph()
    
    # 准备输出
    output_path = Path(config.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    error_count = 0
    
    # 打开输出文件（写入模式）
    with open(config.output_file, 'w', encoding='utf-8') as output_file:
        # 处理每个问题
        for idx, item in enumerate(questions, 1):
            question = item.get("question", "")
            db_id = item.get("db_id", "")
            gold_sql = item.get("SQL", "") or item.get("query", "")  # BIRD用SQL，Spider用query
            
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(questions)}] DB: {db_id}")
            print(f"问题: {question}")
            
            # 获取schema信息
            schema_info = schemas.get(db_id, {})
            if not schema_info:
                print(f"  ⚠️  警告: 未找到 {db_id} 的schema信息")
                sql_result = "SELECT 1;  -- ERROR: No schema found"
                output_file.write(sql_result + "\n")
                output_file.flush()  # 立即刷新到磁盘
                error_count += 1
                continue
            
            try:
                # 构建初始状态
                initial_state = AgentState(
                    question=question,
                    db_id=db_id,
                    schema_info=schema_info,
                    data_dir=config.database_dir,
                    max_revisions=config.max_revisions
                )
                
                # 运行图
                final_state = graph.invoke(initial_state)
                
                # 获取最终SQL (LangGraph 返回的是字典)
                final_sql = final_state.get("final_sql", "") or final_state.get("sql_draft", "")
                
                if not final_sql:
                    print(f"  ⚠️  警告: 未生成SQL")
                    final_sql = "SELECT 1;  -- ERROR: No SQL generated"
                    error_count += 1
                else:
                    # 确保SQL是单行格式
                    final_sql = " ".join(final_sql.split())
                    success_count += 1
                    print(f"  ✅ 生成SQL: {final_sql[:100]}...")
                
                # 立即写入结果
                output_file.write(final_sql + "\n")
                output_file.flush()  # 立即刷新到磁盘
                
                # 显示修订历史
                revision_history = final_state.get("revision_history", [])
                if revision_history:
                    print(f"  📝 修订次数: {len(revision_history)}")
            
            except Exception as e:
                error_msg = str(e).replace('\n', ' ').replace('\r', ' ')
                print(f"  ❌ 执行出错: {error_msg}")
                import traceback
                traceback.print_exc()
                sql_result = f"SELECT 1;  -- ERROR: {error_msg}"
                output_file.write(sql_result + "\n")
                output_file.flush()  # 立即刷新到磁盘
                error_count += 1
    
    # 统计
    print(f"\n{'='*80}")
    print(f"💾 结果已实时写入: {config.output_file}")
    print(f"\n📊 评测统计:")
    print(f"{'='*80}")
    print(f"  ✅ 成功: {success_count}/{len(questions)}")
    print(f"  ❌ 失败: {error_count}/{len(questions)}")
    print(f"  📈 成功率: {success_count/len(questions)*100:.1f}%")
    print(f"{'='*80}")
    
    print(f"\n✅ 完成！结果已保存到 {config.output_file}")
    print(f"\n💡 提示: 可以使用官方评测脚本进行 EM/EX 评估")


if __name__ == "__main__":
    run_evaluation()
