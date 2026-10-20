from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from .. import models, schemas, audit
from ..database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/payment-status")
def payment_status_webhook(payload: schemas.PaymentWebhookPayload, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == payload.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = (
        db.query(models.Payment)
        .filter(
            models.Payment.invoice_id == invoice.id,
            models.Payment.gateway_reference == payload.gateway_reference,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for this gateway reference")

    if payment.status != models.PaymentStatus.pending:
        raise HTTPException(status_code=400, detail="Payment already resolved")

    if payload.status == "succeeded":
        payment.status = models.PaymentStatus.succeeded
        invoice.status = models.InvoiceStatus.paid
        audit.log_event(db, entity_type="payment", entity_id=payment.id, event="payment.succeeded")
    elif payload.status == "failed":
        payment.status = models.PaymentStatus.failed
        subscription = invoice.billing_cycle.subscription
        subscription.status = models.SubscriptionStatus.past_due
        audit.log_event(db, entity_type="payment", entity_id=payment.id, event="payment.failed")

        first_retry = models.PaymentRetry(
            payment_id=payment.id,
            attempt_number=1,
            scheduled_for=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(first_retry)
    else:
        raise HTTPException(status_code=400, detail="Invalid status value")

    db.commit()
    return {"message": "Webhook processed", "payment_id": payment.id, "new_status": payment.status}