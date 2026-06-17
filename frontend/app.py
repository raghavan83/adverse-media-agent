import streamlit as st
import requests

st.set_page_config(page_title="Adverse Media Screening Copilot", layout="wide")
st.title("Adverse Media Screening Copilot")
st.caption("Production-oriented hackathon build with agentic workflow")

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

        st.subheader("Agent traces")
        for trace in details.get("agent_traces", []):
            with st.expander(trace["task"]):
                st.write(trace["output"])

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
