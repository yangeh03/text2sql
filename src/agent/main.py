# -*- coding: utf-8 -*-
"""
Main entry point for running evaluation.
Modify configuration via EVAL_CONFIG in config.py.
Supports Spider and BIRD datasets.
"""
from __future__ import annotations
from pathlib import Path
import sys

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.graph import build_graph, AgentState
from src.agent.config import EVAL_CONFIG
from src.agent.utils import load_dataset, load_schemas


def run_evaluation():
    """
    Run evaluation (supports Spider and BIRD datasets).
    Uses configuration from EVAL_CONFIG.
    """
    # Read configuration
    config = EVAL_CONFIG
    
    dataset_name = config.dataset_type.upper()

    print("=" * 80)
    print(f"🚀 Text-to-SQL Agent - {dataset_name} Evaluation")
    print("=" * 80)
    print(f"📊 Dataset type: {config.dataset_type}")
    print(f"📋 Dataset file: {config.data_file}")
    print(f"📋 Schema: {config.schema_file}")
    print(f"📁 Database directory: {config.database_dir}")
    print(f"💾 Output file: {config.output_file}")
    if config.max_samples:
        print(f"⚠️  Sample limit: {config.max_samples}")
    print(f"🔄 Maximum revisions: {config.max_revisions}")
    print("=" * 80)

    # Load data
    print(f"\n📋 Loading dataset...")
    questions = load_dataset(config.data_file, config.dataset_type)
    
    print(f"📋 Loading schema...")
    schemas = load_schemas(config.schema_file, config.dataset_type)
    
    if config.max_samples:
        questions = questions[:config.max_samples]

    print(f"📊 Total {len(questions)} questions to process\n")

    # Build graph
    graph = build_graph()
    
    # Prepare output
    output_path = Path(config.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    error_count = 0

    # Open output file (write mode)
    with open(config.output_file, 'w', encoding='utf-8') as output_file:
        # Process each question
        for idx, item in enumerate(questions, 1):
            question = item.get("question", "")
            db_id = item.get("db_id", "")
            gold_sql = item.get("SQL", "") or item.get("query", "")  # BIRD uses SQL, Spider uses query

            print(f"\n{'=' * 80}")
            print(f"[{idx}/{len(questions)}] DB: {db_id}")
            print(f"Question: {question}")

            # Get schema info
            schema_info = schemas.get(db_id, {})
            if not schema_info:
                print(f"  ⚠️  Warning: schema info for {db_id} not found")
                sql_result = "SELECT 1;  -- ERROR: No schema found"
                output_file.write(sql_result + "\n")
                output_file.flush()  # Flush to disk immediately
                error_count += 1
                continue

            try:
                # Build initial state
                initial_state = AgentState(
                    question=question,
                    db_id=db_id,
                    schema_info=schema_info,
                    data_dir=config.database_dir,
                    max_revisions=config.max_revisions,
                )

                # Run graph
                final_state = graph.invoke(initial_state)
                
                # Get final SQL (LangGraph returns a dict)
                final_sql = final_state.get("final_sql", "") or final_state.get("sql_draft", "")

                if not final_sql:
                    print(f"  ⚠️  Warning: no SQL generated")
                    final_sql = "SELECT 1;  -- ERROR: No SQL generated"
                    error_count += 1
                else:
                    # Ensure SQL is single-line
                    final_sql = " ".join(final_sql.split())
                    success_count += 1
                    print(f"  ✅ Generated SQL: {final_sql[:100]}...")

                # Write result immediately
                output_file.write(final_sql + "\n")
                output_file.flush()  # Flush to disk immediately

                # Show revision history
                revision_history = final_state.get("revision_history", [])
                if revision_history:
                    print(f"  📝 Revisions: {len(revision_history)}")

            except Exception as e:
                error_msg = str(e).replace('\n', ' ').replace('\r', ' ')
                print(f"  ❌ Execution error: {error_msg}")
                import traceback
                traceback.print_exc()
                sql_result = f"SELECT 1;  -- ERROR: {error_msg}"
                output_file.write(sql_result + "\n")
                output_file.flush()  # Flush to disk immediately
                error_count += 1

    # Summary
    print(f"\n{'=' * 80}")
    print(f"💾 Results have been written to: {config.output_file}")
    print(f"\n📊 Evaluation summary:")
    print(f"{'=' * 80}")
    print(f"  ✅ Success: {success_count}/{len(questions)}")
    print(f"  ❌ Failure: {error_count}/{len(questions)}")
    print(f"  📈 Success rate: {success_count/len(questions)*100:.1f}%")
    print(f"{'=' * 80}")

    print(f"\n✅ Done! Results saved to {config.output_file}")
    print(f"\n💡 Hint: You can use the official evaluation scripts for EM/EX evaluation.")


if __name__ == "__main__":
    run_evaluation()
