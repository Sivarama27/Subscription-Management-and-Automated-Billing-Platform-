from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from .. import models, schemas
from ..database import get_db
import uuid
from .. import auth
from ..import audit

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

@router.post("/", response_model=schemas.SubscriptionOut)
def create_subscription(sub: schemas.SubscriptionCreate, db: Session = Depends(get_db),
                         current_user: models.User = Depends(auth.get_current_user)):
    # ...unchanged body...
    customer = db.query(models.Customer).filter(models.Customer.id == sub.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    plan = db.query(models.Plan).filter(models.Plan.id == sub.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=sub.trial_days) if sub.trial_days > 0 else None
    period_days = 30 if plan.billing_interval == models.BillingInterval.monthly else 365

    new_sub = models.Subscription(
        customer_id=sub.customer_id,
        plan_id=sub.plan_id,
        status=models.SubscriptionStatus.trial if trial_end else models.SubscriptionStatus.active,
        trial_ends_at=trial_end,
        current_period_start=now,
        current_period_end=now + timedelta(days=period_days),
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub

@router.get("/", response_model=list[schemas.SubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db),
                        current_user: models.User = Depends(auth.get_current_user)):
    subs = db.query(models.Subscription).all()
    result = []
    for sub in subs:
        sub_out = schemas.SubscriptionOut.model_validate(sub)
        sub_out.customer_name = sub.customer.name
        sub_out.plan_name = sub.plan.name
        result.append(sub_out)
    return result

@router.get("/{sub_id}", response_model=schemas.SubscriptionOut)
def get_subscription(sub_id: int, db: Session = Depends(get_db),
                      current_user: models.User = Depends(auth.get_current_user)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub

# for cancellation, we can have two modes: immediate or at the end of the current period. If immediate, we will also calculate a refund for any unused days in the current billing cycle.
@router.post("/{subscription_id}/cancel", response_model=schemas.SubscriptionOut)
def cancel_subscription(subscription_id: int, payload: schemas.CancelSubscriptionRequest, db: Session = Depends(get_db),
                         current_user: models.User = Depends(auth.get_current_user)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if payload.immediate:
        # find the most recent billing cycle for this subscription
        latest_cycle = (
            db.query(models.BillingCycle)
            .filter(models.BillingCycle.subscription_id == sub.id)
            .order_by(models.BillingCycle.cycle_start.desc())
            .first()
        )

        if latest_cycle:
            invoice = (
                db.query(models.Invoice)
                .filter(
                    models.Invoice.billing_cycle_id == latest_cycle.id,
                    models.Invoice.status == models.InvoiceStatus.paid,
                )
                .first()
            )

            if invoice:
                now = datetime.now(timezone.utc)
                total_days = (latest_cycle.cycle_end - latest_cycle.cycle_start).days or 1
                unused_days = max((latest_cycle.cycle_end - now).days, 0)
                refund_amount = (invoice.total * unused_days) / total_days

                if refund_amount > 0:
                    refund_line = models.InvoiceLineItem(
                        invoice_id=invoice.id,
                        description=f"Refund for {unused_days} unused day(s)",
                        item_type=models.LineItemType.refund,
                        amount=-refund_amount,   # negative = credit back to customer
                    )
                    db.add(refund_line)

                    refund_payment = models.Payment(
                        invoice_id=invoice.id,
                        amount=refund_amount,
                        status=models.PaymentStatus.refunded,
                        gateway_reference=f"REFUND-{uuid.uuid4().hex[:10].upper()}",
                    )
                    db.add(refund_payment)

        sub.status = models.SubscriptionStatus.cancelled
        sub.cancel_at_period_end = False
        audit.log_event(db, entity_type="subscription", entity_id=sub.id, event="subscription.cancelled_immediately")
    else:
        # cancel at end of period instead — no refund, stays active until period ends
        sub.cancel_at_period_end = True
        audit.log_event(db, entity_type="subscription", entity_id=sub.id, event="subscription.cancel_scheduled")
    db.commit()
    db.refresh(sub)
    return sub

@router.post("/{subscription_id}/change-plan", response_model=schemas.InvoiceOut)
def change_plan(subscription_id: int, payload: schemas.ChangePlanRequest, db: Session = Depends(get_db),
                 current_user: models.User = Depends(auth.get_current_user)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    new_plan = db.query(models.Plan).filter(models.Plan.id == payload.new_plan_id).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="New plan not found")

    old_plan = sub.plan
    now = datetime.now(timezone.utc)
    total_days = (sub.current_period_end - sub.current_period_start).days or 1
    unused_days = max((sub.current_period_end - now).days, 0)

    old_daily_rate = old_plan.price / total_days
    new_daily_rate = new_plan.price / total_days

    credit_amount = old_daily_rate * unused_days   # unused value on old plan
    debit_amount = new_daily_rate * unused_days     # cost of remaining days on new plan
    net_charge = debit_amount - credit_amount

    # create a fresh invoice just for this proration event
    invoice_number = f"INV-PRORATE-{uuid.uuid4().hex[:8].upper()}"
    new_invoice = models.Invoice(
        billing_cycle_id=None,   # not tied to a normal cycle — it's a one-off adjustment
        invoice_number=invoice_number,
        status=models.InvoiceStatus.open,
        due_at=now + timedelta(days=7),
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    credit_line = models.InvoiceLineItem(
        invoice_id=new_invoice.id,
        description=f"Credit for {unused_days} unused day(s) on {old_plan.name}",
        item_type=models.LineItemType.proration_credit,
        amount=-credit_amount,
    )
    debit_line = models.InvoiceLineItem(
        invoice_id=new_invoice.id,
        description=f"Charge for {unused_days} remaining day(s) on {new_plan.name}",
        item_type=models.LineItemType.proration_debit,
        amount=debit_amount,
    )
    db.add(credit_line)
    db.add(debit_line)

    new_invoice.subtotal = net_charge
    new_invoice.total = net_charge

    # switch the subscription to the new plan, same period
    sub.plan_id = new_plan.id
    audit.log_event(db, entity_type="subscription", entity_id=sub.id, event="subscription.plan_changed")
    db.commit()
    db.refresh(new_invoice)
    return new_invoice