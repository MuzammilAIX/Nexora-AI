"""Email sending via Gmail SMTP (works without domain verification)."""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.config import settings


def send_verification_email(to_email: str, verify_link: str) -> None:
    """Send the verification email via Gmail SMTP. Raises RuntimeError on failure."""
    if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_USER or GMAIL_APP_PASSWORD missing in .env — cannot send email."
        )

    msg = EmailMessage()
    msg["Subject"] = "Verify your Nexora AI account"
    msg["From"] = formataddr((settings.MAIL_FROM_NAME, settings.GMAIL_USER))
    msg["To"] = to_email
    msg.set_content(
        f"Welcome to Nexora AI!\n\n"
        f"Click the link below to verify your email:\n\n"
        f"{verify_link}\n\n"
        f"This link expires in 24 hours. If you didn't sign up, ignore this email.\n"
    )
    msg.add_alternative(
        f"""<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
<h2>Welcome to Nexora AI</h2>
<p>Click below to verify your email:</p>
<p><a href="{verify_link}" style="display:inline-block;padding:12px 24px;
background:#1a1a1a;color:#d4af37;text-decoration:none;border-radius:6px">Verify Email</a></p>
<p style="color:#888;font-size:12px">Link expires in 24 hours. If you didn't sign up, ignore this email.</p>
</body></html>""",
        subtype="html",
    )

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as s:
            s.starttls(context=ctx)
            s.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError(
            "Gmail SMTP auth failed. Check GMAIL_APP_PASSWORD is the 16-char "
            f"App Password (not normal password), 2FA is on. Detail: {e}"
        )
    except Exception as e:
        raise RuntimeError(f"Gmail SMTP send failed: {e}")