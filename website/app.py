# app.py
import json
import requests
import streamlit as st
from pydantic import BaseModel, EmailStr, ValidationError

API_URL = "http://127.0.0.1:8000/submit"

class Settings(BaseModel):
    email: EmailStr
    categories: list[str]
    sim_threshold: float
    max_papers: int

st.title("arXiv Preprint Bot")
tab1, tab2 = st.tabs(["Upload PDF", "arXiv ID/URL"])

with tab1:
    pdf = st.file_uploader("Upload PDF", type=["pdf"])

with tab2:
    arxiv_id = st.text_input("arXiv ID or URL")

email = st.text_input("Notification email")
cats = st.multiselect("Categories", [
    "cs","math","physics","astro-ph","cond-mat","gr-qc","hep-ex","hep-lat",
    "hep-ph","hep-th","math-ph","nlin","nucl-ex","nucl-th","quant-ph","stat","eess","econ"
])
sim = st.slider("Similarity threshold", 0.0, 1.0, 0.7, 0.01)
limit = st.number_input("Maximum number of papers to send", min_value=1, max_value=100, value=10, step=1)

if st.button("Run"):
    # basic front-end check: exactly one of pdf / arxiv
    if (pdf is None and not arxiv_id) or (pdf is not None and arxiv_id):
        st.error("Provide either a PDF upload OR an arXiv ID/URL (not both).")
    else:
        try:
            cfg = Settings(email=email, categories=cats, sim_threshold=sim, max_papers=limit)

            data = {
                "email": cfg.email,
                "categories": json.dumps(cfg.categories),
                "similarity": str(cfg.sim_threshold),
                "max_papers": str(cfg.max_papers),
            }
            files = {"file": (pdf.name, pdf.getvalue(), "application/pdf")} if pdf else None
            if not files:
                data["arxiv"] = arxiv_id

            r = requests.post(API_URL, data=data, files=files, timeout=60)
            if r.ok:
                st.success("Job submitted!")
                st.json(r.json())
            else:
                st.error(f"Server error {r.status_code}: {r.text}")

        except ValidationError as e:
            st.error(str(e))
