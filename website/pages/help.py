# pages/help.py
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Help Page", page_icon="?", layout="wide")

# Hide side bar
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

st.title("Help & Documentation")
st.caption("A guide to using Preprint Bot to track arXiv research.")

# Getting Started 
st.header("Getting Started")

st.markdown("""
**1. Sign in or Create an Account**\n
Use your email and password to sign in. If you are new, click **"Create Account"** on the login screen.  
*Forgot your password?* Use the "Forgot password?" link to request a reset token via email.

**2. Create a Profile**\n
To start receiving recommendations, you need to tell the bot what you are interested in:
1.  Navigate to the **Profiles** tab.
2.  Click **"Create new"**.
3.  Fill out the profile details (see the "Profiles" section below for definitions).
4.  Select the specific **arXiv categories** (e.g., *cs.AI*, *stat.ML*) you want to track.
5.  Click **Create Profile**.

**3. Wait for Recommendations**\n
Once your profile is active, the bot will begin scanning new arXiv submissions that match your criteria. Check the **Dashboard** or **Recommendations** tab to see your personalized paper feed.
""")

st.divider()

# Tab Descriptions
st.header("What each tab does")

with st.expander("Dashboard", expanded=True):
    st.write("""
    The Dashboard is your home base. It provides a quick overview of your account activity:
    * **Stats:** Shows how many profiles you manage and the size of your paper corpus.
    * **Today's Top Picks:** Automatically displays the highest-scoring papers from *today's* arXiv dump across all your profiles.
    """)

with st.expander("Profiles (Configuration)", expanded=True):
    st.markdown("""This is where you manage your research interests. When creating or editing a profile, you will see the following settings:""")
    st.markdown("""
    <ul style="line-height: 2;">
        <li><b>Frequency:</b> Controls how often you receive email notifications about new papers found for this profile (e.g., <i>Daily vs Weekly</i>).</li>
        <li><b>Threshold:</b> Determines how strict the matching algorithm is.
            <ul style="margin-top: 0; margin-bottom: 0;">
                <li><b>High (0.75):</b> Only recommends papers that are a very strong match.</li>
                <li><b>Medium (0.6):</b> Balanced (Recommended).</li>
                <li><b>Low (0.5):</b> Shows a broader range of papers, but may include some less relevant results.</li>
            </ul>
        </li>
        <li><b>Max Papers:</b> The maximum number of recommendations to generate and email per run. Setting this to 10 or 20 prevents your inbox from being flooded on busy days.</li>
        <li><b>Categories:</b> The specific sub-fields of arXiv to scan. You must select at least one (e.g., <i>Computer Science > Artificial Intelligence</i>).</li>
        <li><b>Paper Uploads:</b> You can upload your own PDF papers or add specific arXiv IDs to a profile. The bot uses these to learn your specific taste and improve future recommendations.</li>
    </ul>
    """, unsafe_allow_html=True)

with st.expander("Recommendations (Search & Filter)", expanded=True):
    st.write("""
    This tab allows you to browse your entire history of recommended papers.
    * **Filter by Profile:** Switch between your different research interests.
    * **Date Range:** Look back at papers from last week, last month, or a custom range.
    * **Minimum Score:** Use the slider to hide papers that the bot wasn't confident about.
    * **Category Filter:** Narrow down the list to specific sub-categories (e.g., only show me *cs.LG* papers).
    """)

with st.expander("Settings", expanded=True):
    st.write("""
    Manage your global account preferences here.
    * **Update Profile:** Change your display name or email address.
    * **System Info:** View your unique User ID and account creation date.
    """)

st.divider()

st.header("Troubleshooting")

with st.expander("I’m not seeing any recommendations", expanded=True):
    st.markdown("""
    If your dashboard is empty, check the following:
    
    1.  **Is your profile new?** The bot runs periodically. If you just created a profile, wait for the next scheduled run (usually nightly) or check back in 24 hours.
    
    2.  **Are your settings too strict?** * **Threshold:** If set to "High", try lowering it to "Medium" or "Low".
        * **Categories:** Ensure you have selected categories that actually receive frequent submissions (e.g., *cs.CL* is very active, while *cs.OS* is slower).
    
    3.  **Is the Corpus populated?** Ensure the backend system is running and has successfully fetched the latest arXiv data.
    """)

st.divider()

st.header("Contact")

# Using os.getenv defaults email to a placeholder if none set
contact_email = os.environ.get("SYSTEM_USER_EMAIL", "support@example.com")

st.write(
    f"If something looks wrong (missing papers, odd scores, system errors), please email **{contact_email}** with details."
)