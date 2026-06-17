import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

from backend.logging_config import configure_logging
from backend.db import Base, engine
from backend.models import ScreenRequest, ScreenResponse, ReviewRequest, CaseStatusResponse
from backend.pipeline import run_screening, CASE_STORE, submit_review
from backend.repository import Repository

configure_logging()
logger = logging.getLogger("adverse_media.app")
Base.metadata.create_all(bind=engine)
repo = Repository()

logger.info("application startup", extra={"status": "STARTED", "provider": "env-check", "error": None if os.getenv("NEWSAPI_KEY") else "NEWSAPI_KEY missing"})

app = FastAPI(title="Adverse Media Screening Copilot")

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logging.getLogger("api.request").info(
        "request processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return response

@app.get("/health")
def health():
    return {"status": "ok", "newsapi_key_present": bool(os.getenv("NEWSAPI_KEY", "").strip()), "llm_provider": os.getenv("LLM_PROVIDER", "mock"), "local_llm_enabled": os.getenv("ENABLE_LOCAL_LLM", "false")}

@app.post("/screen", response_model=ScreenResponse)
def screen(payload: ScreenRequest):
    case = run_screening(payload)
    return ScreenResponse(screening_case_id=case["screening_case_id"], status=case["status"])

@app.get("/screen/{screening_case_id}", response_model=CaseStatusResponse)
def get_screen(screening_case_id: str):
    case = CASE_STORE.get(screening_case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseStatusResponse(**{k: v for k, v in case.items() if k in CaseStatusResponse.model_fields})

@app.post("/review/{screening_case_id}")
def review(screening_case_id: str, payload: ReviewRequest):
    case = submit_review(screening_case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"screening_case_id": screening_case_id, "status": case["status"], "reviewer_action": payload.reviewer_action}

@app.get("/cases")
def list_cases():
    rows = repo.list_cases()
    return [{"screening_case_id": r.screening_case_id, "entity_name": r.entity_name, "risk_label": r.risk_label, "status": r.status, "provider": r.retrieval_provider, "created_at": str(r.created_at)} for r in rows]

@app.get("/audit/{screening_case_id}")
def get_audit(screening_case_id: str):
    rows = repo.get_audit(screening_case_id)
    return [{"event_type": r.event_type, "event_payload": r.event_payload, "created_at": str(r.created_at)} for r in rows]
