import streamlit as st
import requests

st.set_page_config(page_title="Adverse Media Screening Copilot", layout="wide")
st.title("Adverse Media Screening Copilot v9")
st.caption("Production-oriented hackathon build with agentic workflow and runtime metrics")

api_base = st.sidebar.text_input("Backend URL", value="http://localhost:8000")
entity_name = st.text_input("Entity name", value="Adani")
entity_type = st.selectbox("Entity type", ["company", "person"])
country = st.text_input("Country", value="IN")
aliases = st.text_input("Known aliases (comma-separated)", value="")
industry = st.text_input("Industry", value="")

if st.button("Run screening"):
    payload = {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "country": country,
        "known_aliases": [a.strip() for a in aliases.split(",") if a.strip()],
        "industry": industry or None,
    }
    r = requests.post(f"{api_base}/screen", json=payload, timeout=120)
    if r.ok:
        case_id = r.json()["screening_case_id"]
        details = requests.get(f"{api_base}/screen/{case_id}", timeout=120).json()
        st.subheader(f"Case {case_id}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk label", details["risk_label"])
        c2.metric("Risk score", details["risk_score"])
        c3.metric("Evidence count", details["evidence_count"])
        c4.metric("Duration ms", details.get("duration_ms") or 0)
        st.write(details["summary"])
        st.write(f"Retrieval provider: {details.get('retrieval_provider')}")

        st.subheader("LLM metrics")
        m1, m2, m3 = st.columns(3)
        m1.metric("Prompt tokens total", details.get("prompt_tokens_total") or 0)
        m2.metric("Response tokens total", details.get("response_tokens_total") or 0)
        avg_tps = 0.0
        llm_metrics = details.get("llm_metrics") or []
        if llm_metrics:
            avg_tps = round(sum(float(m.get("tokens_per_second", 0)) for m in llm_metrics) / len(llm_metrics), 2)
        m3.metric("Avg tokens/sec", avg_tps)

        for metric in llm_metrics:
            with st.expander(f"LLM task metrics: {metric.get('task', 'unknown')}"):
                st.json(metric)

        st.subheader("Agent traces")
        for trace in details.get("agent_traces", []):
            with st.expander(trace["task"]):
                st.write(trace["output"])
                if trace.get("metrics"):
                    st.caption("Task metrics")
                    st.json(trace["metrics"])

        st.subheader("Scored articles")
        for article in details["articles"]:
            with st.expander(article["title"]):
                st.write(f"Source: {article['source_name']}")
                st.write(f"Published: {article['published_at']}")
                st.write(f"Category: {article['adverse_category']}")
                st.write(f"Matched keywords: {', '.join(article['matched_keywords']) if article['matched_keywords'] else 'None'}")
                st.write(f"Entity match: {article['entity_match_score']}")
                st.write(f"Relevance: {article['relevance_score']}")
                st.write(f"Credibility: {article['credibility_score']}")
                st.write(f"Severity: {article['severity_score']}")
                st.write(f"Kept for summary: {article['kept_for_summary']}")
                if article['summary_text']:
                    st.write(article['summary_text'])
                st.markdown(f"[Open source]({article['source_url']})")

        st.subheader("Audit trail")
        audit = requests.get(f"{api_base}/audit/{case_id}", timeout=60).json()
        st.json(audit)
    else:
        st.error(r.text)
