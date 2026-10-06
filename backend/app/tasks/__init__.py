from app.celery_app import celery

@celery.task(name="send_notification")
def send_notification(user_id: int, title: str, message: str, type: str = "info"):
    """Background task to create a notification (and optionally send email)."""
    # Import inside task to avoid circular imports
    from app.db.session import SessionLocal
    from app.models.notification import Notification

    db = SessionLocal()
    try:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
        )
        db.add(notif)
        db.commit()
        return {"status": "created", "id": notif.id}
    finally:
        db.close()


@celery.task(name="process_overdue_tasks")
def process_overdue_tasks():
    """Periodic task: mark/find overdue tasks and notify assignees."""
    # Placeholder – implement with date comparison against tasks.due_date
    return {"status": "ok"}
