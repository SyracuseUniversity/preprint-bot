# arXiv Preprint Bot – Demo Site

A simple demo with Streamlit (frontend) and FastAPI (backend).  
- Upload a PDF or provide an arXiv ID/URL  
- Choose categories and number of papers  
- Jobs are saved to `jobs.json`

---------------------------------
How to run:

Open two terminals in the project root:

1. Start the API (backend)

    uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

API runs at: http://127.0.0.1:8000/docs

2. Start the UI (frontend)

    streamlit run app.py

UI runs at: http://localhost:8501

---------------------------------

Install dependencies:
pip install -r requirements.txt
