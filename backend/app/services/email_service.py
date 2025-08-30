import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_magic_link_email(to_email: str, magic_link: str):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("[EmailService] Email configuration missing - EMAIL_SENDER or EMAIL_PASSWORD not set")
        return False

    subject = "Your FinVault Magic Login Link"
    body = f"Click the link to verify your account and log in: {magic_link}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[EmailService] Failed to send magic link: {e}")
        return False 