# Adverse Media Screening Copilot v9

This is a production-oriented hackathon build for adverse media screening with real retrieval, agentic task orchestration, SQLite persistence, audit trail, structured request logging, pluggable LLM execution, and benchmark-friendly runtime metrics.

## Highlights
- Multi-step agent workflow: planner, retrieval evaluator, evidence synthesizer, reviewer advisor
- Real article retrieval: NewsAPI with Google News RSS fallback
- Heuristic entity and adverse scoring
- SQLite persistence for cases, hits, reviews, and audit events
- Structured logs with rotating files and request middleware
- Real LLM hooks with `transformers` for local inference when enabled
- Safe mock mode for environments without model/runtime setup
- AMD-ready extension path for ROCm-backed model inference
- Runtime observability: prompt tokens, response tokens, tokens/sec, GPU snapshots, and end-to-end latency
- CLI artifacts for hackathon submission: metrics JSON and example scenario outputs

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
uvicorn backend.main:app --reload
streamlit run frontend/app.py
```

## Headless mode
```bash
python run_screening.py --input input/request_adani.json --output-dir outputs
```

## New v9 outputs
For each screening case, headless mode now writes:
- `<CASE_ID>_result.json`
- `<CASE_ID>_summary.txt`
- `<CASE_ID>_agent_traces.json`
- `<CASE_ID>_metrics.json`
- `<CASE_ID>_example_output.json`
- `example_scenarios.json`

These files are intended to support Slide 4 and Slide 5 of the hackathon submission with measured token counts, latency, GPU snapshots when available, and example scenario outputs.

## Important config
- `NEWSAPI_KEY`: API key for NewsAPI retrieval
- `ENABLE_LOCAL_LLM=true`: enables local Hugging Face inference
- `LLM_MODEL`: model name for local inference
- `DATABASE_URL`: SQLite/Postgres connection string
- `MAX_NEW_TOKENS`: max generated tokens for local inference
- `TEMPERATURE`: decoding temperature for local inference

## AMD ROCm note
On AMD systems, ensure `rocm-smi` is available in the environment if you want GPU type, utilization, and memory snapshots recorded in the per-task LLM metrics.
