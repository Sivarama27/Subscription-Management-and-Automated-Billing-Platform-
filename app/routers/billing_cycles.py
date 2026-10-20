from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .. import auth

router = APIRouter(prefix="/billing-cycles", tags=["billing-cycles"])

@router.post("/generate/{subscription_id}", response_model=schemas.BillingCycleOut)
def generate_cycle(subscription_id: int, db: Session = Depends(get_db),
                    current_user: models.User = Depends(auth.get_current_user)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    new_cycle = models.BillingCycle(
        subscription_id=sub.id,
        cycle_start=sub.current_period_start,
        cycle_end=sub.current_period_end,
        status=models.CycleStatus.pending,
    )
    db.add(new_cycle)
    db.commit()
    db.refresh(new_cycle)
    return new_cycle

@router.get("/", response_model=list[schemas.BillingCycleOut])
def list_cycles(db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.BillingCycle).all()

@router.get("/{cycle_id}", response_model=schemas.BillingCycleOut)
def get_cycle(cycle_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(auth.get_current_user)):
    cycle = db.query(models.BillingCycle).filter(models.BillingCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Billing cycle not found")
    return cycle