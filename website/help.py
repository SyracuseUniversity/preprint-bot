# pages/help.py
import streamlit as st

st.set_page_config(page_title="Help Page", page_icon="❓", layout="wide")

#hide side bar
st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            [data-testid="stSidebarCollapsedControl"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

st.title("Help Page")
st.caption("How to use Preprint Bot")

st.header("Getting Started")


st.write("1) Sign in")
st.caption(
    "Use your email and password. If you forgot your password, request a reset token and paste it into the reset form."
)

st.write("2) Pick what you care about")
st.caption(
    "Create a **Profile** with keywords + arXiv categories. Your recommendations will use these settings."
)

st.divider()

st.header("What each tab does")

with st.expander("Dashboard", expanded=True):
    st.write(
        "- Shows your profile count and corpus size.\n"
        "- Lists your latest recommendations."
    )

with st.expander("Profiles", expanded=True):
    st.write(
        "Profiles are how you define what you want to track.\n\n"
        "**Create a profile**\n"
        "1. Name your profile\n"
        "2. Choose frequency\n"
        "3. Set similarity threshold\n"
        "4. Add keywords (comma-separated)\n"
        "5. Select arXiv categories in the tree\n\n"
        "**Edit a profile**\n"
        "- Update keywords/categories anytime.\n"
        "- Add/remove papers tied to that profile."
    )

with st.expander("Recommendations", expanded=True):
    st.write(
        "Filter by date range, author, paper title, keyword text, and category.\n\n"
        "Tip: If you select categories, the list narrows fast. Clear category filters to see everything again."
    )

with st.expander("Settings", expanded=True):
    st.write(
        "Global settings apply across the app.\n\n"
        "- **Similarity (global)**: affects how strict matching is.\n"
        "- **Max papers per run**: how many papers are processed when generating recommendations."
    )

st.divider()

st.header("Examples")

st.subheader("Keyword examples")
st.code("llm, transformer, retrieval, rag, knowledge graph", language="text")
st.caption("Use commas. Keep keywords short. Avoid full sentences.")

st.subheader("Category examples")
st.write(
    "- **cs.AI** for AI\n"
    "- **cs.CL** for NLP\n"
    "- **cs.LG** for ML\n"
    "- **stat.ML** for statistical ML\n"
    "- **q-fin.TR** for trading / market microstructure"
)

st.caption("Full taxonomy: https://arxiv.org/category_taxonomy")

st.divider()

st.header("Troubleshooting")

with st.expander("I’m not seeing any recommendations"):
    st.write(
        "Common causes:\n"
        "- No profiles created yet\n"
        "- Similarity threshold is too high\n"
        "- Category filters are too restrictive\n"
        "- Corpus is empty or hasn’t been populated"
    )

with st.expander("My category tree selection isn’t saving"):
    st.write(
        "Make sure you hit **Create** / **Save** in the profile form after selecting categories."
    )

with st.expander("The app feels slow"):
    st.write(
        "Try reducing **Max papers per run** in Settings, or narrow categories/keywords."
    )

st.divider()

st.header("Contact")
st.write(
    "If something looks wrong (missing papers, odd scores, errors), please email preprintbot@syr.edu with details.\n"
)