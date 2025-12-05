from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Appointment(models.Model):
    """
    One row = one booking.
    """
    # Who booked (optional: allow anonymous booking by setting null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Customer details (useful even if user is None, and for receipts/emails)
    name = models.CharField(max_length=100)
    email = models.EmailField()

    # What service did they choose?
    SERVICE_CHOICES = [
        ('HAIR', 'Hair Styling'),
        ('MAKEUP', 'Makeup'),
        ('SPA', 'Spa & Relaxation'),
        ('NAIL', 'Nail Care'),
        ('OTHER', 'Other'),
    ]
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)

    # When is the appointment?
    date = models.DateField()
    time = models.TimeField()

    # Extra notes (optional)
    notes = models.TextField(blank=True)

    # Status helps staff manage bookings
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

   # 🌸 NEW FIELDS for multiple service booking
    selected_services = models.TextField(blank=True)
    total_cost = models.IntegerField(default=0)
    total_minutes = models.IntegerField(default=0)

    # 🌟 STEP 3 — COUPON & DISCOUNT FIELDS (ADD HERE)
    coupon_code = models.CharField(max_length=20, blank=True, null=True)
    discount_given = models.IntegerField(default=0)

    # NEW: when this appointment was cancelled
    cancelled_at = models.DateTimeField(null=True, blank=True) 

    class Meta:
        ordering = ['-created_at']  # show newest first in admin/lists

    def __str__(self):
        # If there are selected services, show them instead of just 'Other'
        if self.selected_services and self.selected_services != "[]":
            try:
                import json
                services = json.loads(self.selected_services)
                names = [s.get("name", "") for s in services]
                return f"{self.name} — {', '.join(names)} on {self.date} at {self.time}"
            except Exception:
                pass
        return f"{self.name} — {self.get_service_display()} on {self.date} at {self.time}"


class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)   # e.g. "NEW5"
    discount = models.IntegerField()                      # flat amount, e.g. 5 € off
    minimum_amount = models.IntegerField(default=0)       # minimum subtotal to apply
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code
  
class Payment(models.Model):
    METHOD_CHOICES = [
        ("QR", "QR Payment"),
        ("CARD", "Credit/Debit Card"),
        ("CASH", "Cash at Salon"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)

    amount = models.FloatField()
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    transaction_id = models.CharField(max_length=100, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} — {self.method} — {self.status}"


