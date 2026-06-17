from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from backend.db import Base

class ScreeningCase(Base):
    __tablename__ = "screening_cases"
    id = Column(Integer, primary_key=True, index=True)
    screening_case_id = Column(String, unique=True, index=True, nullable=False)
    entity_name = Column(String, index=True, nullable=False)
    entity_type = Column(String, nullable=False)
    country = Column(String)
    industry = Column(String)
    status = Column(String, nullable=False)
    retrieval_provider = Column(String)
    risk_label = Column(String)
    risk_score = Column(Integer)
    summary = Column(Text)
    evidence_count = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ArticleHitRecord(Base):
    __tablename__ = "article_hits"
    id = Column(Integer, primary_key=True, index=True)
    screening_case_id = Column(String, index=True, nullable=False)
    title = Column(Text)
    source_name = Column(String)
    source_url = Column(Text)
    published_at = Column(String)
    summary_text = Column(Text)
    entity_match_score = Column(Float)
    relevance_score = Column(Float)
    credibility_score = Column(Float)
    severity_score = Column(Float)
    adverse_category = Column(String)
    matched_keywords = Column(Text)
    kept_for_summary = Column(String)

class ReviewActionRecord(Base):
    __tablename__ = "review_actions"
    id = Column(Integer, primary_key=True, index=True)
    screening_case_id = Column(String, index=True, nullable=False)
    reviewer_action = Column(String, nullable=False)
    reviewer_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    screening_case_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    event_payload = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
