import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.email_service import send_email

success = send_email(
    to_address="udayanfg@gmail.com",
    subject="Preprint Bot — Test Email",
    html_body="<p>If you received this, your SMTP relay is configured correctly.</p>"
)

if success:
    print("Email sent successfully")
else:
    print("Email failed")