import logging
import time
from uuid import uuid4
from backend.models import ScreenRequest, ReviewRequest
from backend.retrieval import retrieve_articles
from backend.scoring import final_article_scores, aggregate_case_risk
from backend.agents import get_llm_client, planner_task, retrieval_evaluator_task, evidence_synthesizer_task, reviewer_advisor_task
from backend.repository import Repository

logger = logging.getLogger("adverse_media.pipeline")
CASE_STORE = {}
repo = Repository()


def run_screening(payload: ScreenRequest):
    screening_case_id = f"SCN-{uuid4().hex[:10].upper()}"
    start = time.perf_counter()
    llm = get_llm_client()
    agent_traces = []

    plan = planner_task(llm, payload.entity_name)
    agent_traces.append({"task": "planner", "output": plan})

    raw_articles, provider = retrieve_articles(payload.entity_name, country=payload.country, page_size=10, case_id=screening_case_id)
    retrieval_eval = retrieval_evaluator_task(llm, raw_articles)
    agent_traces.append({"task": "retrieval_evaluator", "output": retrieval_eval})

    articles = []
    for item in raw_articles:
        score_details = final_article_scores(payload.entity_name, payload.known_aliases, item.get("title", ""), item.get("summary_text", ""), item.get("source_name", ""), item.get("source_url", ""))
        articles.append({**item, **score_details})

    articles = sorted(articles, key=lambda a: (a["kept_for_summary"], a["relevance_score"], a["severity_score"], a["entity_match_score"]), reverse=True)
    risk_score, risk_label = aggregate_case_risk(articles)
    kept_articles = [a for a in articles if a["kept_for_summary"]][:5]

    synthesized = evidence_synthesizer_task(llm, payload.entity_name, kept_articles, risk_label)
    agent_traces.append({"task": "evidence_synthesizer", "output": synthesized})
    recommendation = reviewer_advisor_task(llm, risk_label, kept_articles)
    agent_traces.append({"task": "reviewer_advisor", "output": recommendation})

    summary = synthesized if kept_articles else f"No sufficiently relevant adverse evidence was found for {payload.entity_name}."
    duration_ms = int((time.perf_counter() - start) * 1000)

    case = {
        "screening_case_id": screening_case_id,
        "status": "COMPLETED",
        "entity_name": payload.entity_name,
        "entity_type": payload.entity_type,
        "country": payload.country,
        "industry": payload.industry,
        "risk_label": risk_label,
        "risk_score": risk_score,
        "summary": summary,
        "evidence_count": len(kept_articles),
        "articles": articles,
        "retrieval_provider": provider,
        "duration_ms": duration_ms,
        "agent_traces": agent_traces,
    }
    CASE_STORE[screening_case_id] = case
    repo.save_case(case)
    logger.info("screening completed", extra={"case_id": screening_case_id, "entity_name": payload.entity_name, "provider": provider, "status": "COMPLETED", "duration_ms": duration_ms, "article_count": len(articles)})
    return case


def submit_review(screening_case_id: str, payload: ReviewRequest):
    case = CASE_STORE.get(screening_case_id)
    if not case:
        logger.warning("review requested for missing case", extra={"case_id": screening_case_id, "status": "NOT_FOUND"})
        return None
    case["status"] = f"REVIEWED_{payload.reviewer_action}"
    case["reviewer_notes"] = payload.reviewer_notes
    repo.save_review(screening_case_id, payload.reviewer_action, payload.reviewer_notes)
    logger.info("review submitted", extra={"case_id": screening_case_id, "status": case["status"]})
    return case
