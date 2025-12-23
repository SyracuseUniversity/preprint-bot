import streamlit as st
from typing import Optional, Dict, List
from api_client.sync_client import SyncWebAPIClient
from st_ant_tree import st_ant_tree
import sys
from pathlib import Path

# Add website directory to path
sys.path.insert(0, str(Path(__file__).parent))

# ==================== ARXIV CATEGORY TREE ====================

ARXIV_CATEGORY_TREE: List[Dict] = [
    {
        "title": "Computer Science",
        "value": "cs",
        "children": [
            {"title": "Artificial Intelligence (cs.AI)", "value": "cs.AI"},
            {"title": "Hardware Architecture (cs.AR)", "value": "cs.AR"},
            {"title": "Computational Complexity (cs.CC)", "value": "cs.CC"},
            {"title": "Computational Engineering, Finance, and Science (cs.CE)", "value": "cs.CE"},
            {"title": "Computational Geometry (cs.CG)", "value": "cs.CG"},
            {"title": "Computation and Language (cs.CL)", "value": "cs.CL"},
            {"title": "Cryptography and Security (cs.CR)", "value": "cs.CR"},
            {"title": "Computer Vision and Pattern Recognition (cs.CV)", "value": "cs.CV"},
            {"title": "Computers and Society (cs.CY)", "value": "cs.CY"},
            {"title": "Databases (cs.DB)", "value": "cs.DB"},
            {"title": "Distributed, Parallel, and Cluster Computing (cs.DC)", "value": "cs.DC"},
            {"title": "Digital Libraries (cs.DL)", "value": "cs.DL"},
            {"title": "Discrete Mathematics (cs.DM)", "value": "cs.DM"},
            {"title": "Data Structures and Algorithms (cs.DS)", "value": "cs.DS"},
            {"title": "Emerging Technologies (cs.ET)", "value": "cs.ET"},
            {"title": "Formal Languages and Automata Theory (cs.FL)", "value": "cs.FL"},
            {"title": "General Literature (cs.GL)", "value": "cs.GL"},
            {"title": "Graphics (cs.GR)", "value": "cs.GR"},
            {"title": "Computer Science and Game Theory (cs.GT)", "value": "cs.GT"},
            {"title": "Human-Computer Interaction (cs.HC)", "value": "cs.HC"},
            {"title": "Information Retrieval (cs.IR)", "value": "cs.IR"},
            {"title": "Information Theory (cs.IT)", "value": "cs.IT"},
            {"title": "Machine Learning (cs.LG)", "value": "cs.LG"},
            {"title": "Logic in Computer Science (cs.LO)", "value": "cs.LO"},
            {"title": "Multiagent Systems (cs.MA)", "value": "cs.MA"},
            {"title": "Multimedia (cs.MM)", "value": "cs.MM"},
            {"title": "Mathematical Software (cs.MS)", "value": "cs.MS"},
            {"title": "Numerical Analysis (cs.NA)", "value": "cs.NA"},
            {"title": "Neural and Evolutionary Computing (cs.NE)", "value": "cs.NE"},
            {"title": "Networking and Internet Architecture (cs.NI)", "value": "cs.NI"},
            {"title": "Other Computer Science (cs.OH)", "value": "cs.OH"},
            {"title": "Operating Systems (cs.OS)", "value": "cs.OS"},
            {"title": "Performance (cs.PF)", "value": "cs.PF"},
            {"title": "Programming Languages (cs.PL)", "value": "cs.PL"},
            {"title": "Robotics (cs.RO)", "value": "cs.RO"},
            {"title": "Symbolic Computation (cs.SC)", "value": "cs.SC"},
            {"title": "Sound (cs.SD)", "value": "cs.SD"},
            {"title": "Software Engineering (cs.SE)", "value": "cs.SE"},
            {"title": "Social and Information Networks (cs.SI)", "value": "cs.SI"},
            {"title": "Systems and Control (cs.SY)", "value": "cs.SY"},
        ],
    },
    {
        "title": "Mathematics",
        "value": "math",
        "children": [
            {"title": "Commutative Algebra (math.AC)", "value": "math.AC"},
            {"title": "Algebraic Geometry (math.AG)", "value": "math.AG"},
            {"title": "Analysis of PDEs (math.AP)", "value": "math.AP"},
            {"title": "Algebraic Topology (math.AT)", "value": "math.AT"},
            {"title": "Classical Analysis and ODEs (math.CA)", "value": "math.CA"},
            {"title": "Combinatorics (math.CO)", "value": "math.CO"},
            {"title": "Category Theory (math.CT)", "value": "math.CT"},
            {"title": "Complex Variables (math.CV)", "value": "math.CV"},
            {"title": "Differential Geometry (math.DG)", "value": "math.DG"},
            {"title": "Dynamical Systems (math.DS)", "value": "math.DS"},
            {"title": "Functional Analysis (math.FA)", "value": "math.FA"},
            {"title": "General Mathematics (math.GM)", "value": "math.GM"},
            {"title": "General Topology (math.GN)", "value": "math.GN"},
            {"title": "Group Theory (math.GR)", "value": "math.GR"},
            {"title": "Geometric Topology (math.GT)", "value": "math.GT"},
            {"title": "History and Overview (math.HO)", "value": "math.HO"},
            {"title": "Information Theory (math.IT)", "value": "math.IT"},
            {"title": "Number Theory (math.NT)", "value": "math.NT"},
            {"title": "Optimization and Control (math.OC)", "value": "math.OC"},
            {"title": "Probability (math.PR)", "value": "math.PR"},
            {"title": "Statistics Theory (math.ST)", "value": "math.ST"},
        ],
    },
    {
        "title": "Statistics",
        "value": "stat",
        "children": [
            {"title": "Applications (stat.AP)", "value": "stat.AP"},
            {"title": "Computation (stat.CO)", "value": "stat.CO"},
            {"title": "Methodology (stat.ME)", "value": "stat.ME"},
            {"title": "Machine Learning (stat.ML)", "value": "stat.ML"},
            {"title": "Other Statistics (stat.OT)", "value": "stat.OT"},
            {"title": "Statistics Theory (stat.TH)", "value": "stat.TH"},
        ],
    },
]

def _build_arxiv_code_to_label() -> Dict[str, str]:
    """Build mapping of category codes to labels"""
    out: Dict[str, str] = {}

    def walk(nodes: List[Dict]):
        for n in nodes:
            v = n.get("value")
            t = n.get("title")
            if v and t:
                if "(" in t and ")" in t:
                    out[v] = t
                else:
                    out[v] = f"{t} ({v})"
            for ch in n.get("children") or []:
                walk([ch])

    walk(ARXIV_CATEGORY_TREE)
    return out

ARXIV_CODE_TO_LABEL: Dict[str, str] = _build_arxiv_code_to_label()

# ==================== SESSION STATE & API CLIENT ====================

def get_api_client() -> SyncWebAPIClient:
    """Get or create API client"""
    if 'api_client' not in st.session_state:
        st.session_state['api_client'] = SyncWebAPIClient()
    return st.session_state['api_client']

def get_current_user() -> Optional[Dict]:
    """Get currently logged in user"""
    return st.session_state.get('user')

def set_current_user(user: Dict):
    """Set current user in session"""
    st.session_state['user'] = user

def logout():
    """Logout current user"""
    if 'user' in st.session_state:
        del st.session_state['user']
    st.success("Logged out successfully")
    st.rerun()

# ==================== AUTH PAGES ====================

def login_page():
    """Login page"""
    st.subheader("Sign in")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Login", use_container_width=True)
        with col2:
            signup = st.form_submit_button("Create Account", use_container_width=True)
    
    if submit:
        if not email or not password:
            st.error("Please enter email and password")
            return
        
        try:
            api = get_api_client()
            result = api.login(email, password)
            set_current_user(result)
            st.success("Logged in successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
    
    if signup:
        st.session_state['show_signup'] = True
        st.rerun()
    
    # Forgot password link
    col_forgot, _ = st.columns([1, 3])
    with col_forgot:
        if st.button("Forgot password?"):
            st.session_state['show_forgot'] = True
            st.rerun()

def signup_page():
    """Signup page"""
    st.subheader("Create Account")
    
    with st.form("signup_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        name = st.text_input("Name (optional)")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Create Account", use_container_width=True)
        with col2:
            back = st.form_submit_button("Back to Login", use_container_width=True)
    
    if submit:
        if not email or not password:
            st.error("Email and password are required")
        elif password != confirm:
            st.error("Passwords don't match")
        else:
            try:
                api = get_api_client()
                result = api.register(email, password, name or None)
                set_current_user(result)
                st.success("Account created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Registration failed: {str(e)}")
    
    if back:
        st.session_state['show_signup'] = False
        st.rerun()

def forgot_password_page():
    """Forgot password page"""
    st.subheader("Forgot Password")
    st.caption("Enter your email to receive a password reset token")
    
    with st.form("forgot_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        submit = st.form_submit_button("Send Reset Token", use_container_width=True)
    
    if submit:
        if not email:
            st.error("Please enter your email")
        else:
            try:
                api = get_api_client()
                result = api.request_password_reset(email)
                st.success("If that email exists, we've sent a reset token")
                
                # For development: show the token
                if 'token' in result:
                    st.info(f"Development Mode - Your reset token: {result['token']}")
                
                if st.button("I have a token"):
                    st.session_state['show_reset'] = True
                    st.session_state['show_forgot'] = False
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    if st.button("Back to Login"):
        st.session_state['show_forgot'] = False
        st.rerun()

def reset_password_page():
    """Reset password page"""
    st.subheader("Reset Password")
    
    with st.form("reset_form"):
        token = st.text_input("Reset Token", placeholder="Paste your token here")
        new_password = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Reset Password", use_container_width=True)
    
    if submit:
        if not token or not new_password:
            st.error("Token and new password are required")
        elif new_password != confirm:
            st.error("Passwords don't match")
        else:
            try:
                api = get_api_client()
                api.reset_password(token, new_password)
                st.success("Password reset successfully! Please log in.")
                st.session_state['show_reset'] = False
                st.rerun()
            except Exception as e:
                st.error(f"Reset failed: {str(e)}")
    
    if st.button("Back to Login"):
        st.session_state['show_reset'] = False
        st.rerun()

# ==================== MAIN PAGES ====================

def dashboard_page(user: Dict):
    """Dashboard page"""
    st.markdown("### Dashboard")
    st.markdown(f"Welcome back, **{user.get('name') or user['email']}**")
    
    api = get_api_client()
    
    try:
        # Get stats
        profiles = api.get_user_profiles(user['user_id'])
        corpora = api.get_user_corpora(user['user_id'])
        
        col1, col2 = st.columns(2)
        col1.metric("Your Profiles", len(profiles))
        col2.metric("Your Corpora", len(corpora))
        
        st.divider()
        st.markdown("#### Recent Recommendations")
        
        recommendations = api.get_user_recommendations(user['user_id'], limit=10)
        
        if not recommendations:
            st.info("No recommendations yet. Create a profile and run the recommendation pipeline!")
        else:
            for rec in recommendations[:10]:
                with st.container(border=True):
                    st.markdown(f"**{rec['title']}**")
                    st.caption(f"Score: {rec['score']:.3f} | arXiv: {rec.get('arxiv_id', 'N/A')}")
                    
                    if rec.get('abstract'):
                        abstract_text = rec['abstract'][:300]
                        st.write(abstract_text + ("..." if len(rec['abstract']) > 300 else ""))
                    
                    if rec.get('arxiv_id'):
                        url = f"https://arxiv.org/abs/{rec['arxiv_id']}"
                        st.link_button("View on arXiv", url)
    
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")

def profiles_page(user: Dict):
    """Profiles management page with integrated paper upload"""
    st.markdown("### Profiles")
    
    api = get_api_client()
    view = st.radio("View", ["List", "Create/Edit"], horizontal=True)
    
    if view == "List":
        try:
            profiles = api.get_user_profiles(user['user_id'])
            
            if not profiles:
                st.info("No profiles yet. Switch to **Create/Edit** to add one.")
            else:
                for profile in profiles:
                    with st.container(border=True):
                        st.subheader(profile['name'])
                        
                        col1, col2, col3 = st.columns(3)
                        col1.write(f"**Frequency:** {profile['frequency']}")
                        col2.write(f"**Threshold:** {profile['threshold']}")
                        
                        # Show keywords
                        keywords_display = ', '.join(profile['keywords'][:3])
                        if len(profile['keywords']) > 3:
                            keywords_display += f" (+{len(profile['keywords']) - 3} more)"
                        col3.write(f"**Keywords:** {keywords_display}")
                        
                        st.divider()
                        
                        # ============ PAPER UPLOAD SECTION ============
                        st.markdown("#### 📄 Papers")
                        
                        # Show uploaded papers
                        try:
                            papers_data = api.list_uploaded_papers(user['user_id'], profile['id'])
                            papers = papers_data.get('papers', [])
                            
                            if papers:
                                st.write(f"**{len(papers)} paper(s) uploaded**")
                                
                                # Show papers in expandable section
                                with st.expander("View Papers", expanded=False):
                                    for paper in papers:
                                        paper_col1, paper_col2, paper_col3 = st.columns([3, 1, 1])
                                        
                                        with paper_col1:
                                            st.write(f"📄 {paper['filename']}")
                                        with paper_col2:
                                            st.caption(f"{paper['size_mb']} MB")
                                        with paper_col3:
                                            if st.button("🗑️", key=f"del_{profile['id']}_{paper['filename']}", 
                                                        help="Delete this paper"):
                                                try:
                                                    api.delete_uploaded_paper(
                                                        user['user_id'],
                                                        profile['id'],
                                                        paper['filename']
                                                    )
                                                    st.success(f"Deleted {paper['filename']}")
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"Delete failed: {str(e)}")
                            else:
                                st.caption("No papers uploaded yet")
                            
                            # Upload new papers
                            with st.expander("📤 Upload Papers", expanded=False):
                                uploaded_files = st.file_uploader(
                                    "Choose PDF files",
                                    type=['pdf'],
                                    accept_multiple_files=True,
                                    key=f"upload_{profile['id']}",
                                    help="Upload one or more PDF papers for this profile"
                                )
                                
                                if uploaded_files:
                                    if st.button("Upload Files", key=f"upload_btn_{profile['id']}", type="primary"):
                                        progress_bar = st.progress(0)
                                        status_text = st.empty()
                                        
                                        uploaded_count = 0
                                        total_files = len(uploaded_files)
                                        
                                        for i, uploaded_file in enumerate(uploaded_files):
                                            try:
                                                status_text.text(f"Uploading {uploaded_file.name}...")
                                                
                                                # Read file bytes
                                                file_bytes = uploaded_file.read()
                                                
                                                # Upload to backend
                                                result = api.upload_paper_bytes(
                                                    user['user_id'],
                                                    profile['id'],
                                                    uploaded_file.name,
                                                    file_bytes
                                                )
                                                
                                                uploaded_count += 1
                                                progress_bar.progress((i + 1) / total_files)
                                                
                                            except Exception as e:
                                                st.error(f"Failed to upload {uploaded_file.name}: {str(e)}")
                                        
                                        status_text.text("")
                                        progress_bar.empty()
                                        
                                        if uploaded_count > 0:
                                            st.success(f"Successfully uploaded {uploaded_count} file(s)!")
                                            st.rerun()
                            
                            # Process papers button
                            if papers:
                                with st.expander("⚙️ Process Papers", expanded=False):
                                    st.info(
                                        "Processing will:\n"
                                        "- Extract text from PDFs using GROBID\n"
                                        "- Generate embeddings\n"
                                        "- Store papers in database\n"
                                        "- Enable recommendations"
                                    )
                                    
                                    if st.button("Process All Papers", 
                                               key=f"process_{profile['id']}", 
                                               type="primary"):
                                        try:
                                            with st.spinner("Starting processing..."):
                                                result = api.trigger_processing(
                                                    user['user_id'], 
                                                    profile['id']
                                                )
                                            
                                            st.success(
                                                "✅ Processing started! Papers are being processed in the background. "
                                                "This may take a few minutes. Check the Dashboard for results."
                                            )
                                            
                                        except Exception as e:
                                            st.error(f"Failed to start processing: {str(e)}")
                        
                        except Exception as e:
                            st.error(f"Error managing papers: {str(e)}")
                        
                        st.divider()
                        
                        # ============ DELETE PROFILE SECTION ============
                        # Delete button with confirmation
                        confirm_key = f"confirm_delete_{profile['id']}"
                        if st.session_state.get(confirm_key):
                            st.warning("⚠️ Are you sure? This will delete the profile and all uploaded papers. This cannot be undone.")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("Yes, delete", key=f"yes_{profile['id']}", type="primary"):
                                    try:
                                        api.delete_profile(profile['id'])
                                        st.session_state.pop(confirm_key)
                                        st.success("Profile deleted")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                            with col_no:
                                if st.button("Cancel", key=f"no_{profile['id']}"):
                                    st.session_state.pop(confirm_key)
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete Profile", key=f"del_{profile['id']}"):
                                st.session_state[confirm_key] = True
                                st.rerun()
        
        except Exception as e:
            st.error(f"Error loading profiles: {str(e)}")
    
    else:  # Create/Edit
        with st.form("profile_form"):
            name = st.text_input("Profile Name")
            frequency = st.selectbox("Frequency", ["daily", "weekly", "biweekly", "monthly"])
            threshold = st.selectbox("Threshold", ["low", "medium", "high"])
            keywords = st.text_input("Keywords (comma-separated)", 
                                    placeholder="machine learning, neural networks, optimization")
            
            st.write("**Select arXiv Categories** (optional)")
            selected_cats = st_ant_tree(
                treeData=ARXIV_CATEGORY_TREE,
                treeCheckable=True,
                showSearch=True,
                placeholder="Select categories",
                max_height=300,
                only_children_select=True
            )
            
            submit = st.form_submit_button("Create Profile")
        
        if submit:
            if not name:
                st.error("Profile name is required")
            elif not keywords:
                st.error("At least one keyword is required")
            else:
                try:
                    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
                    api.create_profile(
                        user_id=user['user_id'],
                        name=name,
                        keywords=kw_list,
                        frequency=frequency,
                        threshold=threshold
                    )
                    st.success("Profile created successfully! Go to 'List' view to upload papers.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating profile: {str(e)}")

def recommendations_page(user: Dict):
    """Recommendations page"""
    st.markdown("### Recommendations")
    
    api = get_api_client()
    
    try:
        recommendations = api.get_user_recommendations(user['user_id'], limit=100)
        
        if not recommendations:
            st.info("No recommendations yet. Run the recommendation pipeline to generate recommendations.")
            st.markdown("**To generate recommendations:**")
            st.code("python -m preprint_bot.pipeline --mode user --uid <your_user_id>")
        else:
            # Filters
            with st.expander("Filters", expanded=False):
                min_score = st.slider("Minimum Score", 0.0, 1.0, 0.5, 0.01)
                
                # Category filter
                all_categories = set()
                for rec in recommendations:
                    if rec.get('categories'):
                        if isinstance(rec['categories'], list):
                            all_categories.update(rec['categories'])
                
                selected_category = st.selectbox(
                    "Category",
                    ["All"] + sorted(list(all_categories))
                )
            
            # Apply filters
            filtered = [r for r in recommendations if r['score'] >= min_score]
            
            if selected_category != "All":
                filtered = [
                    r for r in filtered 
                    if selected_category in (r.get('categories') or [])
                ]
            
            st.write(f"Showing {len(filtered)} of {len(recommendations)} recommendations")
            
            # Sort by score
            filtered.sort(key=lambda x: x['score'], reverse=True)
            
            for rec in filtered:
                with st.container(border=True):
                    st.markdown(f"#### {rec['title']}")
                    st.caption(f"Score: {rec['score']:.3f} | arXiv: {rec.get('arxiv_id', 'N/A')}")
                    
                    if rec.get('abstract'):
                        abstract_text = rec['abstract'][:400]
                        st.write(abstract_text + ("..." if len(rec['abstract']) > 400 else ""))
                    
                    if rec.get('arxiv_id'):
                        url = f"https://arxiv.org/abs/{rec['arxiv_id']}"
                        st.link_button("View on arXiv", url)
    
    except Exception as e:
        st.error(f"Error loading recommendations: {str(e)}")

def settings_page(user: Dict):
    """Settings page"""
    st.markdown("### Settings")
    
    api = get_api_client()
    
    with st.form("settings_form"):
        st.markdown("#### Profile Information")
        new_name = st.text_input("Name", value=user.get('name') or "")
        new_email = st.text_input("Email", value=user['email'])
        
        submit = st.form_submit_button("Update Profile")
    
    if submit:
        try:
            updated = api.update_user(
                user['user_id'],
                email=new_email if new_email != user['email'] else None,
                name=new_name if new_name != user.get('name') else None
            )
            set_current_user(updated)
            st.success("Profile updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Update failed: {str(e)}")
    
    st.divider()
    
    # System info
    st.markdown("#### System Information")
    st.caption(f"User ID: {user['user_id']}")
    st.caption(f"Account created: {user.get('created_at', 'N/A')}")

# ==================== MAIN APP ====================

def main():
    st.set_page_config(
        page_title="Preprint Bot",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Preprint Bot")
    
    # Check authentication
    user = get_current_user()
    
    if not user:
        # Show appropriate auth page
        if st.session_state.get('show_signup'):
            signup_page()
        elif st.session_state.get('show_forgot'):
            forgot_password_page()
        elif st.session_state.get('show_reset'):
            reset_password_page()
        else:
            login_page()
        return
    
    # Logged in - show main app
    with st.sidebar:
        st.write(f"**{user.get('name') or user['email']}**")
        st.caption(f"User ID: {user['user_id']}")
        if st.button("Logout", use_container_width=True):
            logout()
    
# Main navigation
    tabs = st.tabs(["Dashboard", "Profiles", "Recommendations", "Settings"])
    
    with tabs[0]:
        dashboard_page(user)
    with tabs[1]:
        profiles_page(user)
    with tabs[2]:
        recommendations_page(user)
    with tabs[3]:
        settings_page(user)

if __name__ == "__main__":
    main()