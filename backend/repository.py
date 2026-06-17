import json
from backend.db import SessionLocal
from backend.db_models import ScreeningCase, ArticleHitRecord, ReviewActionRecord, AuditEventRecord

class Repository:
    def save_case(self, payload: dict):
        db = SessionLocal()
        try:
            case = ScreeningCase(
                screening_case_id=payload["screening_case_id"],
                entity_name=payload["entity_name"],
                entity_type=payload.get("entity_type", "company"),
                country=payload.get("country"),
                industry=payload.get("industry"),
                status=payload["status"],
                retrieval_provider=payload.get("retrieval_provider"),
                risk_label=payload.get("risk_label"),
                risk_score=payload.get("risk_score"),
                summary=payload.get("summary"),
                evidence_count=payload.get("evidence_count", 0),
                duration_ms=payload.get("duration_ms", 0),
            )
            db.add(case)
            for a in payload.get("articles", []):
                db.add(ArticleHitRecord(
                    screening_case_id=payload["screening_case_id"],
                    title=a.get("title"),
                    source_name=a.get("source_name"),
                    source_url=a.get("source_url"),
                    published_at=a.get("published_at"),
                    summary_text=a.get("summary_text"),
                    entity_match_score=a.get("entity_match_score"),
                    relevance_score=a.get("relevance_score"),
                    credibility_score=a.get("credibility_score"),
                    severity_score=a.get("severity_score"),
                    adverse_category=a.get("adverse_category"),
                    matched_keywords=json.dumps(a.get("matched_keywords", [])),
                    kept_for_summary=str(a.get("kept_for_summary", False)),
                ))
            db.add(AuditEventRecord(screening_case_id=payload["screening_case_id"], event_type="CASE_CREATED", event_payload=json.dumps({"risk_label": payload.get("risk_label"), "provider": payload.get("retrieval_provider"), "evidence_count": payload.get("evidence_count", 0)})))
            for trace in payload.get("agent_traces", []):
                db.add(AuditEventRecord(screening_case_id=payload["screening_case_id"], event_type=f"AGENT_{trace['task'].upper()}", event_payload=json.dumps(trace)))
            db.commit()
        finally:
            db.close()

    def save_review(self, screening_case_id: str, reviewer_action: str, reviewer_notes: str | None):
        db = SessionLocal()
        try:
            db.add(ReviewActionRecord(screening_case_id=screening_case_id, reviewer_action=reviewer_action, reviewer_notes=reviewer_notes))
            db.add(AuditEventRecord(screening_case_id=screening_case_id, event_type="REVIEW_SUBMITTED", event_payload=json.dumps({"reviewer_action": reviewer_action, "reviewer_notes": reviewer_notes})))
            case = db.query(ScreeningCase).filter(ScreeningCase.screening_case_id == screening_case_id).first()
            if case:
                case.status = f"REVIEWED_{reviewer_action}"
            db.commit()
        finally:
            db.close()

    def list_cases(self):
        db = SessionLocal()
        try:
            return db.query(ScreeningCase).order_by(ScreeningCase.id.desc()).limit(100).all()
        finally:
            db.close()

    def get_audit(self, screening_case_id: str):
        db = SessionLocal()
        try:
            return db.query(AuditEventRecord).filter(AuditEventRecord.screening_case_id == screening_case_id).order_by(AuditEventRecord.id.asc()).all()
        finally:
            db.close()
