from sqlalchemy import Column, Integer, String, DateTime, Numeric, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    billing_country = Column(String, nullable=True)
    notes = Column(String, nullable=True)   # <-- NEW
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BillingInterval(str, enum.Enum):
    monthly = "monthly"
    annual = "annual"


class PlanStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    billing_interval = Column(Enum(BillingInterval), nullable=False)
    trial_period_days = Column(Integer, default=0)
    status = Column(Enum(PlanStatus), default=PlanStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# keep existing Customer, Plan, BillingInterval, PlanStatus above this

class SubscriptionStatus(str, enum.Enum):
    trial = "trial"
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.trial)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", backref="subscriptions")
    plan = relationship("Plan", backref="subscriptions")

class CycleStatus(str, enum.Enum):
    pending = "pending"
    invoiced = "invoiced"

class BillingCycle(Base):
    __tablename__ = "billing_cycles"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    cycle_start = Column(DateTime(timezone=True), nullable=False)
    cycle_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(CycleStatus), default=CycleStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", backref="billing_cycles")

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    paid = "paid"
    void = "void"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    billing_cycle_id = Column(Integer, ForeignKey("billing_cycles.id"), nullable=True)
    invoice_number = Column(String, unique=True, index=True)
    subtotal = Column(Numeric(10, 2), default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    due_at = Column(DateTime(timezone=True), nullable=True)

    billing_cycle = relationship("BillingCycle", backref="invoices")


class LineItemType(str, enum.Enum):
    plan_fee = "plan_fee"
    proration_credit = "proration_credit"
    proration_debit = "proration_debit"
    usage_charge = "usage_charge"
    tax = "tax"
    refund = "refund"

class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=False)
    item_type = Column(Enum(LineItemType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    invoice = relationship("Invoice", backref="line_items")

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    gateway_reference = Column(String, nullable=True)
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", backref="payments")

class RetryOutcome(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"

class PaymentRetry(Base):# in case we want to track retry attempts for failed payments
    __tablename__ = "payment_retries"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    outcome = Column(Enum(RetryOutcome), default=RetryOutcome.pending)

    payment = relationship("Payment", backref="retries")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)   # "subscription", "invoice", "payment"
    entity_id = Column(Integer, nullable=False)
    event = Column(String, nullable=False)          # "subscription.plan_changed", "payment.refunded"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TaxRate(Base):
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, unique=True, index=True, nullable=False)
    rate_percent = Column(Numeric(5, 2), nullable=False)   # e.g. 18.00 for 18%