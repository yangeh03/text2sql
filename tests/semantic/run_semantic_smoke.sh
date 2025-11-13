#!/usr/bin/env bash
set -euo pipefail

# Semantic gate smoke test for the Text-to-SQL agent
# This script is compatible with the current baseline even if the semantic gate is not implemented yet.

# Resolve project root (two levels up from this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../.." && pwd )"
cd "$PROJECT_ROOT"

# Default environment (can be overridden by caller)
export ENABLE_SEMANTIC_VALIDATE=${ENABLE_SEMANTIC_VALIDATE:-false}
export SEMANTIC_SCORE_THRESHOLD=${SEMANTIC_SCORE_THRESHOLD:-0.7}
export SEMANTIC_GATE_MODE=${SEMANTIC_GATE_MODE:-before_exec}  # before_exec | finalize_on_pass

# Print environment
echo "[Semantic Smoke] PROJECT_ROOT=$PROJECT_ROOT"
echo "[Semantic Smoke] ENABLE_SEMANTIC_VALIDATE=$ENABLE_SEMANTIC_VALIDATE"
echo "[Semantic Smoke] SEMANTIC_SCORE_THRESHOLD=$SEMANTIC_SCORE_THRESHOLD"
echo "[Semantic Smoke] SEMANTIC_GATE_MODE=$SEMANTIC_GATE_MODE"

# Prepare outputs
LOG_DIR="outputs/logs"
REPORT_DIR="outputs/semantic_reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

# Run evaluation (limited samples are configured in src/agent/config.py -> EVAL_CONFIG)
set +e
python src/agent/main.py | tee "$LOG_DIR/semantic_smoke.log"
STATUS=$?
set -e

# Summaries
echo "\n================ SUMMARY ================"
if [ $STATUS -eq 0 ]; then
  echo "[OK] main.py completed."
else
  echo "[WARN] main.py exited with status $STATUS"
fi

if [ -f "outputs/predictions.sql" ]; then
  echo "[OK] Predictions written to outputs/predictions.sql"
else
  echo "[WARN] outputs/predictions.sql not found"
fi

# Optional: list semantic reports if produced by your implementation
if compgen -G "${REPORT_DIR}/*.json" > /dev/null; then
  echo "[OK] Semantic reports found in ${REPORT_DIR}:"
  ls -1 ${REPORT_DIR}/*.json | head -n 5
else
  echo "[INFO] No semantic reports generated (this is fine for baseline)."
fi

echo "Logs: ${LOG_DIR}/semantic_smoke.log"
exit $STATUS
