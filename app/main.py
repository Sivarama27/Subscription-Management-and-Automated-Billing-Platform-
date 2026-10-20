from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routers import customers, plans, subscriptions, billing_cycles, invoices, payments, payment_retries, auth, audit_logs, tax_rates, webhooks, analytics

app = FastAPI(title="Subscription Billing Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

app.include_router(customers.router)
app.include_router(plans.router)
app.include_router(subscriptions.router)
app.include_router(billing_cycles.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(payment_retries.router)
app.include_router(auth.router)
app.include_router(audit_logs.router)
app.include_router(tax_rates.router)
app.include_router(webhooks.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {"status": "running"}