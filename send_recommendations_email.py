import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Config
RECIPIENT_EMAIL = "ggwpfax@gmail.com"
JSON_PATH = os.path.join("preprint-bot", "arxiv_pipeline_data", "ranked_matches.json")  # adjust if needed

def format_date(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except Exception:
        return iso_str

def build_email_html(papers):
    html = """
    <html>
    <head>
        <style>
            body {font-family: Arial, sans-serif; background: #f9f9f9; color: #333;}
            .container {max-width: 700px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
            h1 {color: #2c3e50;}
            .paper {border-bottom: 1px solid #eee; padding: 15px 0;}
            .title {font-size: 18px; color: #2980b9; margin-bottom: 5px;}
            .summary {font-size: 14px; color: #555; white-space: pre-line; margin-bottom: 8px;}
            .meta {font-size: 12px; color: #999;}
            a {color: #2980b9; text-decoration: none;}
            a:hover {text-decoration: underline;}
        </style>
    </head>
    <body>
    <div class="container">
        <h1>📚 Recommended Papers for You</h1>
    """

    for paper in papers:
        summary_clean = paper["summary"].strip().replace("\n", "<br>")
        published = format_date(paper.get("published", ""))
        html += f"""
        <div class="paper">
            <div class="title"><a href="{paper['url']}">{paper['title']}</a></div>
            <div class="summary">{summary_clean}</div>
            <div class="meta">
                Published: {published} | Similarity Score: {paper['score']:.2f}
            </div>
        </div>
        """

    html += """
    </div>
    </body>
    </html>
    """
    return html

def send_email(sender_email, sender_password):
    # Load recommended papers JSON
    if not os.path.exists(JSON_PATH):
        print(f"JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # Build email content
    html_content = build_email_html(papers)

    # Setup MIME
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Recommended arXiv Papers"
    msg["From"] = sender_email
    msg["To"] = RECIPIENT_EMAIL

    msg.attach(MIMEText(html_content, "html"))

    # Send email
    try:
        import ssl
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, RECIPIENT_EMAIL, msg.as_string())
        print(f"Email sent successfully to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    import getpass

    print("Enter your Gmail credentials to send email")
    sender = input("Sender Gmail address: ").strip()
    passwd = getpass.getpass("App password (not your Gmail password): ")

    send_email(sender, passwd)
