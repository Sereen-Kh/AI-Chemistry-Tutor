import resend

from app.core.config import settings


resend.api_key = settings.RESEND_API_KEY


def send_reset_email(
    email: str,
    reset_token: str
):

    reset_link = (
        f"http://127.0.0.1:8000/docs"
        f"?reset_token={reset_token}"
    )

    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": email,
        "subject": "Reset Your Password",
        "html": f"""
        <h2>Password Reset</h2>

        <p>
            Click the link below to reset
            your password:
        </p>

        <a href="{reset_link}">
            Reset Password
        </a>

        <br><br>

        <p>
            This link expires in 15 minutes.
        </p>
        """
    })