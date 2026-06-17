from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel

class ScreenRequest(BaseModel):
    entity_name: str
    entity_type: Literal["person", "company"] = "company"
    country: Optional[str] = None
    known_aliases: List[str] = []
    industry: Optional[str] = None

class ScreenResponse(BaseModel):
    screening_case_id: str
    status: str

class ReviewRequest(BaseModel):
    reviewer_action: Literal["APPROVE", "REJECT", "ESCALATE"]
    reviewer_notes: Optional[str] = None

class ArticleHit(BaseModel):
    title: str
    source_name: str
    source_url: str
    published_at: str
    summary_text: str
    entity_match_score: float
    relevance_score: float
    credibility_score: float
    severity_score: float
    adverse_category: str
    matched_keywords: List[str]
    kept_for_summary: bool

class AgentTrace(BaseModel):
    task: str
    output: str
    metrics: Optional[Dict[str, Any]] = None

class CaseStatusResponse(BaseModel):
    screening_case_id: str
    status: str
    entity_name: str
    risk_label: str
    risk_score: int
    summary: str
    evidence_count: int
    retrieval_provider: str | None = None
    duration_ms: int | None = None
    prompt_tokens_total: int | None = None
    response_tokens_total: int | None = None
    llm_metrics: List[Dict[str, Any]] = []
    agent_traces: List[AgentTrace] = []
    articles: List[ArticleHit]
