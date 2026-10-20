from pydantic import BaseModel, EmailStr
from datetime import datetime
from decimal import Decimal
from .models import BillingInterval, PlanStatus
from .models import SubscriptionStatus
from .models import CycleStatus
from .models import InvoiceStatus, LineItemType
from .models import PaymentStatus
from .models import RetryOutcome

# ---- Customer ----
class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    billing_country: str | None = None

class CustomerOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    billing_country: str | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Plan ----
class PlanCreate(BaseModel):
    name: str
    price: Decimal
    billing_interval: BillingInterval
    trial_period_days: int = 0

class PlanOut(BaseModel):
    id: int
    name: str
    price: Decimal
    billing_interval: BillingInterval
    trial_period_days: int
    status: PlanStatus
    created_at: datetime

    class Config:
        from_attributes = True

class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    trial_days: int = 0

class SubscriptionOut(BaseModel):
    id: int
    customer_id: int
    plan_id: int
    status: SubscriptionStatus
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    created_at: datetime
    customer_name: str | None = None
    plan_name: str | None = None

    class Config:
        from_attributes = True
    
class BillingCycleOut(BaseModel):
    id: int
    subscription_id: int
    cycle_start: datetime
    cycle_end: datetime
    status: CycleStatus
    created_at: datetime

    class Config:
        from_attributes = True

class InvoiceLineItemOut(BaseModel):
    id: int
    description: str
    item_type: LineItemType
    amount: Decimal

    class Config:
        from_attributes = True

class InvoiceOut(BaseModel):
    id: int
    billing_cycle_id: int | None
    invoice_number: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    status: InvoiceStatus
    issued_at: datetime
    due_at: datetime | None
    line_items: list[InvoiceLineItemOut] = []

    class Config:
        from_attributes = True

class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    status: PaymentStatus
    gateway_reference: str | None
    attempted_at: datetime

    class Config:
        from_attributes = True

class PaymentRetryOut(BaseModel):
    id: int
    payment_id: int
    attempt_number: int
    scheduled_for: datetime
    outcome: RetryOutcome

    class Config:
        from_attributes = True
# ---- Cancel Subscription Request ----
class CancelSubscriptionRequest(BaseModel):
    immediate: bool = False

class ChangePlanRequest(BaseModel):
    new_plan_id: int

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class AuditLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    event: str
    created_at: datetime

    class Config:
        from_attributes = True
class TaxRateCreate(BaseModel):
    country: str
    rate_percent: Decimal

class TaxRateOut(BaseModel):
    id: int
    country: str
    rate_percent: Decimal

    class Config:
        from_attributes = True

class PaymentWebhookPayload(BaseModel):
    invoice_id: int
    gateway_reference: str
    status: str   # "succeeded" or "failed"

class MRRDataPoint(BaseModel):
    month: str
    total_revenue: Decimal

class RevenueByPlanDataPoint(BaseModel):
    plan_name: str
    total_revenue: Decimal

class ChurnDataPoint(BaseModel):
    month: str
    cancelled_count: int
    active_at_start: int
    churn_rate_percent: float

class TrialConversionOut(BaseModel):
    total_trials: int
    converted_to_active: int
    conversion_rate_percent: float