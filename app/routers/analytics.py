from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/mrr", response_model=list[schemas.MRRDataPoint])
def get_mrr(db: Session = Depends(get_db),
            current_user: models.User = Depends(auth.get_current_user)):
    results = (
        db.query(
            func.to_char(models.Invoice.issued_at, "YYYY-MM").label("month"),
            func.sum(models.Invoice.total).label("total_revenue"),
        )
        .filter(models.Invoice.status == models.InvoiceStatus.paid)
        .group_by(func.to_char(models.Invoice.issued_at, "YYYY-MM"))
        .order_by(func.to_char(models.Invoice.issued_at, "YYYY-MM"))
        .all()
    )

    return [
        schemas.MRRDataPoint(month=row.month, total_revenue=row.total_revenue)
        for row in results
    ]

@router.get("/revenue-by-plan", response_model=list[schemas.RevenueByPlanDataPoint])
def get_revenue_by_plan(db: Session = Depends(get_db),
                         current_user: models.User = Depends(auth.get_current_user)):
    results = (
        db.query(
            models.Plan.name.label("plan_name"),
            func.sum(models.Invoice.total).label("total_revenue"),
        )
        .join(models.BillingCycle, models.Invoice.billing_cycle_id == models.BillingCycle.id)
        .join(models.Subscription, models.BillingCycle.subscription_id == models.Subscription.id)
        .join(models.Plan, models.Subscription.plan_id == models.Plan.id)
        .filter(models.Invoice.status == models.InvoiceStatus.paid)
        .group_by(models.Plan.name)
        .all()
    )

    return [
        schemas.RevenueByPlanDataPoint(plan_name=row.plan_name, total_revenue=row.total_revenue)
        for row in results
    ]

@router.get("/churn-rate", response_model=list[schemas.ChurnDataPoint])
def get_churn_rate(db: Session = Depends(get_db),
                    current_user: models.User = Depends(auth.get_current_user)):
    cancellation_events = (
        db.query(
            func.to_char(models.AuditLog.created_at, "YYYY-MM").label("month"),
            func.count(models.AuditLog.id).label("cancelled_count"),
        )
        .filter(
            models.AuditLog.entity_type == "subscription",
            models.AuditLog.event.in_(["subscription.cancelled_immediately", "subscription.cancelled_retries_exhausted"]),
        )
        .group_by(func.to_char(models.AuditLog.created_at, "YYYY-MM"))
        .order_by(func.to_char(models.AuditLog.created_at, "YYYY-MM"))
        .all()
    )

    total_subscriptions = db.query(models.Subscription).count()

    results = []
    for row in cancellation_events:
        churn_rate = (row.cancelled_count / total_subscriptions * 100) if total_subscriptions > 0 else 0
        results.append(schemas.ChurnDataPoint(
            month=row.month,
            cancelled_count=row.cancelled_count,
            active_at_start=total_subscriptions,
            churn_rate_percent=round(churn_rate, 2),
        ))

    return results

@router.get("/trial-conversion", response_model=schemas.TrialConversionOut)
def get_trial_conversion(db: Session = Depends(get_db),
                          current_user: models.User = Depends(auth.get_current_user)):
    total_trials = (
        db.query(models.Subscription)
        .filter(models.Subscription.trial_ends_at.isnot(None))
        .count()
    )

    converted = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.trial_ends_at.isnot(None),
            models.Subscription.status == models.SubscriptionStatus.active,
        )
        .count()
    )

    rate = (converted / total_trials * 100) if total_trials > 0 else 0

    return schemas.TrialConversionOut(
        total_trials=total_trials,
        converted_to_active=converted,
        conversion_rate_percent=round(rate, 2),
    )