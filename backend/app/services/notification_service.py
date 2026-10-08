
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    organization_id: int | None,
    notification_type: str,
    title: str,
    message: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:

    notification = Notification(
        user_id=user_id,
        organization_id=organization_id,
        type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification

