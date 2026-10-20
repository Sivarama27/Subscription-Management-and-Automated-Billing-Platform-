from fastapi import APIRouter, Depends, HTTPException
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import uuid
from .. import models, schemas
from ..database import get_db
from .. import auth
from fastapi.responses import FileResponse
from ..pdf_generator import generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/generate/{billing_cycle_id}", response_model=schemas.InvoiceOut)
def generate_invoice(billing_cycle_id: int, db: Session = Depends(get_db),
                      current_user: models.User = Depends(auth.get_current_user)):
    cycle = db.query(models.BillingCycle).filter(models.BillingCycle.id == billing_cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Billing cycle not found")

    subscription = cycle.subscription
    plan = subscription.plan
    customer = subscription.customer   # <-- need this to know their country

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

    # plan fee line item
    plan_fee_item = models.InvoiceLineItem(
        invoice_id=new_invoice.id,
        description=f"{plan.name} - {plan.billing_interval.value} plan fee",
        item_type=models.LineItemType.plan_fee,
        amount=plan.price,
    )
    db.add(plan_fee_item)

    # ---- TAX CALCULATION ----
    tax_amount = 0
    tax_rate_record = None
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

    # totals
    new_invoice.subtotal = plan.price
    new_invoice.tax_amount = tax_amount
    new_invoice.total = plan.price + tax_amount
    new_invoice.status = models.InvoiceStatus.open

    cycle.status = models.CycleStatus.invoiced

    db.commit()
    db.refresh(new_invoice)
    return new_invoice

@router.get("/", response_model=list[schemas.InvoiceOut])
def list_invoices(db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Invoice).all()

@router.get("/{invoice_id}", response_model=schemas.InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.get_current_user)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, db: Session = Depends(get_db),
                          current_user: models.User = Depends(auth.get_current_user)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    customer = invoice.billing_cycle.subscription.customer if invoice.billing_cycle else None
    plan = invoice.billing_cycle.subscription.plan if invoice.billing_cycle else None

    if not customer:
        raise HTTPException(status_code=400, detail="Cannot generate PDF for an invoice with no linked customer")

    filepath = generate_invoice_pdf(invoice, customer, plan)
    return FileResponse(filepath, media_type="application/pdf", filename=f"{invoice.invoice_number}.pdf")