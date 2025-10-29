# app.py
import os
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Sequence, Any, List, Dict, Set
from collections import defaultdict
from pathlib import Path
import secrets, binascii, hashlib
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta, UTC 

from dotenv import load_dotenv
load_dotenv()

import streamlit as st


# Paths / DB

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get("APP_DB_PATH", str(ROOT / "app.db"))

ARXIV_CATEGORIES = [
    "Physics", "Mathematics", "Quantitative Biology", "Computer Science", "Quantitative Finance",
    "Statistics", "Electrical Engineering and Systems Science", "Economics"
]

def arxiv_category_options() -> List[str]:
    return sorted(ARXIV_CATEGORIES)

@contextmanager
def dbh():
    dbp = Path(DB_PATH)
    dbp.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(dbp), check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.commit()
        con.close()

def q(db, sql: str, params: Sequence[Any] = ()):
    return db.execute(sql, params).fetchall()

def e(db, sql: str, params: Sequence[Any] = ()):
    db.execute(sql, params)


def run_migrations():
    with dbh() as db:
        # users
        e(db, """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT DEFAULT ''
        )
        """)
        # make sure password_hash exists even on older DBs
        cols_users = {r["name"] for r in q(db, "PRAGMA table_info(users)")}
        if "password_hash" not in cols_users:
            e(db, "ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")

        # user_roles
        e(db, """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            UNIQUE(user_id, role),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        # preferences
        e(db, """
        CREATE TABLE IF NOT EXISTS preferences (
            user_id INTEGER PRIMARY KEY,
            categories_json TEXT,
            similarity REAL DEFAULT 0.8,
            max_papers INTEGER DEFAULT 25,
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        # papers
        e(db, """
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            authors TEXT,
            year INTEGER,
            category TEXT,
            categories TEXT,
            keywords_json TEXT,
            abstract TEXT,
            source_url TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # profiles
        e(db, """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            frequency TEXT DEFAULT 'weekly',
            threshold REAL DEFAULT 0.75,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        # profile_keywords
        e(db, """
        CREATE TABLE IF NOT EXISTS profile_keywords (
            profile_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        )
        """)

        # profile_papers
        e(db, """
        CREATE TABLE IF NOT EXISTS profile_papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            paper_id INTEGER NOT NULL,
            UNIQUE(profile_id, paper_id),
            FOREIGN KEY(profile_id) REFERENCES profiles(id),
            FOREIGN KEY(paper_id) REFERENCES papers(id)
        )
        """)

        # recommendations
        e(db, """
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            paper_id INTEGER NOT NULL,
            score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(paper_id) REFERENCES papers(id)
        )
        """)

        # password_resets
        e(db, """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        # helpful indexes
        e(db, "CREATE INDEX IF NOT EXISTS idx_users_email ON users(lower(email))")
        e(db, "CREATE INDEX IF NOT EXISTS idx_profiles_user ON profiles(user_id)")
        e(db, "CREATE INDEX IF NOT EXISTS idx_pref_user ON preferences(user_id)")
        e(db, "CREATE INDEX IF NOT EXISTS idx_rec_user_created ON recommendations(user_id, created_at DESC)")
        e(db, "CREATE INDEX IF NOT EXISTS idx_pp_profile ON profile_papers(profile_id)")
        e(db, "CREATE INDEX IF NOT EXISTS idx_pp_paper ON profile_papers(paper_id)")



# Password hashing (PBKDF2)
PBKDF2_ITER = 200_000

def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER)
    return "pbkdf2$%d$%s$%s" % (PBKDF2_ITER, binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode())

def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters, salt_hex, hash_hex = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False
        iters = int(iters)
        salt = binascii.unhexlify(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return binascii.hexlify(dk).decode() == hash_hex
    except Exception:
        return False

# Password reset helpers

def _create_reset_token(email: str) -> bool:
    email = (email or "").strip().lower()
    if not email:
        return False

    with dbh() as db:
        row = q(db, "SELECT id FROM users WHERE lower(email)=? LIMIT 1", (email,))
        if not row:
            # Don't disclose existence
            return True

        uid = row[0]["id"]
        token = secrets.token_urlsafe(32)
        # timezone-aware UTC
        expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat(timespec="seconds")
        e(db, "INSERT INTO password_resets(user_id, token, expires_at) VALUES (?,?,?)", (uid, token, expires))

    # Email the token (no link)
    body = (
        "Hello,\n\n"
        "Here is your Preprint Bot password reset token (valid for 1 hour):\n\n"
        f"{token}\n\n"
        "Open the app, go to 'Reset password', paste this token, and choose a new password.\n\n"
        "If you didn’t request this, you can ignore this email.\n\n"
        "– Preprint Bot"
    )
    _send_email(email, "Your Preprint Bot reset token", body)
    return True

def _reset_password_with_token(token: str, new_password: str) -> bool:
    token = (token or "").strip()
    if not token or not new_password:
        return False
    now = datetime.utcnow().isoformat(timespec="seconds")
    with dbh() as db:
        rows = q(db, """
            SELECT pr.id, pr.user_id, pr.expires_at, pr.used_at
            FROM password_resets pr
            WHERE pr.token=? LIMIT 1
        """, (token,))
        if not rows:
            return False
        pr = rows[0]
        if pr["used_at"]:
            return False
        if pr["expires_at"] < now:  # ISO timestamps compare lexicographically OK
            return False

        # Update password
        hpw = _hash_password(new_password)
        e(db, "UPDATE users SET password_hash=? WHERE id=?", (hpw, pr["user_id"]))
        e(db, "UPDATE password_resets SET used_at=CURRENT_TIMESTAMP WHERE id=?", (pr["id"],))
        return True


# Authentication

@dataclass
class UserCtx:
    id: int
    email: str
    is_admin: bool

DEMO_ADMIN_EMAIL = "demo_admin@example.com"

def ensure_demo_admin():
    with dbh() as db:
        rows = q(db, "SELECT id, password_hash FROM users WHERE lower(email)=?", (DEMO_ADMIN_EMAIL.lower(),))
        if not rows:
            e(db, "INSERT INTO users(email, password_hash) VALUES (?,?)", (DEMO_ADMIN_EMAIL, _hash_password("demoadmin")))
        else:
            # migrate existing plaintext demo pass, if present
            uid = rows[0]["id"]
            ph = rows[0]["password_hash"] or ""
            if ph and not ph.startswith("pbkdf2$"):
                # assume it's plaintext; re-hash
                e(db, "UPDATE users SET password_hash=? WHERE id=?", (_hash_password(ph), uid))
        # roles (best effort)
        try:
            uid = q(db, "SELECT id FROM users WHERE lower(email)=?", (DEMO_ADMIN_EMAIL.lower(),))[0]["id"]
            has_roles = q(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='user_roles'")
            if has_roles:
                role_row = q(db, "SELECT 1 FROM user_roles WHERE user_id=? AND role='admin' LIMIT 1", (uid,))
                if not role_row:
                    e(db, "INSERT INTO user_roles(user_id, role) VALUES (?, 'admin')", (uid,))
        except Exception:
            pass

def is_admin_email(email: str) -> bool:
    if not email:
        return False
    email = email.lower().strip()
    if email == DEMO_ADMIN_EMAIL.lower():
        return True
    admins = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
    if email in admins:
        return True
    try:
        with dbh() as db:
            t = q(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='user_roles'")
            if not t:
                return False
            uid_row = q(db, "SELECT id FROM users WHERE lower(email)=? LIMIT 1", (email,))
            if not uid_row:
                return False
            uid = uid_row[0]["id"]
            r = q(db, "SELECT 1 FROM user_roles WHERE user_id=? AND role='admin' LIMIT 1", (uid,))
            return bool(r)
    except Exception:
        return False

def set_user_session(email: str) -> UserCtx:
    email = email.strip()
    with dbh() as db:
        row = q(db, "SELECT id, email FROM users WHERE lower(email)=? LIMIT 1", (email.lower(),))
        if not row:
            e(db, "INSERT INTO users(email, password_hash) VALUES (?,?)", (email, ""))
            row = q(db, "SELECT id, email FROM users WHERE lower(email)=? LIMIT 1", (email.lower(),))
    user = UserCtx(id=row[0]["id"], email=row[0]["email"], is_admin=is_admin_email(row[0]["email"]))
    st.session_state["user_ctx"] = user
    return user

def current_user() -> Optional[UserCtx]:
    return st.session_state.get("user_ctx")

def logout():
    if "user_ctx" in st.session_state:
        del st.session_state["user_ctx"]
    st.success("Logged out.")
    st.rerun()
    
def _send_email(to_email: str, subject: str, body: str) -> bool:
    host = os.environ.get("EMAIL_HOST")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")

    if not all([host, port, user, password]):
        st.error("Email not configured. Set EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS in .env")
        return False

    msg = MIMEMultipart()
    msg["From"] = formataddr(("Preprint Bot", user))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as ex:
        st.error(f"Email send failed: {ex}")
        return False


# Category utilities

def _has_column(db, table: str, col: str) -> bool:
    cols = q(db, f"PRAGMA table_info({table})")
    return any((r["name"] == col) for r in cols)

def _categories_from_category_col(db) -> Set[str]:
    vals = q(db, """
        SELECT DISTINCT TRIM(category) AS c
        FROM papers
        WHERE category IS NOT NULL AND TRIM(category) != ''
        ORDER BY c
    """)
    return {r["c"] for r in vals if r["c"]}

def _categories_from_categories_json(db) -> Set[str]:
    cats: Set[str] = set()
    rows = q(db, "SELECT categories FROM papers WHERE categories IS NOT NULL AND TRIM(categories) != ''")
    for r in rows:
        try:
            arr = json.loads(r["categories"])
            if isinstance(arr, list):
                for c in arr:
                    cs = str(c).strip()
                    if cs:
                        cats.add(cs)
            else:
                # sometimes stored as single string
                cs = str(arr).strip()
                if cs:
                    cats.add(cs)
        except Exception:
            # if not json, treat as comma-separated
            raw = str(r["categories"]).strip()
            for cs in [p.strip() for p in raw.split(",") if p.strip()]:
                cats.add(cs)
    return cats

def category_options(user_id: Optional[int] = None) -> List[str]:
    """Return sorted categories from corpus; fallback to user/all prefs; supports `category` or `categories` JSON."""
    cats: Set[str] = set()
    with dbh() as db:
        if _has_column(db, "papers", "category"):
            cats |= _categories_from_category_col(db)
        elif _has_column(db, "papers", "categories"):
            cats |= _categories_from_categories_json(db)

        # fallback to user preferences if corpus is empty
        if not cats and user_id is not None:
            pref = q(db, "SELECT categories_json FROM preferences WHERE user_id=? LIMIT 1", (user_id,))
            if pref:
                try:
                    cats |= {c for c in json.loads(pref[0]["categories_json"] or "[]") if c}
                except Exception:
                    pass

        # fallback to any user's preferences
        if not cats:
            for row in q(db, "SELECT categories_json FROM preferences"):
                try:
                    cats |= {c for c in json.loads(row["categories_json"] or "[]") if c}
                except Exception:
                    pass

    return sorted(cats)


# Render helpers

def paper_card(row: sqlite3.Row, score: Optional[float] = None):
    with st.container(border=True):
        st.markdown(f"#### {row['title']}")
        meta = []
        if row["authors"]: meta.append(row["authors"])
        if "year" in row.keys() and row["year"]: meta.append(str(row["year"]))
        if "category" in row.keys() and row["category"]: meta.append(row["category"])
        if score is not None: meta.append(f"score: {score:.3f}")
        if meta: st.caption(" • ".join(meta))
        try:
            kws = json.loads(row["keywords_json"] or "[]")
            if isinstance(kws, list) and kws:
                st.caption("Keywords: " + ", ".join(map(str, kws)))
        except Exception:
            pass
        if "abstract" in row.keys() and row["abstract"]:
            txt = row["abstract"] or ""
            st.write(txt[:600] + ("…" if len(txt) > 600 else ""))
        if "source_url" in row.keys() and row["source_url"]:
            st.link_button("Open", row["source_url"], use_container_width=False)

def profile_keywords(db, profile_id: int) -> List[str]:
    rows = q(db, "SELECT keyword FROM profile_keywords WHERE profile_id=? ORDER BY keyword", (profile_id,))
    return [r["keyword"] for r in rows]

def profile_papers(db, profile_id: int) -> List[sqlite3.Row]:
    return q(db, """
        SELECT pp.id AS link_id, papers.*
        FROM profile_papers pp
        JOIN papers ON papers.id = pp.paper_id
        WHERE pp.profile_id = ?
        ORDER BY papers.added_at DESC
    """, (profile_id,))


# Pages

def page_dashboard(user: UserCtx) -> None:
    st.markdown("### Welcome back")
    with dbh() as db:
        profiles_count = q(db, "SELECT COUNT(*) c FROM profiles WHERE user_id=?", (user.id,))[0]["c"]
        papers_count   = q(db, "SELECT COUNT(*) c FROM papers")[0]["c"]

    c1, c2 = st.columns(2)
    c1.metric("Your profiles", profiles_count)
    c2.metric("Papers in corpus", papers_count)

    st.divider()
    st.markdown("#### Latest recommendations")
    with dbh() as db:
        rows = q(db, """
            SELECT r.created_at AS created_at, r.score, p.*
            FROM recommendations r
            JOIN papers p ON p.id = r.paper_id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC
            LIMIT 15
        """, (user.id,))
    if not rows:
        st.info("No recommendations yet.")
    else:
        for r in rows:
            paper_card(r, score=r["score"])

def page_profiles(user: UserCtx) -> None:
    st.markdown("### Profiles")
    view = st.segmented_control("View", options=["List", "Create / Edit"], key="p_view", selection_mode="single")

    if view == "List":
        with dbh() as db:
            rows = q(db, "SELECT * FROM profiles WHERE user_id=? ORDER BY created_at DESC", (user.id,))
        if not rows:
            st.info("No profiles yet. Switch to **Create / Edit** to add one.")
            return
        for row in rows:
            with st.container(border=True):
                st.subheader(row["name"])
                c1, c2, c3 = st.columns([1, 1, 3])
                c1.write("**Frequency**"); c1.write(row["frequency"])
                c2.write("**Threshold**"); c2.write(f"{float(row['threshold']):.2f}")
                with dbh() as db:
                    kws = profile_keywords(db, row["id"])
                with c3:
                    st.write("**Keywords**")
                    st.write(", ".join(kws) if kws else "—")

                st.write("**Papers**")
                with dbh() as db:
                    plist = profile_papers(db, row["id"])
                if not plist:
                    st.caption("No papers yet.")
                else:
                    for p in plist:
                        colA, colB = st.columns([6, 1], vertical_alignment="center")
                        with colA:
                            st.write(f"- {p['title']}")
                        with colB:
                            if st.button("Delete", key=f"delpp_{row['id']}_{p['id']}"):
                                with dbh() as db:
                                    e(db, "DELETE FROM profile_papers WHERE profile_id=? AND paper_id=?", (row["id"], p["id"]))
                                st.rerun()

    else:
        mode = st.radio("Mode", ["Create new", "Edit existing"], horizontal=True)
        with dbh() as db:
            existing = q(db, "SELECT id, name FROM profiles WHERE user_id=? ORDER BY name", (user.id,))

        sel_id: Optional[int] = None
        if mode == "Edit existing":
            opts = {"— Select —": None} | {f"{r['name']} (#{r['id']})": r["id"] for r in existing}
            label = st.selectbox("Choose profile", list(opts.keys()))
            sel_id = opts[label]

        if mode == "Create new" or sel_id:
            if sel_id:
                with dbh() as db:
                    prof = q(db, "SELECT * FROM profiles WHERE id=?", (sel_id,))[0]
                    kws_rows = q(db, "SELECT keyword FROM profile_keywords WHERE profile_id=? ORDER BY keyword", (sel_id,))
                default = dict(name=prof["name"], freq=prof["frequency"], th=float(prof["threshold"]), kw=", ".join([r["keyword"] for r in kws_rows]))
            else:
                default = dict(name="", freq="weekly", th=0.75, kw="")

            # Form layout
            with st.form("profile_form", enter_to_submit=True):
                name = st.text_input("Profile name", value=default["name"])
                freq = st.selectbox("Frequency", ["daily", "weekly", "biweekly", "monthly"],
                                    index=["daily", "weekly", "biweekly", "monthly"].index(default["freq"]) if default["freq"] in ["daily", "weekly", "biweekly", "monthly"] else 1)
                th = st.slider("Similarity threshold", 0.0, 1.0, value=default["th"], step=0.01)
                c_kw1, c_kw2 = st.columns([2, 1])
                with c_kw1:
                    kwcsv = st.text_input("Keywords (comma-separated)", value=default["kw"])
                with c_kw2:
                    # category choice here is for filtering the Add Paper picker below
                    prof_cat_opts = ["All"] + arxiv_category_options()
                    st.session_state["profile_add_cat"] = st.selectbox("Category", options=prof_cat_opts, index=0)

                ok = st.form_submit_button("Save")
                if ok:
                    with dbh() as db:
                        if sel_id:
                            e(db, "UPDATE profiles SET name=?, frequency=?, threshold=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                              (name.strip(), freq, float(th), sel_id))
                            e(db, "DELETE FROM profile_keywords WHERE profile_id=?", (sel_id,))
                            for w in [w.strip() for w in kwcsv.split(",") if w.strip()]:
                                e(db, "INSERT INTO profile_keywords(profile_id, keyword) VALUES (?,?)", (sel_id, w))
                            st.success("Profile updated.")
                        else:
                            e(db, "INSERT INTO profiles(user_id, name, frequency, threshold) VALUES (?,?,?,?)",
                              (user.id, name.strip(), freq, float(th)))
                            new_id = q(db, "SELECT last_insert_rowid() AS rid")[0]["rid"]
                            for w in [w.strip() for w in kwcsv.split(",") if w.strip()] :
                                e(db, "INSERT INTO profile_keywords(profile_id, keyword) VALUES (?,?)", (new_id, w))
                            st.success("Profile created.")
                    st.rerun()

            # Add/Delete Papers (uses the chosen category right next to the Keywords input)
            if sel_id:
                st.markdown("##### Add/Delete Papers")
                with dbh() as db:
                    papers = q(db, "SELECT id, title, category FROM papers ORDER BY added_at DESC LIMIT 500")

                cat_sel = st.session_state.get("profile_add_cat", "All")
                filtered = [p for p in papers if (cat_sel == "All" or p["category"] == cat_sel)]
                pick = st.selectbox("Add paper", ["— Select —"] + [f"{p['title']} (#{p['id']})" for p in filtered])
                if pick != "— Select —":
                    pid = int(pick.split("#")[-1].rstrip(")"))
                    if st.button("Add to profile", key=f"addpp_{sel_id}_{pid}"):
                        with dbh() as db:
                            e(db, "INSERT OR IGNORE INTO profile_papers(profile_id, paper_id) VALUES (?,?)", (sel_id, pid))
                        st.success("Added.")
                        st.rerun()

def page_recommendations(user: UserCtx) -> None:
    st.markdown("### Recommendations")

    with dbh() as db:
        authors = [r["authors"] for r in q(db, "SELECT DISTINCT authors FROM papers WHERE authors IS NOT NULL AND authors!='' ORDER BY authors")]
        titles  = [r["title"] for r in q(db, "SELECT DISTINCT title FROM papers ORDER BY title")]
    cats = arxiv_category_options()

    # Filters
    with st.expander("Filters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            dfrom = st.date_input("From", value=None)
        with c2:
            dto   = st.date_input("To", value=None)
        with c3:
            author = st.selectbox("Author", ["Any"] + authors)

        title = st.selectbox("Paper", ["Any"] + titles)
        cat   = st.selectbox("Category", ["Any"] + cats)
        keyw  = st.text_input("Keyword contains")

    params = [user.id]
    where = ["r.user_id=?"]
    if dfrom:
        where.append("date(r.created_at) >= date(?)"); params.append(dfrom.isoformat())
    if dto:
        where.append("date(r.created_at) <= date(?)"); params.append(dto.isoformat())
    if author and author != "Any":
        where.append("p.authors LIKE ?"); params.append(f"%{author}%")
    if title and title != "Any":
        where.append("p.title LIKE ?"); params.append(f"%{title}%")
    if cat and cat != "Any":
        where.append("p.category = ?"); params.append(cat)
    if keyw:
        where.append("(p.keywords_json LIKE ? OR p.abstract LIKE ? OR p.title LIKE ?)")
        params.extend([f"%{keyw}%", f"%{keyw}%", f"%{keyw}%"])

    sql = f"""
      SELECT r.created_at, r.score, p.*
      FROM recommendations r JOIN papers p ON p.id=r.paper_id
      WHERE {' AND '.join(where)}
      ORDER BY r.created_at DESC LIMIT 300
    """
    with dbh() as db:
        rows = q(db, sql, params)

    if not rows:
        st.info("No matching recommendations.")
        return

    grouped: Dict[str, list] = defaultdict(list)
    for r in rows:
        d = str(r["created_at"])[:10]
        grouped[d].append(r)

    for d, items in grouped.items():
        st.subheader(d)
        for r in items:
            paper_card(r, score=r["score"])

def page_settings(user: UserCtx) -> None:
    st.markdown("### Settings")

    # Load or create preferences
    with dbh() as db:
        pref_rows = q(db, "SELECT * FROM preferences WHERE user_id=?", (user.id,))
        if pref_rows:
            pref = pref_rows[0]
            cats_saved = json.loads(pref["categories_json"] or "[]")
            sim = float(pref["similarity"])
            maxp = int(pref["max_papers"])
        else:
            cats_saved, sim, maxp = [], 0.8, 25
            e(db, "INSERT INTO preferences (user_id, categories_json, similarity, max_papers) VALUES (?,?,?,?)",
              (user.id, json.dumps(cats_saved), sim, maxp))

    # Single preferences form
    with st.form("prefs"):
        opts = arxiv_category_options()
        if not opts and cats_saved:
            opts = sorted(set(cats_saved))

        selected_cats = st.multiselect(
            "Categories",
            options=opts,
            default=[c for c in cats_saved if c in opts] or cats_saved
        )

        simv = st.slider("Similarity (global)", 0.0, 1.0, value=sim, step=0.01)
        mp   = st.number_input("Max papers per run", min_value=1, max_value=2000, value=maxp, step=1)

        if st.form_submit_button("Save"):
            with dbh() as db:
                e(db, "UPDATE preferences SET categories_json=?, similarity=?, max_papers=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                  (json.dumps(selected_cats), float(simv), int(mp), user.id))
            st.success("Saved.")

    st.divider()
    if user.is_admin:
        st.markdown("#### Admin Stats")
        with dbh() as db:
            user_cnt = q(db, "SELECT COUNT(*) c FROM users")[0]["c"]
            paper_cnt = q(db, "SELECT COUNT(*) c FROM papers")[0]["c"]
            prof_cnt = q(db, "SELECT COUNT(*) c FROM profiles")[0]["c"]
            rec_cnt = q(db, "SELECT COUNT(*) c FROM recommendations")[0]["c"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Users", user_cnt)
        c2.metric("Papers", paper_cnt)
        c3.metric("Profiles", prof_cnt)
        c4.metric("Recommendations", rec_cnt)

# App Frame

def _login(email: str, password: str) -> bool:
    if not email or not password:
        st.warning("Enter email and password.")
        return False
    with dbh() as db:
        row = q(db, "SELECT id, email, password_hash FROM users WHERE lower(email)=? LIMIT 1", (email.lower().strip(),))
        if not row:
            st.error("Account not found.")
            return False
        stored = row[0]["password_hash"] or ""
        ok = _verify_password(password, stored)
        if ok:
            set_user_session(row[0]["email"])
            return True
        # if stored looked like plaintext, accept once and re-hash
        if stored and not stored.startswith("pbkdf2$") and stored == password:
            e(db, "UPDATE users SET password_hash=? WHERE id=?", (_hash_password(password), row[0]["id"]))
            set_user_session(row[0]["email"])
            return True
        st.error("Incorrect password.")
        return False

def _create_account(email: str, password: str, confirm: str) -> bool:
    if not email or not password:
        st.warning("Enter email and password.")
        return False
    if password != confirm:
        st.error("Passwords do not match.")
        return False
    with dbh() as db:
        exists = q(db, "SELECT 1 FROM users WHERE lower(email)=? LIMIT 1", (email.lower().strip(),))
        if exists:
            st.error("An account with this email already exists.")
            return False
        e(db, "INSERT INTO users(email, password_hash) VALUES (?,?)", (email.strip(), _hash_password(password)))
    set_user_session(email.strip())
    st.success("Account created.")
    return True

def auth_bar():
    user = current_user()
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    # Top bar
    left, right = st.columns([3, 1])
    with left:
        if not user:
            st.caption("Welcome. Please sign in.")
        else:
            st.caption(f"Signed in as: **{user.email}**" + ("  •  admin" if user.is_admin else ""))
    with right:
        if user:
            if st.button("Logout", use_container_width=True, key="logout_btn"):
                logout()

    if not user:
        mode = st.session_state["auth_mode"]
        if mode == "login":
            with st.container(border=True):
                st.subheader("Sign in")
                with st.form("login_form", enter_to_submit=True):
                    email = st.text_input("Email", key="login_email", placeholder="you@example.com")
                    pwd   = st.text_input("Password", key="login_pwd", type="password", placeholder="••••••••")

                    # buttons
                    b1, b2 = st.columns([1, 1])
                    with b1:
                        do_login = st.form_submit_button("Login", use_container_width=True)
                    with b2:
                        to_signup = st.form_submit_button("Create account", use_container_width=True)

                if do_login and _login(email, pwd):
                    st.rerun()
                if to_signup:
                    st.session_state["auth_mode"] = "signup"
                    st.rerun()
                #forgot pass button
                c_forgot, _ = st.columns([1, 3])
                with c_forgot:
                    if st.button("Forgot password?"):
                        st.session_state["auth_mode"] = "forgot"
                        st.rerun()
                
                # quick demo admin
                demo_col, _ = st.columns([1, 3])
                with demo_col:
                    if st.button("Demo Admin", key="demo_admin_btn", use_container_width=True):
                        ensure_demo_admin()
                        if _login(DEMO_ADMIN_EMAIL, "demoadmin"):
                            st.rerun()

        elif mode == "signup":
            with st.container(border=True):
                st.subheader("Create account")
                with st.form("signup_form", enter_to_submit=True):
                    email = st.text_input("Email", key="signup_email", placeholder="you@example.com")
                    pwd   = st.text_input("Password", key="signup_pwd", type="password", placeholder="Choose a password")
                    cpw   = st.text_input("Confirm password", key="signup_cpw", type="password", placeholder="Repeat")

                    # Create + Back to login
                    b1, b2 = st.columns([1, 1])
                    with b1:
                        ok = st.form_submit_button("Create account", use_container_width=True)
                    with b2:
                        to_login = st.form_submit_button("Back to login", use_container_width=True)

                if ok and _create_account(email, pwd, cpw):
                    st.rerun()
                if to_login:
                    st.session_state["auth_mode"] = "login"
                    st.rerun()

        elif mode == "forgot":
            with st.container(border=True):
                st.subheader("Forgot password")
                st.caption("Enter your account email; we’ll generate a one-time reset token (valid 1 hour).")
                with st.form("forgot_form", enter_to_submit=True):
                    email_f = st.text_input("Email", key="forgot_email", placeholder="you@example.com")
                    send_btn = st.form_submit_button("Send reset token", use_container_width=True)
                if send_btn:
                    ok = _create_reset_token(email_f)
                    if ok:
                        st.success("If that email exists, we’ve sent a reset link.")
                    else:
                        st.error("Please enter a valid email.")
        
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("I have a token"):
                        st.session_state["auth_mode"] = "reset"
                        st.rerun()
                with c2:
                    if st.button("Back to login"):
                        st.session_state["auth_mode"] = "login"
                        st.rerun()

        elif mode == "reset":
            with st.container(border=True):
                st.subheader("Reset password")
                with st.form("reset_form", enter_to_submit=True):
                    token = st.text_input("Reset token", placeholder="Paste the token")
                    npw   = st.text_input("New password", type="password")
                    cnpw  = st.text_input("Confirm password", type="password")
                    okbtn = st.form_submit_button("Reset password", use_container_width=True)
                if okbtn:
                    if npw != cnpw:
                        st.error("Passwords do not match.")
                    else:
                        if _reset_password_with_token(token, npw):
                            st.success("Password updated. Please log in.")
                            st.session_state["auth_mode"] = "login"
                            st.rerun()
                        else:
                            st.error("Invalid or expired token.")
                if st.button("Back to login"):
                    st.session_state["auth_mode"] = "login"
                    st.rerun()

    

def main():
    st.set_page_config(
        page_title="Preprint Bot",
        page_icon="PB",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    run_migrations() 
    st.title("Preprint Bot")
    auth_bar()

    user = current_user()
    if not user:
        st.info("Please log in to continue.")
        return

    tabs = st.tabs(["Dashboard", "Profiles", "Recommendations", "Settings"])
    with tabs[0]:
        page_dashboard(user)
    with tabs[1]:
        page_profiles(user)
    with tabs[2]:
        page_recommendations(user)
    with tabs[3]:
        page_settings(user)

if __name__ == "__main__":
    main()
