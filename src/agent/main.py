# -*- coding: utf-8 -*-
"""
主程序入口：运行评测
配置参数在 config.py 的 EVAL_CONFIG 中修改
支持 Spider 和 BIRD 数据集
"""
from __future__ import annotations
from pathlib import Path
import sys
import json  # 持久化语义报告（可选）

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.graph import build_graph, AgentState
from src.agent.config import EVAL_CONFIG, SETTINGS  # SETTINGS 用于读取语义闸门开关
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
    
    results = []
    # 若开启语义验证，则准备输出语义报告目录
    report_dir = Path("outputs/semantic_reports")
    if SETTINGS.enable_semantic_validate:
        report_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    error_count = 0
    
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
            results.append("SELECT 1;  -- ERROR: No schema found")
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
            
            results.append(final_sql)

            # 若启用语义闸门，将每个样本的语义信息写入报告（便于课堂演示与排错）
            if SETTINGS.enable_semantic_validate:
                try:
                    semantic_payload = {
                        "db_id": db_id,
                        "index": idx,
                        "question": question,
                        "sql": final_sql,
                        "semantic": {
                            "back_translation": final_state.get("back_translation", {}),
                            "score": final_state.get("semantic_score", 0.0),
                            "pass": final_state.get("semantic_pass", False),
                            "reason": final_state.get("semantic_reason", ""),
                        },
                    }
                    with open(report_dir / f"{idx:04d}_{db_id}.json", "w", encoding="utf-8") as rf:
                        rf.write(json.dumps(semantic_payload, ensure_ascii=False, indent=2))
                except Exception:
                    # 写报告失败不影响主流程
                    pass
            
            # 显示修订历史
            revision_history = final_state.get("revision_history", [])
            if revision_history:
                print(f"  📝 修订次数: {len(revision_history)}")
        
        except Exception as e:
            print(f"  ❌ 执行出错: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(f"SELECT 1;  -- ERROR: {str(e)}")
            error_count += 1
    
    # 写出结果
    print(f"\n{'='*80}")
    print(f"💾 写出结果到: {config.output_file}")
    
    with open(config.output_file, 'w', encoding='utf-8') as f:
        for sql in results:
            f.write(sql + "\n")
    
    # 统计
    print(f"\n📊 评测统计:")
    print(f"{'='*80}")
    print(f"  ✅ 成功: {success_count}/{len(questions)}")
    print(f"  ❌ 失败: {error_count}/{len(questions)}")
    print(f"  📈 成功率: {success_count/len(questions)*100:.1f}%")
    print(f"{'='*80}")
    
    print(f"\n✅ 完成！结果已保存到 {config.output_file}")
    print(f"\n💡 提示: 可以使用官方评测脚本进行 EM/EX 评估")

    # ============================================================
    # 自动聚合指标与报表（report_metrics）
    # - 若开启了语义闸门且生成了语义报告，则汇总生成 summary.json / details.csv / report.md
    # - 缺少任一输入（如未开启语义闸门或未有日志）也不报错，尽力输出可用结果
    # ============================================================
    try:
        from src.agent.report_metrics import generate_reports, Args
        reports_dir = Path("outputs/semantic_reports")
        logs_file = Path("outputs/logs/semantic_smoke.log")
        preds_file = Path(config.output_file)
        out_dir = Path("outputs/reports")
        summary, _ = generate_reports(Args(
            reports_dir=reports_dir,
            log_file=logs_file if logs_file.exists() else None,
            pred_file=preds_file if preds_file.exists() else None,
            out_dir=out_dir,
        ))
        print("\n[report_metrics] 自动生成汇总完成，产物位于 outputs/reports/")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception as e:
        # 聚合失败不影响主流程
        print(f"\n[report_metrics] 跳过（原因：{str(e)}）")


if __name__ == "__main__":
    run_evaluation()
