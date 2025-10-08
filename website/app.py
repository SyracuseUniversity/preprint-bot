# app.py
import os
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Sequence, Any, List, Dict, Set
from collections import defaultdict
from pathlib import Path

import streamlit as st


# Paths / DB

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get("APP_DB_PATH", str(ROOT / "app.db"))

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


# Authentication

@dataclass
class UserCtx:
    id: int
    email: str
    is_admin: bool

DEMO_ADMIN_EMAIL = "demo_admin@example.com"

def ensure_demo_admin():
    with dbh() as db:
        rows = q(db, "SELECT id FROM users WHERE lower(email)=?", (DEMO_ADMIN_EMAIL.lower(),))
        if not rows:
            e(db, "INSERT INTO users(email, password_hash) VALUES (?,?)", (DEMO_ADMIN_EMAIL, "demoadmin"))
        # add user_roles(user_id, role) if the table exists
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


# Category utilities (for `category` or `categories` JSON)

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
                    prof_cat_opts = ["All"] + category_options(user.id)
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
    cats = category_options(user.id)

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
        opts = category_options(user.id)
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
    else:
        st.caption("Admin stats are available to admin users only.")

# App Frame

def auth_bar():
    user = current_user()
    left, right = st.columns([3,1])
    with left:
        if not user:
            st.text_input("Email", key="login_email", placeholder="you@example.com")
        else:
            st.caption(f"Signed in as: **{user.email}**" + ("  •  admin" if user.is_admin else ""))
    with right:
        if not user:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login", use_container_width=True, key="login_btn"):
                    email = st.session_state.get("login_email", "").strip()
                    if email:
                        set_user_session(email)
                        st.rerun()
                    else:
                        st.warning("Enter an email to login.")
            with col2:
                if st.button("Demo Admin", use_container_width=True, key="demo_admin_btn"):
                    ensure_demo_admin()
                    set_user_session("demo_admin@example.com")
                    st.rerun()
        else:
            if st.button("Logout", use_container_width=True, key="logout_btn"):
                logout()

def main():
    st.set_page_config(page_title="Research Recs", page_icon="🧠", layout="wide")
    st.title("Research Recs")
    auth_bar()

    user = current_user()
    if not user:
        st.info("Please log in to continue.")
        return

    st.sidebar.title("Main")
    nav = st.sidebar.radio("Navigation", ["Dashboard","Profiles","Recommendations","Settings"], label_visibility="collapsed")

    if nav == "Dashboard":
        page_dashboard(user)
    elif nav == "Profiles":
        page_profiles(user)
    elif nav == "Recommendations":
        page_recommendations(user)
    elif nav == "Settings":
        page_settings(user)

if __name__ == "__main__":
    main()
