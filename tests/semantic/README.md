# Semantic Gate Smoke Test

This folder contains a smoke test for the Back-Translation Semantic Validation gate.
It works with the current baseline even if your semantic gate is not implemented yet.

## Files
- `run_semantic_smoke.sh`: Bash script to run an end-to-end small evaluation and collect logs.

## Prerequisites
- Python >= 3.10
- Project dependencies installed: `pip install -r requirements.txt`
- Configure your `.env` (see project README) for LLM provider and model.

## Run
```bash
bash tests/semantic/run_semantic_smoke.sh
```

Environment variables (optional):
```bash
export ENABLE_SEMANTIC_VALIDATE=true      # enable semantic gate if implemented
export SEMANTIC_SCORE_THRESHOLD=0.7       # threshold in [0,1]
export SEMANTIC_GATE_MODE=before_exec     # before_exec | finalize_on_pass
```

## Outputs
- `outputs/predictions.sql`: generated SQL predictions
- `outputs/logs/semantic_smoke.log`: console log
- `outputs/semantic_reports/*.json` (optional): per-sample semantic reports if your implementation writes them

## Notes
- This smoke test uses the sample size configured in `src/agent/config.py -> EVAL_CONFIG.max_samples`.
- The script returns non-zero status if `python src/agent/main.py` fails.
