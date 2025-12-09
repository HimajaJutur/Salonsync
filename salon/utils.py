from datetime import datetime, time, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.conf import settings
import os
import json

def inr_to_eur(inr):
    """
    Converts INR to Euro using approx. 1 EUR = 89 INR.
    """
    return round(inr / 89)


# -----------------------------
# ✔ 2. Generate time slots
# -----------------------------
def generate_slots(start_hour=9, end_hour=18, interval_minutes=15):
    """
    Creates start-time slots every 15 minutes between 9 AM and 6 PM.
    Example: 09:00, 09:15, 09:30 ...
    """
    slots = []
    current = time(hour=start_hour, minute=0)
    end = time(hour=end_hour, minute=0)

    while datetime.combine(datetime.today(), current) <= datetime.combine(datetime.today(), end):
        slots.append(current)
        # Add interval
        dt = (datetime.combine(datetime.today(), current) + timedelta(minutes=interval_minutes)).time()
        current = dt

    return slots


# -----------------------------
# ✔ 3. Slot Overlap Checker
# -----------------------------
def is_overlap(start1, end1, start2, end2):
    """
    Returns True if two time ranges overlap.
    """
    return not (end1 <= start2 or start1 >= end2)



# -----------------------------
# ✔ 4. Generate Bill PDF
# -----------------------------
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_bill_pdf(appointment):
    """
    Creates a clean PDF bill file and returns the file path.
    """
    filename = f"bill_{appointment.id}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, filename)

    # Create PDF canvas
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "SalonSync - Appointment Bill")
    y -= 40

    # Customer details
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Customer: {appointment.name}")
    y -= 20
    c.drawString(50, y, f"Email: {appointment.email}")
    y -= 20
    c.drawString(50, y, f"Date: {appointment.date}")
    y -= 20
    c.drawString(50, y, f"Time: {appointment.time}")
    y -= 30

    # Services
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Services:")
    y -= 20

    try:
        services = json.loads(appointment.selected_services)
    except (json.JSONDecodeError, TypeError):
        services = []

    c.setFont("Helvetica", 12)
    for s in services:
        c.drawString(70, y, f"{s['name']} — €{s['cost']} ({s['time']} mins)")
        y -= 18

    # Pricing
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Total Cost: €{appointment.total_cost}")
    y -= 20

    if appointment.discount_given > 0:
        c.drawString(50, y, f"Discount Applied: €{appointment.discount_given}")
        y -= 20

    c.drawString(50, y, f"Final Amount: €{appointment.total_cost}")
    y -= 30

    # Footer
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Thank you for choosing SalonSync! 💖")

    c.save()
    return pdf_path
