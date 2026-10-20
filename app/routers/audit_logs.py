from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

@router.get("/", response_model=list[schemas.AuditLogOut])
def list_audit_logs(db: Session = Depends(get_db),
                     current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).all()

@router.get("/{entity_type}/{entity_id}", response_model=list[schemas.AuditLogOut])
def get_entity_history(entity_type: str, entity_id: int, db: Session = Depends(get_db),
                        current_user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.entity_type == entity_type, models.AuditLog.entity_id == entity_id)
        .order_by(models.AuditLog.created_at.desc())
        .all()
    )