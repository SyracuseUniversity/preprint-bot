# api/main.py
from fastapi import FastAPI, UploadFile, Form
from pydantic import BaseModel, EmailStr
from pathlib import Path
from datetime import datetime
import json

app = FastAPI()

class Settings(BaseModel):
    email: EmailStr
    categories: list[str]
    similarity: float
    max_papers: int

# Save next to the repo root (one level above api/)
BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_FILE = BASE_DIR / "jobs.json"

def _append_job(entry: dict) -> None:
    try:
        data = json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else []
        if not isinstance(data, list):
            data = []
    except Exception:
        data = []
    data.append(entry)
    JOBS_FILE.write_text(json.dumps(data, indent=2))

@app.post("/submit")
async def submit(
    file: UploadFile | None = None,
    arxiv: str | None = Form(None),
    email: EmailStr = Form(...),
    categories: str = Form("[]"),
    similarity: float = Form(0.7),
    max_papers: int = Form(10, ge=1, le=100)
):
    try:
        cats = json.loads(categories)
    except Exception:
        cats = categories

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "email": str(email),
        "categories": cats,
        "similarity": similarity,
        "max_papers": max_papers,
        "arxiv": arxiv,
        "file_name": file.filename if file else None,
    }

    _append_job(record)
    return {"ok": True}