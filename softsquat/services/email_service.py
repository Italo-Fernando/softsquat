from email_validator import validate_email
from pydantic import EmailStr

from softsquat.settings import Settings


def check_email(email: EmailStr) -> EmailStr:
    email_info = validate_email(
        email, check_deliverability=Settings().EMAIL_CHECK_DELIVERABILITY
    )
    return email_info.normalized
