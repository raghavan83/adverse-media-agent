import re
from rapidfuzz import fuzz

ADVERSE_KEYWORDS = {
    "fraud": 0.95,
    "money laundering": 0.98,
    "sanctions": 0.98,
    "bribery": 0.94,
    "corruption": 0.94,
    "lawsuit": 0.72,
    "sued": 0.72,
    "penalty": 0.78,
    "regulatory": 0.8,
    "probe": 0.82,
    "investigation": 0.84,
    "crime": 0.9,
    "arrest": 0.92,
    "fine": 0.75,
    "bankruptcy": 0.77,
    "default": 0.8,
}

LEGAL_SUFFIXES = ["inc", "ltd", "limited", "llc", "corp", "corporation", "pvt", "private", "co", "company", "plc"]


def normalize_name(name: str) -> str:
    value = (name or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    tokens = [t for t in value.split() if t and t not in LEGAL_SUFFIXES]
    return " ".join(tokens)


def entity_match_score(entity_name: str, aliases: list[str], title: str, summary_text: str) -> float:
    candidates = [entity_name] + list(aliases or [])
    scores = []
    ntitle = normalize_name(title)
    nsummary = normalize_name(summary_text)
    for c in candidates:
        n = normalize_name(c)
        if not n:
            continue
        exact_bonus = 1.0 if n in ntitle or n in nsummary else 0.0
        title_score = fuzz.token_set_ratio(n, ntitle) / 100.0
        body_score = fuzz.token_set_ratio(n, nsummary) / 100.0
        combined = min(1.0, max(exact_bonus, title_score * 0.65 + body_score * 0.35))
        scores.append(combined)
    return round(max(scores) if scores else 0.0, 3)


def adverse_signal_score(title: str, summary_text: str):
    text = f"{title} {summary_text}".lower()
    matched = []
    score = 0.05
    for kw, kw_score in ADVERSE_KEYWORDS.items():
        if kw in text:
            matched.append(kw)
            score = max(score, kw_score)
    return round(score, 3), matched


def source_credibility_score(source_name: str, source_url: str) -> float:
    text = f"{source_name} {source_url}".lower()
    if any(x in text for x in ["reuters", "apnews", "bloomberg", "wsj", "ft.com"]):
        return 0.95
    if any(x in text for x in ["news.google", "google news"]):
        return 0.7
    if source_url.startswith("https://"):
        return 0.75
    return 0.6


def adverse_category(keywords: list[str]) -> str:
    priority = ["money laundering", "sanctions", "fraud", "corruption", "bribery", "crime", "arrest", "investigation", "probe", "regulatory", "lawsuit", "fine", "bankruptcy", "default"]
    for p in priority:
        if p in keywords:
            return p
    return "other"


def final_article_scores(entity_name: str, aliases: list[str], title: str, summary_text: str, source_name: str, source_url: str):
    ems = entity_match_score(entity_name, aliases, title, summary_text)
    adverse_score, keywords = adverse_signal_score(title, summary_text)
    credibility = source_credibility_score(source_name, source_url)
    relevance = round((ems * 0.55 + adverse_score * 0.45), 3)
    severity = adverse_score
    kept = relevance >= 0.45 and ems >= 0.35
    return {
        "entity_match_score": ems,
        "relevance_score": relevance,
        "credibility_score": credibility,
        "severity_score": severity,
        "adverse_category": adverse_category(keywords),
        "matched_keywords": keywords,
        "kept_for_summary": kept,
    }


def aggregate_case_risk(scored_articles: list[dict]):
    kept = [a for a in scored_articles if a.get("kept_for_summary")]
    if not kept:
        return 18, "LOW"
    total = 0
    for a in kept:
        score = (
            a["severity_score"] * 0.35
            + a["credibility_score"] * 0.20
            + a["entity_match_score"] * 0.25
            + a["relevance_score"] * 0.20
        ) * 100
        total += score
    final = int(total / len(kept))
    if final >= 70:
        return final, "HIGH"
    if final >= 40:
        return final, "MEDIUM"
    return final, "LOW"
