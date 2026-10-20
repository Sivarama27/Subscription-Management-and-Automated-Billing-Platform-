from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

INVOICE_DIR = "invoices"


def generate_invoice_pdf(invoice, customer, plan) -> str:
    os.makedirs(INVOICE_DIR, exist_ok=True)
    filepath = os.path.join(INVOICE_DIR, f"{invoice.invoice_number}.pdf")

    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=20, spaceAfter=10)
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 4 * mm))

    meta_data = [
        ["Invoice Number:", invoice.invoice_number],
        ["Issued:", invoice.issued_at.strftime("%Y-%m-%d")],
        ["Due:", invoice.due_at.strftime("%Y-%m-%d") if invoice.due_at else "-"],
        ["Status:", invoice.status.value.upper()],
    ]
    meta_table = Table(meta_data, colWidths=[40 * mm, 100 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph(f"<b>Bill To:</b> {customer.name}", styles["Normal"]))
    elements.append(Paragraph(f"{customer.email}", styles["Normal"]))
    if customer.billing_country:
        elements.append(Paragraph(f"{customer.billing_country}", styles["Normal"]))
    elements.append(Spacer(1, 8 * mm))

    line_data = [["Description", "Type", "Amount"]]
    for item in invoice.line_items:
        line_data.append([item.description, item.item_type.value, f"{item.amount:.2f}"])

    line_table = Table(line_data, colWidths=[90 * mm, 40 * mm, 30 * mm])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d2d2d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 6 * mm))

    totals_data = [
        ["Subtotal:", f"{invoice.subtotal:.2f}"],
        ["Tax:", f"{invoice.tax_amount:.2f}"],
        ["Total:", f"{invoice.total:.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[130 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.black),
    ]))
    elements.append(totals_table)

    doc.build(elements)
    return filepath