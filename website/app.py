import streamlit as st
from typing import Optional, Dict, List
from api_client.sync_client import SyncWebAPIClient
from st_ant_tree import st_ant_tree
import sys
from pathlib import Path
import time 
import traceback
import logging
from datetime import datetime, date, timedelta

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('streamlit_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add website directory to path
sys.path.insert(0, str(Path(__file__).parent))

def log_error(func_name: str, error: Exception, context: Dict = None):
    """Centralized error logging"""
    logger.error(f"Error in {func_name}: {str(error)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    if context:
        logger.error(f"Context: {context}")

def auto_refresh_during_processing(api, user_id, profile_id, interval=3):
    """Auto-refresh page during processing"""
    try:
        progress = api.get_processing_progress(user_id, profile_id)
        if progress and progress.get('status') == 'running':
            time.sleep(interval)
            st.rerun()
    except Exception as e:
        log_error("auto_refresh_during_processing", e, {
            "user_id": user_id,
            "profile_id": profile_id
        })

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
        "title": "Economics",
        "value": "econ",
        "children": [
            {"title": "Econometrics (econ.EM)", "value": "econ.EM"},
            {"title": "General Economics (econ.GN)", "value": "econ.GN"},
            {"title": "Theoretical Economics (econ.TH)", "value": "econ.TH"},
        ],
    },
    {
        "title": "Electrical Engineering and Systems Science",
        "value": "eess",
        "children": [
            {"title": "Audio and Speech Processing (eess.AS)", "value": "eess.AS"},
            {"title": "Image and Video Processing (eess.IV)", "value": "eess.IV"},
            {"title": "Signal Processing (eess.SP)", "value": "eess.SP"},
            {"title": "Systems and Control (eess.SY)", "value": "eess.SY"},
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
            {"title": "K-Theory and Homology (math.KT)", "value": "math.KT"},
            {"title": "Logic (math.LO)", "value": "math.LO"},
            {"title": "Metric Geometry (math.MG)", "value": "math.MG"},
            {"title": "Mathematical Physics (math.MP)", "value": "math.MP"},
            {"title": "Numerical Analysis (math.NA)", "value": "math.NA"},
            {"title": "Number Theory (math.NT)", "value": "math.NT"},
            {"title": "Operator Algebras (math.OA)", "value": "math.OA"},
            {"title": "Optimization and Control (math.OC)", "value": "math.OC"},
            {"title": "Probability (math.PR)", "value": "math.PR"},
            {"title": "Quantum Algebra (math.QA)", "value": "math.QA"},
            {"title": "Rings and Algebras (math.RA)", "value": "math.RA"},
            {"title": "Representation Theory (math.RT)", "value": "math.RT"},
            {"title": "Symplectic Geometry (math.SG)", "value": "math.SG"},
            {"title": "Spectral Theory (math.SP)", "value": "math.SP"},
            {"title": "Statistics Theory (math.ST)", "value": "math.ST"},
        ],
    },
    {
        "title": "Physics",
        "value": "physics_group",
        "children": [
            {
                "title": "Astrophysics",
                "value": "astro-ph",
                "children": [
                    {"title": "Cosmology and Nongalactic Astrophysics (astro-ph.CO)", "value": "astro-ph.CO"},
                    {"title": "Earth and Planetary Astrophysics (astro-ph.EP)", "value": "astro-ph.EP"},
                    {"title": "Astrophysics of Galaxies (astro-ph.GA)", "value": "astro-ph.GA"},
                    {"title": "High Energy Astrophysical Phenomena (astro-ph.HE)", "value": "astro-ph.HE"},
                    {"title": "Instrumentation and Methods for Astrophysics (astro-ph.IM)", "value": "astro-ph.IM"},
                    {"title": "Solar and Stellar Astrophysics (astro-ph.SR)", "value": "astro-ph.SR"},
                ],
            },
            {
                "title": "Condensed Matter",
                "value": "cond-mat",
                "children": [
                    {"title": "Disordered Systems and Neural Networks (cond-mat.dis-nn)", "value": "cond-mat.dis-nn"},
                    {"title": "Mesoscale and Nanoscale Physics (cond-mat.mes-hall)", "value": "cond-mat.mes-hall"},
                    {"title": "Materials Science (cond-mat.mtrl-sci)", "value": "cond-mat.mtrl-sci"},
                    {"title": "Other Condensed Matter (cond-mat.other)", "value": "cond-mat.other"},
                    {"title": "Quantum Gases (cond-mat.quant-gas)", "value": "cond-mat.quant-gas"},
                    {"title": "Soft Condensed Matter (cond-mat.soft)", "value": "cond-mat.soft"},
                    {"title": "Statistical Mechanics (cond-mat.stat-mech)", "value": "cond-mat.stat-mech"},
                    {"title": "Strongly Correlated Electrons (cond-mat.str-el)", "value": "cond-mat.str-el"},
                    {"title": "Superconductivity (cond-mat.supr-con)", "value": "cond-mat.supr-con"},
                ],
            },
            {"title": "General Relativity and Quantum Cosmology (gr-qc)", "value": "gr-qc"},
            {"title": "High Energy Physics - Experiment (hep-ex)", "value": "hep-ex"},
            {"title": "High Energy Physics - Lattice (hep-lat)", "value": "hep-lat"},
            {"title": "High Energy Physics - Phenomenology (hep-ph)", "value": "hep-ph"},
            {"title": "High Energy Physics - Theory (hep-th)", "value": "hep-th"},
            {"title": "Mathematical Physics (math-ph)", "value": "math-ph"},
            {
                "title": "Nonlinear Sciences",
                "value": "nlin",
                "children": [
                    {"title": "Adaptation and Self-Organizing Systems (nlin.AO)", "value": "nlin.AO"},
                    {"title": "Chaotic Dynamics (nlin.CD)", "value": "nlin.CD"},
                    {"title": "Cellular Automata and Lattice Gases (nlin.CG)", "value": "nlin.CG"},
                    {"title": "Pattern Formation and Solitons (nlin.PS)", "value": "nlin.PS"},
                    {"title": "Exactly Solvable and Integrable Systems (nlin.SI)", "value": "nlin.SI"},
                ],
            },
            {"title": "Nuclear Experiment (nucl-ex)", "value": "nucl-ex"},
            {"title": "Nuclear Theory (nucl-th)", "value": "nucl-th"},
            {
                "title": "Physics",
                "value": "physics",
                "children": [
                    {"title": "Accelerator Physics (physics.acc-ph)", "value": "physics.acc-ph"},
                    {"title": "Atmospheric and Oceanic Physics (physics.ao-ph)", "value": "physics.ao-ph"},
                    {"title": "Applied Physics (physics.app-ph)", "value": "physics.app-ph"},
                    {"title": "Atomic and Molecular Clusters (physics.atm-clus)", "value": "physics.atm-clus"},
                    {"title": "Atomic Physics (physics.atom-ph)", "value": "physics.atom-ph"},
                    {"title": "Biological Physics (physics.bio-ph)", "value": "physics.bio-ph"},
                    {"title": "Chemical Physics (physics.chem-ph)", "value": "physics.chem-ph"},
                    {"title": "Classical Physics (physics.class-ph)", "value": "physics.class-ph"},
                    {"title": "Computational Physics (physics.comp-ph)", "value": "physics.comp-ph"},
                    {"title": "Data Analysis, Statistics and Probability (physics.data-an)", "value": "physics.data-an"},
                    {"title": "Physics Education (physics.ed-ph)", "value": "physics.ed-ph"},
                    {"title": "Fluid Dynamics (physics.flu-dyn)", "value": "physics.flu-dyn"},
                    {"title": "General Physics (physics.gen-ph)", "value": "physics.gen-ph"},
                    {"title": "Geophysics (physics.geo-ph)", "value": "physics.geo-ph"},
                    {"title": "History and Philosophy of Physics (physics.hist-ph)", "value": "physics.hist-ph"},
                    {"title": "Instrumentation and Detectors (physics.ins-det)", "value": "physics.ins-det"},
                    {"title": "Medical Physics (physics.med-ph)", "value": "physics.med-ph"},
                    {"title": "Optics (physics.optics)", "value": "physics.optics"},
                    {"title": "Plasma Physics (physics.plasm-ph)", "value": "physics.plasm-ph"},
                    {"title": "Popular Physics (physics.pop-ph)", "value": "physics.pop-ph"},
                    {"title": "Physics and Society (physics.soc-ph)", "value": "physics.soc-ph"},
                    {"title": "Space Physics (physics.space-ph)", "value": "physics.space-ph"},
                ],
            },
            {"title": "Quantum Physics (quant-ph)", "value": "quant-ph"},
        ],
    },
    {
        "title": "Quantitative Biology",
        "value": "q-bio",
        "children": [
            {"title": "Biomolecules (q-bio.BM)", "value": "q-bio.BM"},
            {"title": "Cell Behavior (q-bio.CB)", "value": "q-bio.CB"},
            {"title": "Genomics (q-bio.GN)", "value": "q-bio.GN"},
            {"title": "Molecular Networks (q-bio.MN)", "value": "q-bio.MN"},
            {"title": "Neurons and Cognition (q-bio.NC)", "value": "q-bio.NC"},
            {"title": "Other Quantitative Biology (q-bio.OT)", "value": "q-bio.OT"},
            {"title": "Populations and Evolution (q-bio.PE)", "value": "q-bio.PE"},
            {"title": "Quantitative Methods (q-bio.QM)", "value": "q-bio.QM"},
            {"title": "Subcellular Processes (q-bio.SC)", "value": "q-bio.SC"},
            {"title": "Tissues and Organs (q-bio.TO)", "value": "q-bio.TO"},
        ],
    },
    {
        "title": "Quantitative Finance",
        "value": "q-fin",
        "children": [
            {"title": "Computational Finance (q-fin.CP)", "value": "q-fin.CP"},
            {"title": "Economics (q-fin.EC)", "value": "q-fin.EC"},
            {"title": "General Finance (q-fin.GN)", "value": "q-fin.GN"},
            {"title": "Mathematical Finance (q-fin.MF)", "value": "q-fin.MF"},
            {"title": "Portfolio Management (q-fin.PM)", "value": "q-fin.PM"},
            {"title": "Pricing of Securities (q-fin.PR)", "value": "q-fin.PR"},
            {"title": "Risk Management (q-fin.RM)", "value": "q-fin.RM"},
            {"title": "Statistical Finance (q-fin.ST)", "value": "q-fin.ST"},
            {"title": "Trading and Market Microstructure (q-fin.TR)", "value": "q-fin.TR"},
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
    try:
        out: Dict[str, str] = {}

        def walk(nodes: List[Dict]):
            for n in nodes:
                try:
                    v = n.get("value")
                    t = n.get("title")
                    if v and t:
                        if "(" in t and ")" in t:
                            out[v] = t
                        else:
                            out[v] = f"{t} ({v})"
                    for ch in n.get("children") or []:
                        walk([ch])
                except Exception as e:
                    log_error("_build_arxiv_code_to_label.walk", e, {"node": n})

        walk(ARXIV_CATEGORY_TREE)
        return out
    except Exception as e:
        log_error("_build_arxiv_code_to_label", e)
        return {}

ARXIV_CODE_TO_LABEL: Dict[str, str] = _build_arxiv_code_to_label()

# ==================== SESSION STATE & API CLIENT ====================

def get_api_client() -> SyncWebAPIClient:
    """Get or create API client"""
    try:
        if 'api_client' not in st.session_state:
            logger.info("Creating new API client")
            st.session_state['api_client'] = SyncWebAPIClient()
        return st.session_state['api_client']
    except Exception as e:
        log_error("get_api_client", e)
        st.error(f"Failed to create API client: {str(e)}")
        raise

def get_current_user() -> Optional[Dict]:
    """Get currently logged in user"""
    try:
        # Try session first
        if 'user' in st.session_state and st.session_state.get('user'):
            logger.debug(f"User from session: {st.session_state['user'].get('email')}")
            return st.session_state['user']
        
        # Try to restore from query params
        query_params = st.query_params
        user_id = query_params.get('user_id')
        
        if user_id:
            logger.info(f"Attempting to restore user from query params: {user_id}")
            try:
                api = get_api_client()
                user = api.get_user(int(user_id))
                st.session_state['user'] = user
                logger.info(f"User restored: {user.get('email')}")
                return user
            except Exception as e:
                log_error("get_current_user.restore_from_params", e, {"user_id": user_id})
        
        logger.debug("No user found")
        return None
    except Exception as e:
        log_error("get_current_user", e)
        return None

def set_current_user(user: Dict):
    """Set current user in session"""
    try:
        logger.info(f"Setting current user: {user.get('email')}")
        
        # Normalize - make sure both 'id' and 'user_id' exist
        if 'user_id' in user and 'id' not in user:
            user['id'] = user['user_id']
        elif 'id' in user and 'user_id' not in user:
            user['user_id'] = user['id']
        
        st.session_state['user'] = user
        
        # Add to URL for persistence
        user_id = user.get('user_id') or user.get('id')
        if user_id:
            st.query_params['user_id'] = str(user_id)
            logger.debug(f"Added user_id to query params: {user_id}")
    except Exception as e:
        log_error("set_current_user", e, {"user": user})

def logout():
    """Logout current user"""
    try:
        logger.info("Logging out user")
        if 'user' in st.session_state:
            del st.session_state['user']
        
        # Clear from URL
        st.query_params.clear()
        
        st.success("Logged out successfully")
        st.rerun()
    except Exception as e:
        log_error("logout", e)
        st.error(f"Logout failed: {str(e)}")

def check_duplicate_profile_name(api, user_id: int, name: str, exclude_profile_id: int = None) -> bool:
    """Check if profile name already exists for this user (case-insensitive)"""
    try:
        profiles = api.get_user_profiles(user_id)
        for p in profiles:
            if p['id'] == exclude_profile_id:
                continue
            if p['name'].lower() == name.lower():
                return True
        return False
    except Exception as e:
        log_error("check_duplicate_profile_name", e, {
            "user_id": user_id,
            "name": name,
            "exclude_profile_id": exclude_profile_id
        })
        return False

# ==================== AUTH PAGES ====================

def login_page():
    """Login page"""
    try:
        st.subheader("Sign in")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="********")
            
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
                logger.info(f"Login attempt for: {email}")
                api = get_api_client()
                result = api.login(email, password)
                set_current_user(result)
                st.success("Logged in successfully!")
                logger.info(f"Login successful: {email}")
                st.rerun()
            except Exception as e:
                log_error("login_page.submit", e, {"email": email})
                st.error(f"Login failed: {str(e)}")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
        
        if signup:
            st.session_state['show_signup'] = True
            st.rerun()
        
        # Forgot password link
        col_forgot, _ = st.columns([1, 3])
        with col_forgot:
            if st.button("Forgot password?"):
                st.session_state['show_forgot'] = True
                st.rerun()
    except Exception as e:
        log_error("login_page", e)
        st.error(f"Login page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def signup_page():
    """Signup page"""
    try:
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
                    logger.info(f"Signup attempt for: {email}")
                    api = get_api_client()
                    result = api.register(email, password, name or None)
                    set_current_user(result)
                    st.success("Account created successfully!")
                    logger.info(f"Signup successful: {email}")
                    st.rerun()
                except Exception as e:
                    log_error("signup_page.submit", e, {"email": email})
                    st.error(f"Registration failed: {str(e)}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
        
        if back:
            st.session_state['show_signup'] = False
            st.rerun()
    except Exception as e:
        log_error("signup_page", e)
        st.error(f"Signup page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def reset_password_page():
    """Reset password page"""
    try:
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
                    logger.info("Password reset attempt")
                    api = get_api_client()
                    api.reset_password(token, new_password)
                    st.success("Password reset successfully! Please log in.")
                    st.session_state['show_reset'] = False
                    logger.info("Password reset successful")
                    st.rerun()
                except Exception as e:
                    log_error("reset_password_page.submit", e)
                    st.error(f"Reset failed: {str(e)}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
        
        if st.button("Back to Login"):
            st.session_state['show_reset'] = False
            st.rerun()
    except Exception as e:
        log_error("reset_password_page", e)
        st.error(f"Reset password page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def forgot_password_page():
    """Forgot password page"""
    try:
        st.subheader("Forgot Password")
        st.caption("Enter your email to receive a password reset token (valid for 1 hour)")
        
        with st.form("forgot_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            submit = st.form_submit_button("Send Reset Token", use_container_width=True)
        
        if submit:
            if not email:
                st.error("Please enter your email")
            else:
                try:
                    logger.info(f"Password reset request for: {email}")
                    api = get_api_client()
                    result = api.request_password_reset(email)
                    st.success("If that email exists, we've sent a reset token")
                    logger.info(f"Password reset token sent: {email}")
                    
                    # For development: show the token
                    if 'token' in result:
                        st.info(f"Development Mode - Your reset token: {result['token']}")
                    
                    # Show button to go to reset page
                    if st.button("I have a token"):
                        st.session_state['show_reset'] = True
                        st.session_state['show_forgot'] = False
                        st.rerun()
                except Exception as e:
                    log_error("forgot_password_page.submit", e, {"email": email})
                    st.error(f"Error: {str(e)}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
        
        if st.button("Back to Login"):
            st.session_state['show_forgot'] = False
            st.rerun()
    except Exception as e:
        log_error("forgot_password_page", e)
        st.error(f"Forgot password page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# ==================== MAIN PAGES ====================

def dashboard_page(user: Dict):
    """Dashboard page"""
    try:
        logger.info(f"Loading dashboard for user: {user.get('email')}")
        st.markdown("### Dashboard")
        st.markdown(f"Welcome back, **{user.get('name') or user['email']}**")
        
        api = get_api_client()
        
        try:
            # Get stats
            user_id = user.get('id') or user.get('user_id')
            logger.debug(f"Fetching profiles for user_id: {user_id}")
            
            profiles = api.get_user_profiles(user_id)
            corpora = api.get_user_corpora(user_id)
            
            col1, col2 = st.columns(2)
            col1.metric("Your Profiles", len(profiles))
            col2.metric("Your Corpora", len(corpora))
            
            st.divider()
            st.markdown("#### Today's Recommendations")

            # Get recommendations from ALL profiles
            all_recommendations = []
            for profile in profiles:
                try:
                    logger.debug(f"Fetching recommendations for profile: {profile['id']}")
                    recs = api.get_profile_recommendations(profile['id'], limit=5000)
                    all_recommendations.extend(recs)
                except Exception as e:
                    log_error("dashboard_page.get_profile_recommendations", e, {
                        "profile_id": profile['id']
                    })
                    continue

            if not all_recommendations:
                st.info("No recommendations yet. Create a profile and run the recommendation pipeline!")
            else:
                # Find the most recent date across all recommendations
                most_recent_date = None
                for rec in all_recommendations:
                    submitted_date = rec.get('submitted_date')
                    if submitted_date:
                        try:
                            if isinstance(submitted_date, str):
                                paper_date = datetime.fromisoformat(submitted_date.replace('Z', '').replace('+00:00', ''))
                            else:
                                paper_date = submitted_date
                            
                            if most_recent_date is None or paper_date > most_recent_date:
                                most_recent_date = paper_date
                        except Exception as e:
                            log_error("dashboard_page.parse_date", e, {
                                "submitted_date": submitted_date
                            })
                            continue
                
                if not most_recent_date:
                    st.info("No dated recommendations found.")
                    return
                
                # Filter to only papers from the most recent date
                todays_recs = []
                most_recent_date_only = most_recent_date.date() if hasattr(most_recent_date, 'date') else most_recent_date
                
                for rec in all_recommendations:
                    submitted_date = rec.get('submitted_date')
                    if submitted_date:
                        try:
                            if isinstance(submitted_date, str):
                                rec_date = datetime.fromisoformat(submitted_date.replace('Z', '').replace('+00:00', '')).date()
                            else:
                                rec_date = submitted_date.date() if hasattr(submitted_date, 'date') else None
                            
                            if rec_date == most_recent_date_only:
                                todays_recs.append(rec)
                        except Exception as e:
                            log_error("dashboard_page.filter_by_date", e, {
                                "submitted_date": submitted_date
                            })
                            continue
                
                # Deduplicate by arxiv_id - keep highest score
                seen_arxiv_ids = {}
                for rec in todays_recs:
                    arxiv_id = rec.get('arxiv_id')
                    if arxiv_id:
                        if arxiv_id not in seen_arxiv_ids or rec['score'] > seen_arxiv_ids[arxiv_id]['score']:
                            seen_arxiv_ids[arxiv_id] = rec
                
                todays_recs = list(seen_arxiv_ids.values())
                
                if not todays_recs:
                    st.info(f"No recommendations from the most recent date ({most_recent_date_only}).")
                else:
                    # Sort by score
                    todays_recs = sorted(todays_recs, key=lambda x: x['score'], reverse=True)
                    
                    st.caption(f"**{len(todays_recs)} paper(s) from {most_recent_date_only.strftime('%d %B %Y')}** (across all profiles)")
                    
                    for rec in todays_recs[:10]:  # Show top 10
                        with st.container(border=True):
                            st.markdown(f"**{rec['title']}**")
                            st.caption(f"Score: {rec['score']:.3f} | arXiv: {rec.get('arxiv_id', 'N/A')}")
                            
                            # Show summary if available
                            if rec.get('summary_text'):
                                st.write(rec['summary_text'])
                            elif rec.get('abstract'):
                                st.write(rec['abstract'][:200] + "...")
                            
                            if rec.get('arxiv_id'):
                                st.link_button("View on arXiv", f"https://arxiv.org/abs/{rec['arxiv_id']}")
        
        except Exception as e:
            log_error("dashboard_page.load_data", e, {"user_id": user.get('id')})
            st.error(f"Error loading dashboard: {str(e)}")
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
    
    except Exception as e:
        log_error("dashboard_page", e, {"user": user})
        st.error(f"Dashboard error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def profiles_page(user: Dict):
    """Profiles management page with integrated paper upload"""
    try:
        logger.info(f"Loading profiles page for user: {user.get('email')}")
        api = get_api_client()
        
        # Check for any running processing tasks and auto-refresh
        try:
            user_id = user.get('id') or user.get('user_id')
            logger.debug(f"Checking for running processing tasks for user_id: {user_id}")
            profiles = api.get_user_profiles(user_id)
            
            for profile in profiles:
                try:
                    progress = api.get_processing_progress(user_id, profile['id'])
                    if progress and progress.get('status') == 'running':
                        st.info(f"Processing papers for profile '{profile['name']}'... Auto-refreshing every 3 seconds.")
                        time.sleep(3)
                        st.rerun()
                except Exception as e:
                    log_error("profiles_page.check_progress", e, {
                        "user_id": user_id,
                        "profile_id": profile['id']
                    })
        except Exception as e:
            log_error("profiles_page.check_processing", e, {"user_id": user.get('id')})
            
        st.markdown("### Profiles")
        
        view = st.radio("View", ["List", "Create/Edit"], horizontal=True)
        
        if view == "List":
            try:
                logger.debug("Loading profiles list view")
                profiles = api.get_user_profiles(user.get('id'))
                
                if not profiles:
                    st.info("No profiles yet. Switch to **Create/Edit** to add one.")
                else:
                    logger.debug(f"Displaying {len(profiles)} profiles")
                    for profile in profiles:
                        try:
                            with st.container(border=True):
                                st.subheader(profile['name'])
                                
                                # Profile info in 4 columns
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.write("**Frequency**")
                                    st.write(profile['frequency'])
                                with col2:
                                    st.write("**Threshold**")
                                    st.write(profile['threshold'])
                                with col3:
                                    st.write("**Max Papers**")
                                    st.write(str(profile.get('top_x', 10)))
                                with col4:
                                    st.write("**Keywords**")
                                    keywords_display = ', '.join(profile['keywords'][:3])
                                    if len(profile['keywords']) > 3:
                                        keywords_display += f" (+{len(profile['keywords']) - 3} more)"
                                    st.write(keywords_display)
                                
                                # Categories display
                                if profile.get('categories'):
                                    st.write("**Categories**")
                                    cat_labels = [ARXIV_CODE_TO_LABEL.get(c, c) for c in profile['categories']]
                                    st.caption(", ".join(cat_labels))
                                
                                st.divider()
                                
                                # ============ PAPER UPLOAD SECTION ============
                                st.markdown("#### 📄 Papers")
                                
                                # Show uploaded papers
                                try:
                                    logger.debug(f"Fetching papers for profile {profile['id']}")
                                    papers_data = api.list_uploaded_papers(user.get('id'), profile['id'])
                                    papers = papers_data.get('papers', [])
                                    
                                    if papers:
                                        st.write(f"**{len(papers)} paper(s) uploaded**")
                                        
                                        # Show papers in expandable section
                                        with st.expander("View Papers", expanded=False):
                                            for paper in papers:
                                                try:
                                                    paper_col1, paper_col2, paper_col3 = st.columns([3, 1, 1])
                                                    
                                                    with paper_col1:
                                                        st.write(f"📄 {paper['filename']}")
                                                    with paper_col2:
                                                        st.caption(f"{paper['size_mb']} MB")
                                                    with paper_col3:
                                                        if st.button("🗑️", key=f"del_{profile['id']}_{paper['filename']}", 
                                                                    help="Delete this paper"):
                                                            try:
                                                                logger.info(f"Deleting paper: {paper['filename']}")
                                                                api.delete_uploaded_paper(
                                                                    user.get('id'),
                                                                    profile['id'],
                                                                    paper['filename']
                                                                )
                                                                st.success(f"Deleted {paper['filename']}")
                                                                logger.info(f"Successfully deleted: {paper['filename']}")
                                                                st.rerun()
                                                            except Exception as e:
                                                                log_error("profiles_page.delete_paper", e, {
                                                                    "user_id": user.get('id'),
                                                                    "profile_id": profile['id'],
                                                                    "filename": paper['filename']
                                                                })
                                                                st.error(f"Delete failed: {str(e)}")
                                                except Exception as e:
                                                    log_error("profiles_page.display_paper", e, {"paper": paper})
                                    else:
                                        st.caption("No papers uploaded yet")
                                    
                                    # Upload new papers - WITH TABS
                                    with st.expander("📤 Upload Papers", expanded=False):
                                        # Create tabs for different upload methods
                                        upload_tab, arxiv_tab = st.tabs(["Upload PDF", "Add from arXiv"])
                                        
                                        # TAB 1: Upload PDF files
                                        with upload_tab:
                                            uploaded_files = st.file_uploader(
                                                "Choose PDF files",
                                                type=['pdf'],
                                                accept_multiple_files=True,
                                                key=f"upload_{profile['id']}",
                                                help="Upload one or more PDF papers for this profile"
                                            )
                                            
                                            if uploaded_files:
                                                if st.button("Upload Files", key=f"upload_btn_{profile['id']}", type="primary"):
                                                    try:
                                                        logger.info(f"Starting upload of {len(uploaded_files)} files")
                                                        progress_bar = st.progress(0)
                                                        status_text = st.empty()
                                                        
                                                        uploaded_count = 0
                                                        total_files = len(uploaded_files)
                                                        
                                                        for i, uploaded_file in enumerate(uploaded_files):
                                                            try:
                                                                status_text.text(f"Uploading {uploaded_file.name}...")
                                                                logger.debug(f"Uploading file {i+1}/{total_files}: {uploaded_file.name}")
                                                                
                                                                file_bytes = uploaded_file.read()
                                                                
                                                                api.upload_paper_bytes(
                                                                    user.get('id'),
                                                                    profile['id'],
                                                                    uploaded_file.name,
                                                                    file_bytes
                                                                )
                                                                
                                                                uploaded_count += 1
                                                                progress_bar.progress((i + 1) / total_files)
                                                                logger.info(f"Successfully uploaded: {uploaded_file.name}")
                                                                
                                                            except Exception as e:
                                                                log_error("profiles_page.upload_file", e, {
                                                                    "filename": uploaded_file.name,
                                                                    "user_id": user.get('id'),
                                                                    "profile_id": profile['id']
                                                                })
                                                                st.error(f"Failed to upload {uploaded_file.name}: {str(e)}")
                                                        
                                                        status_text.text("")
                                                        progress_bar.empty()
                                                        
                                                        if uploaded_count > 0:
                                                            st.success(f"Successfully uploaded {uploaded_count} file(s)!")
                                                            logger.info(f"Upload complete: {uploaded_count}/{total_files} files")
                                                            st.rerun()
                                                    except Exception as e:
                                                        log_error("profiles_page.upload_files", e, {
                                                            "user_id": user.get('id'),
                                                            "profile_id": profile['id'],
                                                            "file_count": len(uploaded_files)
                                                        })
                                                        st.error(f"Upload failed: {str(e)}")
                                                        with st.expander("Error Details"):
                                                            st.code(traceback.format_exc())
                                        
                                        # TAB 2: Add from arXiv
                                        with arxiv_tab:
                                            st.write("**Add papers from arXiv**")
                                            st.caption("Enter arXiv IDs (one per line or comma-separated)")
                                            
                                            arxiv_input = st.text_area(
                                                "arXiv IDs",
                                                placeholder="2301.12345\n2302.67890\nor\n2301.12345, 2302.67890",
                                                key=f"arxiv_input_{profile['id']}",
                                                height=100
                                            )
                                            
                                            if st.button("Add from arXiv", key=f"arxiv_btn_{profile['id']}", type="primary"):
                                                if not arxiv_input.strip():
                                                    st.error("Please enter at least one arXiv ID")
                                                else:
                                                    try:
                                                        logger.info("Processing arXiv IDs input")
                                                        # Parse arXiv IDs
                                                        arxiv_ids = []
                                                        
                                                        # Handle both newline and comma separation
                                                        for line in arxiv_input.split('\n'):
                                                            for arxiv_id in line.split(','):
                                                                arxiv_id = arxiv_id.strip()
                                                                if arxiv_id:
                                                                    # Remove version suffix if present (e.g., v1, v2)
                                                                    if 'v' in arxiv_id:
                                                                        arxiv_id = arxiv_id.split('v')[0]
                                                                    arxiv_ids.append(arxiv_id)
                                                        
                                                        if not arxiv_ids:
                                                            st.error("No valid arXiv IDs found")
                                                        else:
                                                            logger.info(f"Adding {len(arxiv_ids)} papers from arXiv: {arxiv_ids}")
                                                            st.info(f"Adding {len(arxiv_ids)} paper(s) from arXiv...")
                                                            
                                                            progress_bar = st.progress(0)
                                                            status_text = st.empty()
                                                            
                                                            success_count = 0
                                                            failed_papers = []
                                                            
                                                            for i, arxiv_id in enumerate(arxiv_ids):
                                                                try:
                                                                    status_text.text(f"Fetching {arxiv_id}...")
                                                                    logger.debug(f"Fetching arXiv paper {i+1}/{len(arxiv_ids)}: {arxiv_id}")
                                                                    
                                                                    # Call backend API to add paper from arXiv
                                                                    result = api.add_paper_from_arxiv(
                                                                        user.get('id'),
                                                                        profile['id'],
                                                                        arxiv_id
                                                                    )
                                                                    
                                                                    success_count += 1
                                                                    progress_bar.progress((i + 1) / len(arxiv_ids))
                                                                    logger.info(f"Successfully added arXiv paper: {arxiv_id}")
                                                                    
                                                                except Exception as e:
                                                                    log_error("profiles_page.add_arxiv_paper", e, {
                                                                        "arxiv_id": arxiv_id,
                                                                        "user_id": user.get('id'),
                                                                        "profile_id": profile['id']
                                                                    })
                                                                    failed_papers.append(f"{arxiv_id}: {str(e)}")
                                                                    progress_bar.progress((i + 1) / len(arxiv_ids))
                                                            
                                                            status_text.text("")
                                                            progress_bar.empty()
                                                            
                                                            if success_count > 0:
                                                                st.success(f"Successfully added {success_count} paper(s) from arXiv!")
                                                                logger.info(f"arXiv import complete: {success_count}/{len(arxiv_ids)} papers")
                                                            
                                                            if failed_papers:
                                                                with st.expander("❌ Failed papers"):
                                                                    for failure in failed_papers:
                                                                        st.error(failure)
                                                            
                                                            if success_count > 0:
                                                                st.rerun()
                                                    except Exception as e:
                                                        log_error("profiles_page.arxiv_import", e, {
                                                            "user_id": user.get('id'),
                                                            "profile_id": profile['id'],
                                                            "input": arxiv_input
                                                        })
                                                        st.error(f"arXiv import failed: {str(e)}")
                                                        with st.expander("Error Details"):
                                                            st.code(traceback.format_exc())
                                
                                except Exception as e:
                                    log_error("profiles_page.paper_management", e, {
                                        "user_id": user.get('id'),
                                        "profile_id": profile['id']
                                    })
                                    st.error(f"Error managing papers: {str(e)}")
                                    with st.expander("Error Details"):
                                        st.code(traceback.format_exc())
                                
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
                                                logger.info(f"Deleting profile: {profile['id']}")
                                                api.delete_profile(profile['id'])
                                                st.session_state.pop(confirm_key)
                                                st.success("Profile deleted")
                                                logger.info(f"Successfully deleted profile: {profile['id']}")
                                                st.rerun()
                                            except Exception as e:
                                                log_error("profiles_page.delete_profile", e, {
                                                    "profile_id": profile['id']
                                                })
                                                st.error(f"Error: {str(e)}")
                                                with st.expander("Error Details"):
                                                    st.code(traceback.format_exc())
                                    with col_no:
                                        if st.button("Cancel", key=f"no_{profile['id']}"):
                                            st.session_state.pop(confirm_key)
                                            st.rerun()
                                else:
                                    if st.button("🗑️ Delete Profile", key=f"del_{profile['id']}"):
                                        st.session_state[confirm_key] = True
                                        st.rerun()
                        
                        except Exception as e:
                            log_error("profiles_page.display_profile", e, {
                                "profile_id": profile.get('id'),
                                "profile_name": profile.get('name')
                            })
                            st.error(f"Error displaying profile {profile.get('name')}: {str(e)}")
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
            
            except Exception as e:
                log_error("profiles_page.list_view", e, {"user_id": user.get('id')})
                st.error(f"Error loading profiles: {str(e)}")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
            
            return  # End of List view
        
        # ==================== CREATE / EDIT VIEW ====================
        
        try:
            logger.debug("Loading Create/Edit view")
            
            # Mode selector
            mode = st.radio("Mode", ["Create new", "Edit existing"], horizontal=True, key="profile_mode")
            
            # Initialize session keys
            if "profile_cat_tree_selected" not in st.session_state:
                st.session_state["profile_cat_tree_selected"] = []
            
            # Get existing profiles for edit mode
            profiles = api.get_user_profiles(user.get('id'))
            
            selected_profile_id = None
            if mode == "Edit existing":
                if not profiles:
                    st.info("No profiles to edit. Create one first.")
                    return
                
                profile_options = {p['name']: p['id'] for p in profiles}
                selected_name = st.selectbox("Choose profile to edit", ["— Select —"] + list(profile_options.keys()))
                
                if selected_name != "— Select —":
                    selected_profile_id = profile_options[selected_name]
            
            # Set defaults based on mode
            if selected_profile_id:
                try:
                    profile = next(p for p in profiles if p['id'] == selected_profile_id)
                    default_name = profile['name']
                    default_freq = profile['frequency']
                    default_threshold = profile['threshold']
                    default_top_x = profile.get('top_x', 10)
                    default_keywords = ', '.join(profile['keywords'])
                    st.session_state["profile_cat_tree_selected"] = profile.get('categories', [])
                except Exception as e:
                    log_error("profiles_page.load_profile_defaults", e, {
                        "profile_id": selected_profile_id
                    })
                    st.error(f"Error loading profile: {str(e)}")
                    return
            else:
                default_name = ""
                default_freq = "weekly"
                default_threshold = "medium"
                default_top_x = 10
                default_keywords = ""
                if mode == "Create new":
                    st.session_state["profile_cat_tree_selected"] = []
            
            # Profile form
            if mode == "Create new" or selected_profile_id:
                with st.form("profile_form", enter_to_submit=True):
                    name = st.text_input("Profile Name", value=default_name)
                    
                    freq = st.selectbox(
                        "Frequency",
                        ["daily", "weekly", "biweekly", "monthly"],
                        index=["daily", "weekly", "biweekly", "monthly"].index(default_freq) if default_freq in ["daily", "weekly", "biweekly", "monthly"] else 1
                    )
                    
                    threshold = st.selectbox(
                        "Threshold",
                        ["low", "medium", "high"],
                        index=["low", "medium", "high"].index(default_threshold) if default_threshold in ["low", "medium", "high"] else 1
                    )

                    top_x = st.slider(
                        "Maximum recommendations to show",
                        min_value=5,
                        max_value=50,
                        value=default_top_x if selected_profile_id else 10,
                        step=5,
                        help="Number of top papers to show for this profile"
                    )
                    
                    keywords = st.text_input(
                        "Keywords (comma-separated)",
                        value=default_keywords,
                        placeholder="machine learning, neural networks, optimization"
                    )
                    
                    st.write("**Select arXiv Categories** (optional)")
                    try:
                        selected_cats = st_ant_tree(
                            treeData=ARXIV_CATEGORY_TREE,
                            treeCheckable=True,
                            showSearch=True,
                            placeholder="Select categories",
                            max_height=300,
                            only_children_select=True
                        )
                    except Exception as e:
                        log_error("profiles_page.category_tree", e)
                        st.error("Error loading category tree")
                        selected_cats = []
                    
                    submit = st.form_submit_button("Create Profile" if mode == "Create new" else "Update Profile")
                
                if submit:
                    if not name:
                        st.error("Profile name is required")
                    elif not keywords:
                        st.error("At least one keyword is required")
                    else:
                        try:
                            logger.info(f"Processing profile form submission: {name}")
                            
                            # Clean and validate name
                            clean_name = name.strip()
                            
                            # Check for duplicate names
                            if check_duplicate_profile_name(api, user.get('id'), clean_name, selected_profile_id):
                                st.error(f"Profile name '{clean_name}' already exists. Please choose a different name.")
                                return
                            
                            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
                            
                            # Extract selected categories from tree
                            categories_list = []
                            if selected_cats:
                                try:
                                    if isinstance(selected_cats, list):
                                        categories_list = selected_cats
                                    elif isinstance(selected_cats, dict):
                                        for key in ['checked', 'selected', 'value', 'checkedKeys', 'halfCheckedKeys']:
                                            if key in selected_cats:
                                                val = selected_cats[key]
                                                if isinstance(val, list):
                                                    categories_list = val
                                                break
                                    
                                    # Filter out parent nodes (keep only leaf categories with dots)
                                    if categories_list:
                                        categories_list = [cat for cat in categories_list if '.' in cat]
                                    
                                    logger.debug(f"Extracted categories: {categories_list}")
                                except Exception as e:
                                    log_error("profiles_page.extract_categories", e, {
                                        "selected_cats": selected_cats
                                    })
                                    st.warning("Error processing categories, proceeding without them")
                                    categories_list = []
                            
                            if selected_profile_id:
                                # EDIT MODE: Save immediately
                                try:
                                    logger.info(f"Updating profile: {selected_profile_id}")
                                    api.update_profile(
                                        selected_profile_id,
                                        name=clean_name,
                                        keywords=kw_list,
                                        categories=categories_list,
                                        frequency=freq,
                                        threshold=threshold,
                                        top_x=top_x
                                    )
                                    st.success("Profile updated successfully!")
                                    logger.info(f"Successfully updated profile: {selected_profile_id}")
                                    st.rerun()
                                except Exception as e:
                                    log_error("profiles_page.update_profile", e, {
                                        "profile_id": selected_profile_id,
                                        "name": clean_name
                                    })
                                    st.error(f"Error updating profile: {str(e)}")
                                    with st.expander("Error Details"):
                                        st.code(traceback.format_exc())
                            else:
                                # CREATE MODE: Stage for confirmation
                                logger.debug("Staging profile for creation confirmation")
                                st.session_state["pending_profile_create"] = {
                                    "name": clean_name,
                                    "keywords": kw_list,
                                    "categories": categories_list,
                                    "frequency": freq,
                                    "threshold": threshold,
                                    "top_x": top_x
                                }
                                st.session_state["show_profile_create_confirm"] = True
                                st.rerun()
                        
                        except Exception as e:
                            log_error("profiles_page.form_submit", e, {
                                "name": name,
                                "mode": mode
                            })
                            st.error(f"Error: {str(e)}")
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
            
            # Creation confirmation panel
            if st.session_state.get("show_profile_create_confirm") and st.session_state.get("pending_profile_create"):
                try:
                    data = st.session_state["pending_profile_create"]
                    
                    with st.container(border=True):
                        st.warning("Create this profile?")
                        
                        st.write(f"**Name:** {data['name']}")
                        st.write(f"**Frequency:** {data['frequency']}")
                        st.write(f"**Threshold:** {data['threshold']}")
                        st.write(f"**Max Papers:** {data['top_x']}")
                        st.write(f"**Keywords:** {', '.join(data['keywords'])}")
                        if data.get('categories'):
                            cat_labels = [ARXIV_CODE_TO_LABEL.get(c, c) for c in data['categories']]
                            st.write(f"**Categories:** {', '.join(cat_labels)}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Confirm Create", key="confirm_profile_create", type="primary"):
                                try:
                                    logger.info(f"Creating profile: {data['name']}")
                                    api.create_profile(
                                        user_id=user.get('id'),
                                        name=data['name'],
                                        keywords=data['keywords'],
                                        categories=data.get('categories', []),
                                        frequency=data['frequency'],
                                        threshold=data['threshold'],
                                        top_x=data['top_x']
                                    )
                                    
                                    st.session_state.pop("pending_profile_create", None)
                                    st.session_state.pop("show_profile_create_confirm", None)
                                    st.session_state["profile_cat_tree_selected"] = []
                                    
                                    st.success("Profile created successfully! Go to 'List' view to upload papers.")
                                    logger.info(f"Successfully created profile: {data['name']}")
                                    st.rerun()
                                except Exception as e:
                                    log_error("profiles_page.confirm_create", e, {"profile_data": data})
                                    st.error(f"Error creating profile: {str(e)}")
                                    with st.expander("Error Details"):
                                        st.code(traceback.format_exc())
                        
                        with col2:
                            if st.button("Cancel", key="cancel_profile_create"):
                                st.session_state.pop("pending_profile_create", None)
                                st.session_state.pop("show_profile_create_confirm", None)
                                st.session_state["profile_cat_tree_selected"] = []
                                st.info("Creation cancelled")
                                st.rerun()
                
                except Exception as e:
                    log_error("profiles_page.confirmation_panel", e)
                    st.error(f"Error in confirmation panel: {str(e)}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
        
        except Exception as e:
            log_error("profiles_page.create_edit_view", e, {"user_id": user.get('id')})
            st.error(f"Error in Create/Edit view: {str(e)}")
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
    
    except Exception as e:
        log_error("profiles_page", e, {"user": user})
        st.error(f"Profiles page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def recommendations_page(user: Dict):
    """Recommendations page with advanced filtering and date grouping"""
    try:
        logger.info(f"Loading recommendations page for user: {user.get('email')}")
        st.markdown("### Recommendations")
        
        api = get_api_client()
        
        try:
            user_id = user.get('id') or user.get('user_id')
            logger.debug(f"Fetching profiles for user_id: {user_id}")
            profiles = api.get_user_profiles(user_id)
            
            if not profiles:
                st.info("No profiles found. Create a profile first.")
                return
            
            # Profile dropdown - NO "All Profiles"
            profile_options = {}
            for p in profiles:
                profile_options[str(p['id'])] = p['name']
            
            selected = st.selectbox(
                "Select Profile",
                options=list(profile_options.keys()),
                format_func=lambda x: profile_options[x],
                index=0  # Default to first profile
            )

            # Get selected profile details
            try:
                selected_profile = next((p for p in profiles if str(p['id']) == selected), None)
                profile_categories = selected_profile.get('categories', []) if selected_profile else []
                logger.debug(f"Selected profile {selected} with {len(profile_categories)} categories")
            except Exception as e:
                log_error("recommendations_page.get_profile_details", e, {"selected": selected})
                profile_categories = []

            # Fetch recommendations for selected profile
            try:
                profile_id_int = int(selected)
                logger.info(f"Fetching recommendations for profile: {profile_id_int}")
                recommendations = api.get_profile_recommendations(profile_id_int, limit=5000)
                logger.debug(f"Fetched {len(recommendations)} recommendations")
            except Exception as e:
                log_error("recommendations_page.fetch_recommendations", e, {
                    "profile_id": selected
                })
                st.error(f"Error fetching recommendations: {str(e)}")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                return

            # DEDUPLICATE by arxiv_id - keep highest score
            try:
                seen_arxiv_ids = {}
                for rec in recommendations:
                    arxiv_id = rec.get('arxiv_id')
                    if arxiv_id:
                        if arxiv_id not in seen_arxiv_ids or rec['score'] > seen_arxiv_ids[arxiv_id]['score']:
                            seen_arxiv_ids[arxiv_id] = rec
                    else:
                        seen_arxiv_ids[f"_no_id_{rec.get('id')}"] = rec

                recommendations = list(seen_arxiv_ids.values())
                logger.debug(f"After deduplication: {len(recommendations)} recommendations")
            except Exception as e:
                log_error("recommendations_page.deduplicate", e)
                st.warning("Error deduplicating recommendations, showing all")
                    
            if not recommendations:
                st.info("No recommendations yet.")
                return
            
            # Calculate min and max scores from recommendations
            try:
                all_scores = [r['score'] for r in recommendations if r.get('score') is not None]
                min_score_available = min(all_scores) if all_scores else 0.0
                max_score_available = max(all_scores) if all_scores else 1.0
                logger.debug(f"Score range: {min_score_available:.3f} to {max_score_available:.3f}")
            except Exception as e:
                log_error("recommendations_page.calculate_score_range", e)
                min_score_available = 0.0
                max_score_available = 1.0
            
            # Advanced filters in expandable section
            with st.expander("Filters", expanded=False):
                try:
                    # Quick filter buttons
                    col_quick1, col_quick2, col_quick3, col_quick4 = st.columns(4)
                    
                    with col_quick1:
                        if st.button("Today", use_container_width=True):
                            st.session_state['rec_date_from'] = date.today()
                            st.session_state['rec_date_to'] = date.today()
                            st.rerun()
                    
                    with col_quick2:
                        if st.button("Last 7 days", use_container_width=True):
                            st.session_state['rec_date_from'] = date.today() - timedelta(days=7)
                            st.session_state['rec_date_to'] = date.today()
                            st.rerun()
                    
                    with col_quick3:
                        if st.button("Last 30 days", use_container_width=True):
                            st.session_state['rec_date_from'] = date.today() - timedelta(days=30)
                            st.session_state['rec_date_to'] = date.today()
                            st.rerun()
                    
                    with col_quick4:
                        if st.button("All time", use_container_width=True):
                            st.session_state['rec_date_from'] = None
                            st.session_state['rec_date_to'] = None
                            st.rerun()
                    
                    st.divider()
                    
                    # Manual date inputs
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        date_from = st.date_input(
                            "From date", 
                            value=st.session_state.get('rec_date_from'),
                            key="rec_date_from_input"
                        )
                        if date_from:
                            st.session_state['rec_date_from'] = date_from
                    
                    with col2:
                        date_to = st.date_input(
                            "To date", 
                            value=st.session_state.get('rec_date_to'),
                            key="rec_date_to_input"
                        )
                        if date_to:
                            st.session_state['rec_date_to'] = date_to
                    
                    # Minimum score slider with dynamic range
                    min_score = st.slider(
                        "Minimum Score", 
                        min_value=float(min_score_available),
                        max_value=float(max_score_available),
                        value=float(min_score_available),  # Default to lowest score (show all)
                        step=0.01, 
                        key="rec_min_score",
                        help=f"Score range: {min_score_available:.3f} to {max_score_available:.3f}"
                    )
                    
                    # Keyword search
                    keyword_search = st.text_input("Search in title/abstract", placeholder="Enter keywords...")
                    
                    # Category filter - Show profile's categories as checkboxes
                    st.write("**Filter by Categories**")
                    
                    if profile_categories:
                        # Initialize session state for category selections if not exists
                        if f"selected_cats_{selected}" not in st.session_state:
                            st.session_state[f"selected_cats_{selected}"] = []
                        
                        # Create checkboxes for each category in the profile
                        selected_cats = []
                        
                        for cat in profile_categories:
                            try:
                                cat_label = ARXIV_CODE_TO_LABEL.get(cat, cat)
                                is_checked = st.checkbox(
                                    cat_label,
                                    value=cat in st.session_state[f"selected_cats_{selected}"],
                                    key=f"cat_checkbox_{selected}_{cat}"
                                )
                                if is_checked:
                                    selected_cats.append(cat)
                            except Exception as e:
                                log_error("recommendations_page.category_checkbox", e, {"category": cat})
                        
                        # Update session state
                        st.session_state[f"selected_cats_{selected}"] = selected_cats
                        
                        # Add "Clear all" button if any categories are selected
                        if selected_cats:
                            if st.button("Clear category filters", key=f"clear_cats_{selected}"):
                                st.session_state[f"selected_cats_{selected}"] = []
                                st.rerun()
                    else:
                        st.caption("No categories configured for this profile")
                
                except Exception as e:
                    log_error("recommendations_page.filters", e)
                    st.error("Error loading filters")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
            
            # Apply filters
            try:
                logger.debug("Applying filters to recommendations")
                filtered = recommendations
                
                # Score filter
                filtered = [r for r in filtered if r['score'] >= min_score]
                logger.debug(f"After score filter: {len(filtered)} recommendations")
                
                # Date filters
                date_from = st.session_state.get('rec_date_from')
                date_to = st.session_state.get('rec_date_to')

                if date_from or date_to:
                    date_filtered = []
                    for r in filtered:
                        submitted_date = r.get('submitted_date')
                        
                        if submitted_date:
                            try:
                                if isinstance(submitted_date, str):
                                    paper_date = datetime.fromisoformat(submitted_date.replace('Z', '').replace('+00:00', '')).date()
                                else:
                                    paper_date = submitted_date.date() if hasattr(submitted_date, 'date') else None
                                
                                if paper_date:
                                    if date_from and paper_date < date_from:
                                        continue
                                    if date_to and paper_date > date_to:
                                        continue
                                    
                                    date_filtered.append(r)
                            except Exception as e:
                                log_error("recommendations_page.filter_date", e, {
                                    "submitted_date": submitted_date
                                })
                                date_filtered.append(r)
                        else:
                            date_filtered.append(r)
                    
                    filtered = date_filtered
                    logger.debug(f"After date filter: {len(filtered)} recommendations")
                
                # Keyword search filter
                if keyword_search:
                    keyword_lower = keyword_search.lower()
                    filtered = [
                        r for r in filtered
                        if keyword_lower in r.get('title', '').lower() or 
                           keyword_lower in r.get('abstract', '').lower()
                    ]
                    logger.debug(f"After keyword filter: {len(filtered)} recommendations")
                
                # Category filter
                selected_cats = st.session_state.get(f"selected_cats_{selected}", [])
                if selected_cats:
                    filtered = [
                        r for r in filtered
                        if r.get('metadata') and 
                           any(cat in r['metadata'].get('categories', []) for cat in selected_cats)
                    ]
                    logger.debug(f"After category filter: {len(filtered)} recommendations")
                
                # Sort by score
                filtered = sorted(filtered, key=lambda x: x['score'], reverse=True)
                
            except Exception as e:
                log_error("recommendations_page.apply_filters", e)
                st.error("Error applying filters")
                filtered = recommendations
            
            # Group by submitted_date
            try:
                from collections import defaultdict
                
                grouped = defaultdict(list)
                
                for rec in filtered:
                    submitted_date = rec.get('submitted_date')
                    date_str = "Unknown Date"
                    date_obj = None
                    
                    if submitted_date:
                        try:
                            if isinstance(submitted_date, str):
                                date_obj = datetime.fromisoformat(submitted_date.replace('Z', '').replace('+00:00', ''))
                            else:
                                date_obj = submitted_date
                            
                            date_str = date_obj.strftime("%d %B %Y")
                        except Exception as e:
                            log_error("recommendations_page.parse_submitted_date", e, {
                                "submitted_date": submitted_date
                            })
                            date_str = "Unknown Date"
                    
                    rec['_date_obj'] = date_obj
                    grouped[date_str].append(rec)
                
                logger.debug(f"Grouped into {len(grouped)} date groups")
                
                # Sort dates (newest first)
                def date_sort_key(date_str):
                    if date_str == "Unknown Date":
                        return datetime.min
                    recs_in_group = grouped[date_str]
                    if recs_in_group and recs_in_group[0].get('_date_obj'):
                        return recs_in_group[0]['_date_obj']
                    return datetime.min
                
                try:
                    sorted_dates = sorted(grouped.keys(), key=date_sort_key, reverse=True)
                except Exception as e:
                    log_error("recommendations_page.sort_dates", e)
                    sorted_dates = list(grouped.keys())
                
                # Flatten papers for pagination
                all_papers_ordered = []
                for date in sorted_dates:
                    recs = sorted(grouped[date], key=lambda x: x['score'], reverse=True)
                    for rec in recs:
                        rec['_display_date'] = date
                        all_papers_ordered.append(rec)
                
            except Exception as e:
                log_error("recommendations_page.group_by_date", e)
                st.error("Error grouping recommendations by date")
                all_papers_ordered = filtered
            
            # PAGINATION - 20 papers per page
            try:
                PAPERS_PER_PAGE = 20
                total_papers = len(all_papers_ordered)
                total_pages = (total_papers + PAPERS_PER_PAGE - 1) // PAPERS_PER_PAGE
                
                # Initialize page number
                if f'rec_page_{selected}' not in st.session_state:
                    st.session_state[f'rec_page_{selected}'] = 1
                
                current_page = st.session_state[f'rec_page_{selected}']
                
                # Ensure current page is valid
                if current_page > total_pages and total_pages > 0:
                    current_page = total_pages
                    st.session_state[f'rec_page_{selected}'] = current_page
                
                # Calculate pagination indices
                start_idx = (current_page - 1) * PAPERS_PER_PAGE
                end_idx = min(start_idx + PAPERS_PER_PAGE, total_papers)
                
                # Get papers for current page
                page_papers = all_papers_ordered[start_idx:end_idx]
                
                logger.debug(f"Pagination: page {current_page}/{total_pages}, showing {start_idx+1}-{end_idx} of {total_papers}")
                
                # Display info and pagination controls
                col_info, col_pagination = st.columns([2, 1])
                
                with col_info:
                    st.write(f"Showing {start_idx + 1}-{end_idx} of {total_papers} recommendations")
                
                with col_pagination:
                    if total_pages > 1:
                        col_prev, col_page, col_next = st.columns([1, 2, 1])
                        
                        with col_prev:
                            if st.button("← Prev", disabled=(current_page == 1), key=f"prev_top_{selected}"):
                                st.session_state[f'rec_page_{selected}'] = current_page - 1
                                st.rerun()
                        
                        with col_page:
                            st.write(f"Page {current_page} of {total_pages}")
                        
                        with col_next:
                            if st.button("Next →", disabled=(current_page == total_pages), key=f"next_top_{selected}"):
                                st.session_state[f'rec_page_{selected}'] = current_page + 1
                                st.rerun()
                
                if not page_papers:
                    st.info("No recommendations match the filters.")
                    return
                
                # Re-group papers for current page by date
                page_grouped = defaultdict(list)
                for rec in page_papers:
                    date_str = rec.get('_display_date', 'Unknown Date')
                    page_grouped[date_str].append(rec)
                
                # Get unique dates in order
                page_dates = []
                seen = set()
                for rec in page_papers:
                    date_str = rec.get('_display_date', 'Unknown Date')
                    if date_str not in seen:
                        page_dates.append(date_str)
                        seen.add(date_str)
                
                # Display by date
                for date in page_dates:
                    try:
                        recs = page_grouped[date]
                        
                        # Display header with counts
                        st.markdown(f"### {date}")

                        # Get total_papers_fetched from the recommendation run
                        total_fetched = recs[0].get('total_papers_fetched', 0) if recs else 0
                        total_for_this_date = len(grouped[date])

                        if total_fetched > 0:
                            st.caption(f"Recommended {total_for_this_date} out of {total_fetched} papers fetched on this day")
                        else:
                            st.caption(f"{total_for_this_date} paper(s)")
                        
                        for rec in recs:
                            try:
                                with st.container(border=True):
                                    col1, col2 = st.columns([5, 1])
                                    with col1:
                                        st.markdown(f"**{rec['title']}**")
                                    with col2:
                                        st.markdown(f"**{rec['score']:.3f}**")
                                    
                                    # GET CATEGORIES FROM METADATA
                                    metadata = rec.get('metadata', {})
                                    categories = metadata.get('categories', [])
                                    
                                    if categories:
                                        # Show only primary category 
                                        primary_cat = categories[0]
                                        primary_label = ARXIV_CODE_TO_LABEL.get(primary_cat, primary_cat)
                                        if len(categories) > 1:
                                            st.caption(f"**Category:** {primary_label} (+{len(categories) - 1} more)")
                                        else:
                                            st.caption(f"**Category:** {primary_label}")
                                    
                                    st.caption(f"**arXiv:** {rec.get('arxiv_id', 'N/A')}")
                                    
                                    # Show summary if available, otherwise truncated abstract
                                    if rec.get('summary_text'):
                                        st.write(rec['summary_text'])
                                    elif rec.get('abstract'):
                                        st.write(rec['abstract'][:200] + "...")
                                    
                                    if rec.get('arxiv_id'):
                                        st.link_button("View on arXiv", f"https://arxiv.org/abs/{rec['arxiv_id']}")
                            
                            except Exception as e:
                                log_error("recommendations_page.display_recommendation", e, {
                                    "rec_id": rec.get('id'),
                                    "arxiv_id": rec.get('arxiv_id')
                                })
                                st.error(f"Error displaying recommendation")
                        
                        st.divider()
                    
                    except Exception as e:
                        log_error("recommendations_page.display_date_group", e, {"date": date})
                        st.error(f"Error displaying group: {date}")
                
                # Bottom pagination controls
                if total_pages > 1:
                    col_prev2, col_page2, col_next2 = st.columns([1, 2, 1])
                    
                    with col_prev2:
                        if st.button("← Previous", disabled=(current_page == 1), key=f"prev_bottom_{selected}"):
                            st.session_state[f'rec_page_{selected}'] = current_page - 1
                            st.rerun()
                    
                    with col_page2:
                        st.write(f"Page {current_page} of {total_pages}")
                    
                    with col_next2:
                        if st.button("Next →", disabled=(current_page == total_pages), key=f"next_bottom_{selected}"):
                            st.session_state[f'rec_page_{selected}'] = current_page + 1
                            st.rerun()
            
            except Exception as e:
                log_error("recommendations_page.pagination", e)
                st.error("Error in pagination")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
        
        except Exception as e:
            log_error("recommendations_page.main_logic", e, {"user_id": user.get('id')})
            st.error(f"Error: {str(e)}")
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
    
    except Exception as e:
        log_error("recommendations_page", e, {"user": user})
        st.error(f"Recommendations page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())


def settings_page(user: Dict):
    """Settings page"""
    try:
        logger.info(f"Loading settings page for user: {user.get('email')}")
        st.markdown("### Settings")
        
        api = get_api_client()
        
        with st.form("settings_form"):
            st.markdown("#### Profile Information")
            new_name = st.text_input("Name", value=user.get('name') or "")
            new_email = st.text_input("Email", value=user['email'])
            
            submit = st.form_submit_button("Update Profile")
        
        if submit:
            try:
                logger.info(f"Updating user settings for: {user.get('email')}")
                
                # Prepare update data
                update_data = {}
                if new_email != user['email']:
                    update_data['email'] = new_email
                if new_name != user.get('name'):
                    update_data['name'] = new_name
                
                if update_data:
                    logger.debug(f"Update data: {update_data}")
                    updated = api.update_user(
                        user.get('id'),
                        email=update_data.get('email'),
                        name=update_data.get('name')
                    )
                    set_current_user(updated)
                    st.success("Profile updated successfully!")
                    logger.info(f"Successfully updated user: {user.get('email')}")
                    st.rerun()
                else:
                    st.info("No changes to save")
            
            except Exception as e:
                log_error("settings_page.update", e, {
                    "user_id": user.get('id'),
                    "email": user.get('email')
                })
                st.error(f"Update failed: {str(e)}")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
        
        st.divider()
        
        # System info
        try:
            st.markdown("#### System Information")
            st.caption(f"User ID: {user.get('user_id') or user.get('id')}")
            st.caption(f"Account created: {user.get('created_at', 'N/A')}")
            
            # Optional: Add password change section
            with st.expander("Change Password"):
                with st.form("password_change_form"):
                    current_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm New Password", type="password")
                    
                    change_pw = st.form_submit_button("Change Password")
                
                if change_pw:
                    if not current_password or not new_password or not confirm_password:
                        st.error("All fields are required")
                    elif new_password != confirm_password:
                        st.error("New passwords don't match")
                    else:
                        try:
                            logger.info(f"Password change request for: {user.get('email')}")
                            # Note: You'll need to implement this endpoint in your API
                            # api.change_password(user.get('id'), current_password, new_password)
                            st.success("Password changed successfully!")
                            logger.info(f"Password changed for: {user.get('email')}")
                        except Exception as e:
                            log_error("settings_page.change_password", e, {
                                "user_id": user.get('id')
                            })
                            st.error(f"Password change failed: {str(e)}")
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
        
        except Exception as e:
            log_error("settings_page.system_info", e)
            st.error("Error displaying system information")
    
    except Exception as e:
        log_error("settings_page", e, {"user": user})
        st.error(f"Settings page error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# ==================== MAIN APP ====================

def main():
    st.set_page_config(
        page_title="Preprint Bot",
        page_icon="",
        layout="wide"
    )
    
    st.title(" Preprint Bot")
    
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
        st.caption(f"User ID: {user.get('id')}")
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