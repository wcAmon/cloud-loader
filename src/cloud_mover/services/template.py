"""Template service for sharing CLAUDE.md and AGENTS.md templates."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from cloud_mover.config import settings
from cloud_mover.models import Template
from cloud_mover.services.auth import generate_code

MAX_CODE_GENERATION_ATTEMPTS = 100


def create_template(
    session: Session,
    template_type: str,
    title: str,
    content: str,
    description: Optional[str] = None,
) -> Template:
    """Create a new template record with unique code."""
    # Generate unique code
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        code = generate_code()
        # Check both Template and Backup tables to avoid code collision
        existing = session.exec(select(Template).where(Template.code == code)).first()
        if not existing:
            break
    else:
        raise RuntimeError("Failed to generate unique code after max attempts")

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.template_expiry_days
    )

    template = Template(
        code=code,
        template_type=template_type,
        title=title,
        description=description,
        content=content,
        content_size=len(content.encode("utf-8")),
        expires_at=expires_at,
    )
    session.add(template)
    session.commit()
    session.refresh(template)

    return template


def get_template_by_code(session: Session, code: str) -> Optional[Template]:
    """Get template by code if not expired."""
    return session.exec(
        select(Template).where(
            Template.code == code,
            Template.expires_at > datetime.now(timezone.utc),
        )
    ).first()


def increment_download_count(session: Session, template: Template) -> None:
    """Increment the download count for a template."""
    template.download_count += 1
    session.add(template)
    session.commit()
