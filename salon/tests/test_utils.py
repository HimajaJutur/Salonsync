from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from salon.utils import (
    inr_to_eur,
    is_overlap,
    generate_slots,
    _ensure_coupons_exist,
    _create_appointment_object,
    _apply_coupon_logic,
    generate_bill_pdf,
)
from salon.forms import AppointmentForm
from salon.models import Coupon, Appointment
from unittest.mock import patch
from datetime import date, time, timedelta
import os
from django.conf import settings
import json

class TestINRConversion(TestCase):
    def test_inr_to_eur_basic(self):
        self.assertEqual(inr_to_eur(89), 1)
        self.assertEqual(inr_to_eur(178), 2)
        self.assertEqual(inr_to_eur(0), 0)

class TestOverlap(TestCase):
    def test_overlap_true(self):
        self.assertTrue(is_overlap(time(10,0), time(11,0), time(10,30), time(11,30)))

    def test_overlap_false(self):
        self.assertFalse(is_overlap(time(10,0), time(11,0), time(11,0), time(12,0)))

class TestGenerateSlots(TestCase):
    def test_slots_generated(self):
        slots = generate_slots()
        self.assertGreater(len(slots), 0)
        self.assertEqual(slots[0].strftime("%H:%M"), "09:00")

class TestEnsureCoupons(TestCase):
    def test_default_coupons_created(self):
        Coupon.objects.all().delete()
        _ensure_coupons_exist()

        self.assertTrue(Coupon.objects.filter(code="NEW10").exists())
        self.assertTrue(Coupon.objects.filter(code="GLOW5").exists())
        self.assertTrue(Coupon.objects.filter(code="LOYAL20").exists())


class TestCreateAppointment(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("test", "test@mail.com", "123")

    def test_appointment_object_creation(self):
        data = {
            "date": date.today(),
            "time": "10:00",
            "service": "HAIR"
        }

        request = self.factory.post("/appointments/book/", data)
        request.user = self.user

        form = AppointmentForm(data)
        appt = _create_appointment_object(request, form)

        self.assertEqual(appt.name, "test")
        self.assertEqual(appt.email, "test@mail.com")

class TestCouponLogic(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("u", "u@test.com", "123")
        self.appt = Appointment(
            name="u",
            email="u@test.com",
            service="HAIR",
            date=date.today(),
            time=time(10,0),
            total_cost=50
        )

    def test_valid_coupon(self):
        Coupon.objects.create(code="NEW10", discount=10, minimum_amount=30)

        request = self.factory.post("/", {"coupon": "NEW10"})
        request.user = self.user

        _apply_coupon_logic(request, self.appt)

        self.assertEqual(self.appt.total_cost, 40)
        self.assertEqual(self.appt.discount_given, 10)

    def test_invalid_coupon(self):
        request = self.factory.post("/", {"coupon": "FAKE"})
        request.user = self.user

        _apply_coupon_logic(request, self.appt)

        self.assertEqual(self.appt.total_cost, 50)

class TestPDFGeneration(TestCase):
    @patch("salon.utils.canvas.Canvas")
    def test_pdf_generated(self, mock_canvas):
        appt = Appointment(
            id=1,
            name="Test",
            email="t@test.com",
            date=date.today(),
            time=time(10,0),
            service="HAIR",
            selected_services="[]",
            total_cost=50,
        )

        path = generate_bill_pdf(appt)

        self.assertTrue(path.endswith("bill_1.pdf"))
        mock_canvas.assert_called()

