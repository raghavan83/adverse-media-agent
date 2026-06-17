import logging
import os
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from datetime import datetime

logger = logging.getLogger("adverse_media.retrieval")
NEWSAPI_URL = "https://newsapi.org/v2/everything"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _clean_text(value):
    return (value or "").strip()


def _request_with_retry(url, *, params=None, headers=None, timeout=30, retries=2, backoff=1.5):
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(backoff ** attempt)
    raise last_error


def retrieve_articles(entity_name: str, country: str | None = None, page_size: int = 10, case_id: str | None = None):
    api_key = os.getenv("NEWSAPI_KEY", "").strip()
    if api_key:
        try:
            articles = _retrieve_newsapi(entity_name, api_key, page_size=page_size)
            if articles:
                logger.info("NewsAPI retrieval completed", extra={"case_id": case_id, "entity_name": entity_name, "provider": "newsapi", "status": "SUCCESS", "article_count": len(articles)})
                return articles, "newsapi"
        except Exception as exc:
            logger.exception("NewsAPI retrieval failed; falling back to Google News RSS", extra={"case_id": case_id, "entity_name": entity_name, "provider": "newsapi", "status": "FAILED", "error": str(exc)})
    articles = _retrieve_google_news_rss(entity_name, country=country, page_size=page_size)
    logger.info("Google News RSS retrieval completed", extra={"case_id": case_id, "entity_name": entity_name, "provider": "google_news_rss", "status": "SUCCESS", "article_count": len(articles)})
    return articles, "google_news_rss"


def _retrieve_newsapi(entity_name: str, api_key: str, page_size: int = 10):
    params = {"q": f'"{entity_name}"', "language": "en", "sortBy": "relevancy", "pageSize": page_size, "apiKey": api_key}
    response = _request_with_retry(NEWSAPI_URL, params=params, timeout=30)
    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(f"Unexpected NewsAPI status: {payload}")
    results = []
    for art in payload.get("articles", []):
        title = _clean_text(art.get("title"))
        description = _clean_text(art.get("description"))
        content = _clean_text(art.get("content"))
        published_at = art.get("publishedAt")
        results.append({"title": title, "summary_text": " ".join([x for x in [description, content] if x]).strip(), "source_name": _clean_text((art.get("source") or {}).get("name")), "source_url": art.get("url", ""), "published_at": published_at or datetime.utcnow().isoformat()})
    return results


def _retrieve_google_news_rss(entity_name: str, country: str | None = None, page_size: int = 10):
    query = f'"{entity_name}"'
    if country:
        query += f' {country}'
    params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    url = GOOGLE_NEWS_RSS + "?" + "&".join(f"{k}={quote_plus(v)}" for k, v in params.items())
    response = _request_with_retry(url, headers={"User-Agent": os.getenv("USER_AGENT", "AdverseMediaScreeningCopilot/1.0")}, timeout=30)
    root = ET.fromstring(response.text)
    items = root.findall(".//item")[:page_size]
    results = []
    for item in items:
        results.append({"title": _clean_text(item.findtext("title")), "summary_text": _clean_text(item.findtext("description")), "source_name": "Google News RSS", "source_url": _clean_text(item.findtext("link")), "published_at": _clean_text(item.findtext("pubDate"))})
    return results
