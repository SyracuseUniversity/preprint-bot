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

# ---------------------------
# Streamlit App
# ---------------------------
import os
import time
import uuid
import hashlib
import json as _json
from pathlib import Path as _Path

import bcrypt
import streamlit as st
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Float
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

# ---------------------------
# Config & Paths
# ---------------------------
APP_DIR = _Path(__file__).resolve().parent
DB_PATH = APP_DIR / "app.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

load_dotenv(override=True)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ---------------------------
# Database (SQLAlchemy)
# ---------------------------
Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("Asset", back_populates="owner", cascade="all, delete-orphan")
    pref = relationship("Preference", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    kind = Column(String(20), nullable=False)  # 'file' or 'link'
    title = Column(String(255), nullable=True)

    # for files
    original_name = Column(String(255), nullable=True)
    stored_path = Column(Text, nullable=True)  # relative path under ./uploads

    # for links
    url = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="assets")

class Preference(Base):
    __tablename__ = "preferences"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    categories_json = Column(Text, nullable=False, default="[]")
    similarity = Column(Float, nullable=False, default=0.7)
    max_papers = Column(Integer, nullable=False, default=10)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="pref")

Base.metadata.create_all(engine)

# ---------------------------
# Helpers
# ---------------------------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

def get_session():
    return SessionLocal()

def session_token() -> str:
    token = st.session_state.get("_token")
    if not token:
        token = hashlib.sha256(f"{SECRET_KEY}-{time.time()}".encode()).hexdigest()
        st.session_state["_token"] = token
    return token

# ---------------------------
# Preferences (DB + session)
# ---------------------------
DEFAULT_PREFS = {"categories": [], "similarity": 0.7, "max_papers": 10}

def get_prefs(db, user_id: int) -> dict:
    p = db.query(Preference).filter(Preference.user_id == user_id).first()
    if not p:
        return DEFAULT_PREFS.copy()
    try:
        cats = _json.loads(p.categories_json)
    except Exception:
        cats = []
    return {"categories": cats, "similarity": p.similarity, "max_papers": p.max_papers}

def upsert_prefs(db, user_id: int, prefs: dict) -> None:
    p = db.query(Preference).filter(Preference.user_id == user_id).first()
    cats_json = _json.dumps(prefs.get("categories", []))
    if not p:
        p = Preference(
            user_id=user_id,
            categories_json=cats_json,
            similarity=float(prefs.get("similarity", 0.7)),
            max_papers=int(prefs.get("max_papers", 10)),
        )
        db.add(p)
    else:
        p.categories_json = cats_json
        p.similarity = float(prefs.get("similarity", 0.7))
        p.max_papers = int(prefs.get("max_papers", 10))
    db.commit()

def get_session_prefs() -> dict:
    # Always have something in session so prefs UI shows even when logged out
    if "prefs" not in st.session_state:
        st.session_state["prefs"] = DEFAULT_PREFS.copy()
    return st.session_state["prefs"]

# ---------------------------
# Auth UI (Always visible)
# ---------------------------
def sidebar_auth():
    st.sidebar.header("Account")
    email = st.sidebar.text_input("Email", key="auth_email")
    password = st.sidebar.text_input("Password", type="password", key="auth_pw")

    # All buttons are immediately available
    colA, colB = st.sidebar.columns(2)
    with colA:
        if st.button("Log in", use_container_width=True, key="btn_login"):
            with get_session() as db:
                user = db.query(User).filter(User.email == email.lower().strip()).first()
                if not user or not verify_password(password, user.password_hash):
                    st.sidebar.error("Invalid email or password.")
                else:
                    st.session_state["user_id"] = user.id
                    st.session_state["user_email"] = user.email

                    # Load stored prefs or keep current session prefs if user has none yet
                    stored = get_prefs(db, user.id)
                    if stored == DEFAULT_PREFS and st.session_state.get("prefs"):
                        # if session has custom choices, persist them now
                        upsert_prefs(db, user.id, st.session_state["prefs"])
                        st.session_state["prefs"] = get_prefs(db, user.id)
                    else:
                        st.session_state["prefs"] = stored

                    st.sidebar.success("Logged in.")
    with colB:
        if st.button("Sign up", use_container_width=True, key="btn_signup"):
            if not email or not password:
                st.sidebar.error("Email and password are required.")
            else:
                with get_session() as db:
                    exists = db.query(User).filter(User.email == email.lower().strip()).first()
                    if exists:
                        st.sidebar.warning("That email already has an account.")
                    else:
                        u = User(email=email.lower().strip(), password_hash=hash_password(password))
                        db.add(u)
                        db.commit()
                        st.sidebar.success("Account created. You can log in now.")

    if "user_id" in st.session_state:
        st.sidebar.caption(f"Signed in as {st.session_state['user_email']}")
        if st.sidebar.button("Log out", type="secondary"):
            for k in ["user_id", "user_email"]:
                st.session_state.pop(k, None)
            st.sidebar.info("Logged out.")
            # keep session prefs so the UI still shows user choices when logged out

# ---------------------------
# Preferences UI (Right column)
# ---------------------------
def render_prefs(container):
    # Show prefs regardless of auth state (like the old site)
    prefs = get_session_prefs()

    with container:
        st.subheader("Preferences")

        # --- Categories dropdown (multi-select) ---
        CATEGORY_OPTIONS = [
            "cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.NE",
            "math.CO", "math.PR", "math.GR", "stat.ML", "stat.TH",
            "physics.comp-ph", "physics.data-an"
        ]
        cats_in = st.multiselect(
            "Categories",
            options=CATEGORY_OPTIONS,
            default=prefs.get("categories", []),
            key="cats_in_right"
        )

        sim = st.slider(
            "Similarity threshold",
            min_value=0.0, max_value=1.0, step=0.01,
            value=float(prefs.get("similarity", 0.7)),
            key="sim_in_right"
        )
        mp = st.number_input(
            "Max papers",
            min_value=1, max_value=100, step=1,
            value=int(prefs.get("max_papers", 10)),
            key="mp_in_right"
        )

        if st.button("Save preferences", use_container_width=True, key="save_prefs_right"):
            new_prefs = {
                "categories": cats_in,
                "similarity": float(sim),
                "max_papers": int(mp),
            }
            st.session_state["prefs"] = new_prefs
            if "user_id" in st.session_state:
                with get_session() as db:
                    upsert_prefs(db, st.session_state["user_id"], new_prefs)
            st.success("Preferences saved.")

# ---------------------------
# Dashboard (LEFT) + Prefs (RIGHT)
# ---------------------------
def page_dashboard():
    st.title("Uploads & Links")

    # Two columns: content left, preferences right (visible even if logged out)
    left, right = st.columns([3, 2], gap="large")

    with left:
        uid = st.session_state.get("user_id", None)
        token = session_token()

        st.subheader("Upload files")
        files = st.file_uploader(
            "Choose one or more files",
            type=None, accept_multiple_files=True, key="multi_files"
        )
        if files and st.button("Save files", key="save_files_btn"):
            if not uid:
                st.warning("Please log in to save files.")
            else:
                saved_any = False
                with get_session() as db:
                    for f in files:
                        ext = _Path(f.name).suffix
                        unique_name = f"{uuid.uuid4().hex}{ext}"
                        dest = UPLOAD_DIR / unique_name
                        with open(dest, "wb") as out:
                            out.write(f.read())

                        asset = Asset(
                            user_id=uid,
                            kind="file",
                            title=f.name,
                            original_name=f.name,
                            stored_path=str(dest.relative_to(APP_DIR)),
                        )
                        db.add(asset)
                        saved_any = True
                    if saved_any:
                        db.commit()
                if saved_any:
                    st.success("File(s) uploaded.")
                    st.rerun()

        st.subheader("Add links")
        with st.form("add_link_form", clear_on_submit=True):
            link_title = st.text_input("Title (optional)")
            link_url = st.text_input("URL", placeholder="https://...")
            submitted = st.form_submit_button("Save link")
            if submitted:
                if not uid:
                    st.warning("Please log in to save links.")
                elif not link_url.strip():
                    st.warning("Please provide a URL.")
                else:
                    with get_session() as db:
                        db.add(Asset(user_id=uid, kind="link", title=link_title or None, url=link_url.strip()))
                        db.commit()
                    st.success("Link saved.")
                    st.rerun()

            # ---- List current user's items ----
    st.subheader("Your items")
    if not uid:
        st.caption("Log in to view your uploads and links.")
    else:
        with get_session() as db:
            items = (
                db.query(Asset)
                .filter(Asset.user_id == uid)
                .order_by(Asset.created_at.desc())
                .all()
            )
        if not items:
            st.caption("No uploads or links yet.")
        else:
            for a in items:
                with st.container(border=True):
                    if a.kind == "file":
                        st.write(f"📄 **{a.title or a.original_name}**")
                        if a.stored_path:
                            rel = _Path(a.stored_path)
                            abspath = APP_DIR / rel
                            if abspath.exists():
                                st.download_button(
                                    label=f"Download #{a.id}",
                                    file_name=a.original_name or _Path(a.stored_path).name,
                                    data=open(abspath, "rb").read(),
                                    key=f"dl_{a.id}",
                                )
                            st.caption(a.stored_path)
                    else:
                        st.write(f"🔗 **{a.title or a.url}**")
                        if a.url:
                            # NOTE: link_button has no `key` param; make label unique
                            st.link_button(f"Open #{a.id}", a.url, use_container_width=False)

                    if st.button("Delete", key=f"del_{a.id}"):
                        with get_session() as db:
                            obj = db.query(Asset).filter(Asset.id == a.id, Asset.user_id == uid).first()
                            if obj:
                                if obj.stored_path:
                                    p = APP_DIR / _Path(obj.stored_path)
                                    if p.exists():
                                        try:
                                            p.unlink()
                                        except Exception:
                                            pass
                                db.delete(obj)
                                db.commit()
                        st.toast("Deleted.")
                        st.rerun()
    # Preferences panel on the right column (always visible)
    render_prefs(right)

# ---------------------------
# App Entry
# ---------------------------
def main():
    st.set_page_config(page_title="OSPO Demo", page_icon="📎", layout="wide")
    sidebar_auth()      # login/signup always visible (no extra click)
    page_dashboard()    # left: content, right: preferences (always shown)

if __name__ == "__main__":
    main()
