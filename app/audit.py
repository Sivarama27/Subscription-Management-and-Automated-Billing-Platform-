from sqlalchemy.orm import Session
from . import models

def log_event(db: Session, entity_type: str, entity_id: int, event: str):
    entry = models.AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        event=event,
    )
    db.add(entry)