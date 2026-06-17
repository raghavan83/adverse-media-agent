# Adverse Media Screening Copilot v5

This is a production-oriented hackathon build for adverse media screening with real retrieval, agentic task orchestration, SQLite persistence, audit trail, structured request logging, and pluggable LLM execution.

## Highlights
- Multi-step agent workflow: planner, retrieval evaluator, evidence synthesizer, reviewer advisor
- Real article retrieval: NewsAPI with Google News RSS fallback
- Heuristic entity and adverse scoring
- SQLite persistence for cases, hits, reviews, and audit events
- Structured logs with rotating files and request middleware
- Real LLM hooks with `transformers` for local inference when enabled
- Safe mock mode for environments without model/runtime setup
- AMD-ready extension path for ROCm-backed model inference

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

## Important config
- `NEWSAPI_KEY`: API key for NewsAPI retrieval
- `ENABLE_LOCAL_LLM=true`: enables local Hugging Face inference
- `LLM_MODEL`: model name for local inference
- `DATABASE_URL`: SQLite/Postgres connection string

## AMD ROCm note
For AMD systems, install ROCm-enabled PyTorch wheels and `transformers`/`accelerate`, then run local inference through the same `TransformersLLMClient` interface. AMD documents describe using ROCm-enabled PyTorch and Hugging Face models for inference workflows.


## LLM observability
This version logs LLM usage details including provider, model, latency, prompt/response size estimates, and response preview snippets. This helps you demonstrate model usage during the hackathon and troubleshoot inference behavior.


## Headless mode
You can run the complete screening pipeline without FastAPI or Streamlit:
```bash
python run_screening.py --input input/request_adani.json --output-dir outputs
```
This mode is ideal for AMD notebook environments with browser or port restrictions.
