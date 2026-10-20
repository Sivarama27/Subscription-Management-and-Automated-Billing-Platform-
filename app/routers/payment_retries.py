from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random
from .. import models, schemas
from ..database import get_db
from .. import auth
from .. import audit

router = APIRouter(prefix="/payment-retries", tags=["payment-retries"])

RETRY_SCHEDULE_DAYS = {1: 1, 2: 3, 3: 7}   # attempt_number -> days after previous attempt
MAX_ATTEMPTS = 3

@router.post("/process/{retry_id}", response_model=schemas.PaymentRetryOut)
def process_retry(retry_id: int, db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth.get_current_admin)):
    retry = db.query(models.PaymentRetry).filter(models.PaymentRetry.id == retry_id).first()
    if not retry:
        raise HTTPException(status_code=404, detail="Retry not found")

    if retry.outcome != models.RetryOutcome.pending:
        raise HTTPException(status_code=400, detail="Retry already processed")

    payment = retry.payment
    invoice = payment.invoice
    subscription = invoice.billing_cycle.subscription

    success = random.random() < 0.8 # 80% chance of success

    if success:
        retry.outcome = models.RetryOutcome.succeeded
        invoice.status = models.InvoiceStatus.paid
        subscription.status = models.SubscriptionStatus.active
        audit.log_event(db, entity_type="payment", entity_id=payment.id, event="payment.retry_succeeded")
    else:
        retry.outcome = models.RetryOutcome.failed

        if retry.attempt_number < MAX_ATTEMPTS:
            next_attempt = retry.attempt_number + 1
            days_ahead = RETRY_SCHEDULE_DAYS[next_attempt]
            next_retry = models.PaymentRetry(
                payment_id=payment.id,
                attempt_number=next_attempt,
                scheduled_for=datetime.now(timezone.utc) + timedelta(days=days_ahead),
            )
            db.add(next_retry)
        else:
            # all 3 attempts exhausted — cancel the subscription
            subscription.status = models.SubscriptionStatus.cancelled
            audit.log_event(db, entity_type="subscription", entity_id=subscription.id, event="subscription.cancelled_retries_exhausted")

    db.commit()
    db.refresh(retry)
    return retry

@router.get("/", response_model=list[schemas.PaymentRetryOut])
def list_retries(db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models.PaymentRetry).all()