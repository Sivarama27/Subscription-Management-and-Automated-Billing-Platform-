from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .. import auth
from .. import audit

router = APIRouter(prefix="/plans", tags=["plans"])
@router.post("/", response_model=schemas.PlanOut)
def create_plan(plan: schemas.PlanCreate, db: Session = Depends(get_db),
                 current_admin: models.User = Depends(auth.get_current_admin)):
    new_plan = models.Plan(**plan.model_dump())
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    audit.log_event(db, entity_type="plan", entity_id=new_plan.id, event="plan.created")
    db.commit()   # <-- ADD THIS to actually save the audit entry
    return new_plan
@router.get("/", response_model=list[schemas.PlanOut])
def list_plans(db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Plan).all()

@router.get("/{plan_id}", response_model=schemas.PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db),
             current_user: models.User = Depends(auth.get_current_user)):
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan