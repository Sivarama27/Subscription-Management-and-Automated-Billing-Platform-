from .celery_app import celery_app
from .database import SessionLocal
from . import models, audit
from datetime import datetime, timedelta, timezone
import uuid
import random


@celery_app.task
def generate_due_billing_cycles():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_subscriptions = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.status == models.SubscriptionStatus.active,
                models.Subscription.current_period_end <= now,
            )
            .all()
        )

        created_count = 0
        for sub in due_subscriptions:
            new_cycle = models.BillingCycle(
                subscription_id=sub.id,
                cycle_start=sub.current_period_start,
                cycle_end=sub.current_period_end,
                status=models.CycleStatus.pending,
            )
            db.add(new_cycle)
            created_count += 1

        db.commit()
        return f"Created {created_count} billing cycle(s)"
    finally:
        db.close()


@celery_app.task
def generate_invoices_from_pending_cycles():
    db = SessionLocal()
    try:
        pending_cycles = (
            db.query(models.BillingCycle)
            .filter(models.BillingCycle.status == models.CycleStatus.pending)
            .all()
        )

        created_count = 0
        for cycle in pending_cycles:
            subscription = cycle.subscription
            plan = subscription.plan
            customer = subscription.customer

            invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
            new_invoice = models.Invoice(
                billing_cycle_id=cycle.id,
                invoice_number=invoice_number,
                status=models.InvoiceStatus.draft,
                due_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            db.add(new_invoice)
            db.commit()
            db.refresh(new_invoice)

            plan_fee_item = models.InvoiceLineItem(
                invoice_id=new_invoice.id,
                description=f"{plan.name} - {plan.billing_interval.value} plan fee",
                item_type=models.LineItemType.plan_fee,
                amount=plan.price,
            )
            db.add(plan_fee_item)

            tax_amount = 0
            if customer.billing_country:
                tax_rate_record = (
                    db.query(models.TaxRate)
                    .filter(models.TaxRate.country == customer.billing_country)
                    .first()
                )
                if tax_rate_record and tax_rate_record.rate_percent > 0:
                    tax_amount = plan.price * (tax_rate_record.rate_percent / 100)
                    tax_item = models.InvoiceLineItem(
                        invoice_id=new_invoice.id,
                        description=f"Tax ({tax_rate_record.rate_percent}% - {customer.billing_country})",
                        item_type=models.LineItemType.tax,
                        amount=tax_amount,
                    )
                    db.add(tax_item)

            new_invoice.subtotal = plan.price
            new_invoice.tax_amount = tax_amount
            new_invoice.total = plan.price + tax_amount
            new_invoice.status = models.InvoiceStatus.open

            cycle.status = models.CycleStatus.invoiced
            created_count += 1

        db.commit()
        return f"Generated {created_count} invoice(s)"
    finally:
        db.close()


RETRY_SCHEDULE_DAYS = {1: 1, 2: 3, 3: 7}
MAX_ATTEMPTS = 3


@celery_app.task
def process_due_payment_retries():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_retries = (
            db.query(models.PaymentRetry)
            .filter(
                models.PaymentRetry.outcome == models.RetryOutcome.pending,
                models.PaymentRetry.scheduled_for <= now,
            )
            .all()
        )

        processed_count = 0
        for retry in due_retries:
            payment = retry.payment
            invoice = payment.invoice
            subscription = invoice.billing_cycle.subscription

            success = random.random() < 0.8

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
                    subscription.status = models.SubscriptionStatus.cancelled
                    audit.log_event(db, entity_type="subscription", entity_id=subscription.id, event="subscription.cancelled_retries_exhausted")

            processed_count += 1

        db.commit()
        return f"Processed {processed_count} retry(ies)"
    finally:
        db.close()