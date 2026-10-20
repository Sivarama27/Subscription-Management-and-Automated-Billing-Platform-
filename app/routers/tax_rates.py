from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/tax-rates", tags=["tax-rates"])

@router.post("/", response_model=schemas.TaxRateOut)
def create_tax_rate(rate: schemas.TaxRateCreate, db: Session = Depends(get_db),
                     current_admin: models.User = Depends(auth.get_current_admin)):
    existing = db.query(models.TaxRate).filter(models.TaxRate.country == rate.country).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tax rate for this country already exists")

    new_rate = models.TaxRate(**rate.model_dump())
    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)
    return new_rate

@router.get("/", response_model=list[schemas.TaxRateOut])
def list_tax_rates(db: Session = Depends(get_db),
                    current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.TaxRate).all()