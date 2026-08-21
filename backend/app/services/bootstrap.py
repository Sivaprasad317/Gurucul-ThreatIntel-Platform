from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.models.user import User


def ensure_admin(session: Session) -> None:
    settings = get_settings()
    existing = session.scalar(select(User).where(User.email == settings.admin_email.lower()))
    if existing is None:
        session.add(User(email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password), is_active=True))
        session.commit()
