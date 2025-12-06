from django.test import TestCase
from salon.models import Appointment, Coupon
from django.contrib.auth.models import User
from datetime import date, time

class ModelTests(TestCase):

    def test_appointment_creation(self):
        user = User.objects.create_user(username="a", password="b")
        appt = Appointment.objects.create(
            user=user,
            name="Test",
            email="a@b.com",
            date=date.today(),
            time=time(10, 0),
            service="Haircut",
            total_cost=50
        )
        self.assertEqual(appt.total_cost, 50)

    def test_coupon_creation(self):
        c = Coupon.objects.create(
            code="TEST10",
            discount=10,
            minimum_amount=20,
            active=True
        )
        self.assertEqual(c.code, "TEST10")