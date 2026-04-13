import smtplib
import re
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM_ADDRESS, EMAIL_FROM_NAME

DASHBOARD_URL = "https://preprint-bot.syr.edu/"
SU_ORANGE = "#F76900"
SU_NAVY = "#002147"


def truncate_to_sentences(text: str, n: int = 3) -> tuple[str, bool]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= n:
        return text.strip(), False
    return ' '.join(sentences[:n]), True


def build_digest_html(profile_name: str, papers: List[Dict], run_date: str) -> str:
    rows = ""
    papers = papers[:10]
    for i, paper in enumerate(papers, 1):
        arxiv_id = paper.get("arxiv_id", "")
        title = paper.get("title", "No title")
        score = paper.get("score", 0)
        summary = paper.get("summary_text") or paper.get("summary") or paper.get("abstract", "")
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "#"

        truncated_summary, was_truncated = truncate_to_sentences(summary, 3)
        read_more = f' <a href="{DASHBOARD_URL}" style="color:{SU_ORANGE};font-size:12px;text-decoration:none;">Read more →</a>' if was_truncated else ''

        rows += f"""
        <tr>
            <td style="padding:12px;border-bottom:1px solid #eee;vertical-align:top;width:30px;color:#888;">{i}</td>
            <td style="padding:12px;border-bottom:1px solid #eee;vertical-align:top;">
                <a href="{arxiv_url}" style="font-size:15px;font-weight:bold;color:{SU_NAVY};text-decoration:none;">{title}</a>
                <br>
                <span style="font-size:12px;color:#888;">Score: {score:.3f}</span>
                <p style="margin:8px 0 0;font-size:13px;color:#444;">{truncated_summary}{read_more}</p>
            </td>
        </tr>
        """

    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f9f9f9;margin:0;padding:0;">
    <div style="max-width:700px;margin:30px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="background:{SU_NAVY};padding:24px 32px;">
            <h1 style="margin:0;font-size:22px;"><a href="{DASHBOARD_URL}" style="color:{SU_ORANGE};text-decoration:none;">Preprint Bot</a></h1>
            <p style="color:#cce0ff;margin:4px 0 0;font-size:14px;">Daily Recommendations &mdash; {run_date}</p>
        </div>
        <div style="padding:24px 32px;">
            <p style="font-size:15px;color:#333;">Here are your top recommendations for profile <strong>{profile_name}</strong>:</p>
            <table style="width:100%;border-collapse:collapse;">
                {rows}
            </table>
            <div style="text-align:center;margin-top:24px;">
                <a href="{DASHBOARD_URL}" style="display:inline-block;padding:12px 28px;background:{SU_ORANGE};color:#fff;border-radius:6px;text-decoration:none;font-size:14px;font-weight:bold;">See all recommendations →</a>
            </div>
        </div>
        <div style="padding:16px 32px;background:#f1f1f1;font-size:12px;color:#888;text-align:center;">
            You are receiving this because email notifications are enabled for this profile.
        </div>
    </div>
    </body></html>
    """


def send_email(to_address: str, subject: str, html_body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>"
        msg["To"] = to_address
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM_ADDRESS, to_address, msg.as_string())

        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def send_recommendations_digest(
    to_address: str,
    profile_name: str,
    papers: List[Dict],
    run_date: str,
) -> tuple[bool, str, str]:
    subject = f"Preprint Bot: Showing 10 out of {len(papers)} new recommendations for '{profile_name}' ({run_date})"
    html_body = build_digest_html(profile_name, papers, run_date)
    success = send_email(to_address, subject, html_body)
    return success, subject, html_body