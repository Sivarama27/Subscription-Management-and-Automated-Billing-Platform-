from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import uuid
from .. import models, schemas
from ..database import get_db
from datetime import datetime, timedelta, timezone
from .. import auth
from .. import audit
router = APIRouter(prefix="/payments", tags=["payments"])
@router.post("/charge/{invoice_id}", response_model=schemas.PaymentOut)
@router.post("/charge/{invoice_id}", response_model=schemas.PaymentOut)
def charge_invoice(invoice_id: int, db: Session = Depends(get_db),
                   current_admin: models.User = Depends(auth.get_current_admin)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == models.InvoiceStatus.paid:
        raise HTTPException(status_code=400, detail="Invoice already paid")

    gateway_ref = f"MOCK-{uuid.uuid4().hex[:10].upper()}"

    new_payment = models.Payment(
        invoice_id=invoice.id,
        amount=invoice.total,
        status=models.PaymentStatus.pending,   # <-- CHANGED: no longer decided immediately
        gateway_reference=gateway_ref,
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    audit.log_event(db, entity_type="payment", entity_id=new_payment.id, event="payment.initiated")
    db.commit()

    # In a REAL system, this is where you'd call the actual gateway's API.
    # Here, we simulate that the gateway will call our webhook back shortly.
    return new_payment

@router.get("/", response_model=list[schemas.PaymentOut])
def list_payments(db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models.Payment).all()

@router.get("/{payment_id}", response_model=schemas.PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.get_current_admin)):
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment