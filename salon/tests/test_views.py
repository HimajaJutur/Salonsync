from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from salon.models import Appointment, Coupon, Payment
from datetime import date, time, datetime, timedelta
from django.utils import timezone
import json
from unittest.mock import patch


class AuthenticationTests(TestCase):
    """Test suite for user authentication"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )

    def test_login_page_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/login.html")

    def test_login_with_username(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "testpass123"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_with_email(self):
        response = self.client.post(reverse("login"), {
            "username": "test@example.com",
            "password": "testpass123"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/login.html")

    def test_register_page_get(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/register.html")

    @patch('salon.views.send_mail')
    def test_register_user_success(self, mock_mail):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!"
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(mock_mail.called)

    def test_register_user_invalid_form(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "invalid-email",
            "password1": "pass",
            "password2": "different"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/register.html")

    def test_logout_user(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login"))


class DashboardTests(TestCase):
    """Test suite for dashboard and profile views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )

    def test_dashboard_view_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/dashboard.html")

    def test_dashboard_view_unauthenticated(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_profile_view(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/profile.html")


class AppointmentBookingTests(TestCase):
    """Test suite for booking appointments"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )
        Coupon.objects.create(code="NEW10", discount=10, minimum_amount=30, active=True)
        Coupon.objects.create(code="GLOW5", discount=5, minimum_amount=20, active=True)
        Coupon.objects.create(code="LOYAL20", discount=20, minimum_amount=30, active=True)

    def test_book_appointment_get(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("book_appointment"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/book_appointment.html")

    @patch('salon.views.generate_bill_pdf')
    def test_book_appointment_post_valid(self, mock_pdf):
        self.client.login(username="testuser", password="testpass123")
        
        tomorrow = date.today() + timedelta(days=1)
        services = json.dumps([{"name": "Haircut", "price": 50, "duration": 60}])
        
        response = self.client.post(reverse("book_appointment"), {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "time": "10:00",
            "selected_services": services,
            "total_cost": "50",
            "total_minutes": "60",
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Appointment.objects.filter(user=self.user).exists())
        self.assertTrue(mock_pdf.called)

    @patch('salon.views.generate_bill_pdf')
    def test_book_appointment_with_valid_coupon(self, mock_pdf):
        self.client.login(username="testuser", password="testpass123")
        
        tomorrow = date.today() + timedelta(days=1)
        services = json.dumps([{"name": "Haircut", "price": 50, "duration": 60}])
        
        response = self.client.post(reverse("book_appointment"), {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "time": "10:00",
            "selected_services": services,
            "total_cost": "50",
            "total_minutes": "60",
            "coupon": "NEW10"
        })
        
        appt = Appointment.objects.filter(user=self.user).first()
        self.assertEqual(appt.total_cost, 40)
        self.assertEqual(appt.discount_given, 10)
        self.assertTrue(mock_pdf.called)

    @patch('salon.views.generate_bill_pdf')
    def test_book_appointment_with_invalid_coupon(self, mock_pdf):
        self.client.login(username="testuser", password="testpass123")
        
        tomorrow = date.today() + timedelta(days=1)
        services = json.dumps([{"name": "Haircut", "price": 50, "duration": 60}])
        
        response = self.client.post(reverse("book_appointment"), {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "time": "10:00",
            "selected_services": services,
            "total_cost": "50",
            "total_minutes": "60",
            "coupon": "INVALID"
        })
        
        appt = Appointment.objects.filter(user=self.user).first()
        self.assertEqual(appt.total_cost, 50)
        self.assertTrue(mock_pdf.called)

    @patch('salon.views.generate_bill_pdf')
    def test_book_appointment_coupon_below_minimum(self, mock_pdf):
        self.client.login(username="testuser", password="testpass123")
        
        tomorrow = date.today() + timedelta(days=1)
        services = json.dumps([{"name": "Service", "price": 15, "duration": 30}])
        
        response = self.client.post(reverse("book_appointment"), {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "time": "10:00",
            "selected_services": services,
            "total_cost": "15",
            "total_minutes": "30",
            "coupon": "GLOW5"
        })
        
        appt = Appointment.objects.filter(user=self.user).first()
        self.assertEqual(appt.total_cost, 15)
        self.assertTrue(mock_pdf.called)


class AppointmentViewTests(TestCase):
    """Test suite for viewing appointments"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="staffpass123",
            email="staff@example.com",
            is_staff=True
        )

    def test_my_appointments_view(self):
        self.client.login(username="testuser", password="testpass123")
        
        Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.get(reverse("my_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/my_appointments.html")
        self.assertEqual(len(response.context["appointments"]), 1)

    def test_view_bill_success(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            selected_services=json.dumps([{"name": "Haircut", "price": 50}])
        )
        
        response = self.client.get(reverse("view_bill", args=[appt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/bill.html")

    def test_view_bill_cancelled_appointment(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            status="CANCELLED"
        )
        
        response = self.client.get(reverse("view_bill", args=[appt.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("my_appointments"))

    def test_view_bill_staff_access(self):
        self.client.login(username="staffuser", password="staffpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.get(reverse("view_bill", args=[appt.pk]))
        self.assertEqual(response.status_code, 200)


class CancellationTests(TestCase):
    """Test suite for appointment cancellation"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )

    @patch('salon.views.send_mail')
    def test_cancel_appointment_success(self, mock_mail):
        self.client.login(username="testuser", password="testpass123")
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=future_time.date(),
            time=future_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.post(reverse("cancel_appointment", args=[appt.pk]))
        self.assertEqual(response.status_code, 302)
        
        appt.refresh_from_db()
        self.assertEqual(appt.status, "CANCELLED")
        self.assertTrue(mock_mail.called)

    def test_cancel_appointment_within_2_hours(self):
        self.client.login(username="testuser", password="testpass123")
        
        soon_time = timezone.now() + timedelta(hours=1)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=soon_time.date(),
            time=soon_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.post(reverse("cancel_appointment", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertNotEqual(appt.status, "CANCELLED")

    def test_cancel_already_cancelled(self):
        self.client.login(username="testuser", password="testpass123")
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=future_time.date(),
            time=future_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            status="CANCELLED"
        )
        
        response = self.client.post(reverse("cancel_appointment", args=[appt.pk]))
        self.assertEqual(response.status_code, 302)

    def test_cancel_paid_appointment(self):
        self.client.login(username="testuser", password="testpass123")
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=future_time.date(),
            time=future_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        Payment.objects.create(
            user=self.user,
            appointment=appt,
            amount=50,
            method="CARD",
            status="SUCCESS",
            transaction_id="test123"
        )
        
        response = self.client.post(reverse("cancel_appointment", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertNotEqual(appt.status, "CANCELLED")


class ReactivationTests(TestCase):
    """Test suite for appointment reactivation"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="staffpass123",
            is_staff=True
        )

    @patch('salon.views.send_mail')
    def test_reactivate_appointment_within_1_hour(self, mock_mail):
        self.client.login(username="testuser", password="testpass123")
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=future_time.date(),
            time=future_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            status="CANCELLED",
            cancelled_at=timezone.now() - timedelta(minutes=30)
        )
        
        response = self.client.post(reverse("reactivate_appointment", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, "PENDING")
        self.assertTrue(mock_mail.called)

    def test_reactivate_appointment_after_1_hour(self):
        self.client.login(username="testuser", password="testpass123")
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=future_time.date(),
            time=future_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            status="CANCELLED",
            cancelled_at=timezone.now() - timedelta(hours=2)
        )
        
        response = self.client.post(reverse("reactivate_appointment", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, "CANCELLED")

    def test_reactivate_by_staff(self):
        self.client.login(username="staffuser", password="staffpass123")
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=future_time.date(),
            time=future_time.time(),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            status="CANCELLED",
            cancelled_at=timezone.now() - timedelta(hours=5)
        )
        
        response = self.client.post(reverse("reactivate_appointment", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, "PENDING")


class PaymentTests(TestCase):
    """Test suite for payment processing"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )

    def test_choose_payment(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.get(reverse("choose_payment", args=[appt.pk]))
        self.assertEqual(response.status_code, 200)

    def test_choose_payment_cancelled_appointment(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            status="CANCELLED"
        )
        
        response = self.client.get(reverse("choose_payment", args=[appt.pk]))
        self.assertEqual(response.status_code, 302)

    def test_qr_payment(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.get(reverse("qr_payment", args=[appt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Payment.objects.filter(appointment=appt).exists())

    def test_payment_success(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        payment = Payment.objects.create(
            user=self.user,
            appointment=appt,
            amount=50,
            method="CARD",
            status="PENDING",
            transaction_id="test123"
        )
        
        response = self.client.get(reverse("payment_success", args=["test123"]))
        self.assertEqual(response.status_code, 200)
        
        payment.refresh_from_db()
        self.assertEqual(payment.status, "SUCCESS")

    def test_card_payment_post(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.post(reverse("card_payment", args=[appt.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(appointment=appt, method="CARD").exists())

    def test_cash_payment(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60
        )
        
        response = self.client.get(reverse("cash_payment", args=[appt.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(appointment=appt, method="CASH").exists())

    def test_payment_page(self):
        self.client.login(username="testuser", password="testpass123")
        
        appt = Appointment.objects.create(
            user=self.user,
            name="testuser",
            email="test@example.com",
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service="HAIRCUT",
            total_cost=50,
            total_minutes=60,
            selected_services=json.dumps([{"name": "Haircut", "price": 50}])
        )
        
        response = self.client.get(reverse("payment_page", args=[appt.pk]))
        self.assertEqual(response.status_code, 200)


class StaticPageTests(TestCase):
    """Test suite for static pages"""

    def setUp(self):
        self.client = Client()

    def test_contact_page(self):
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)

    def test_salon_location_page(self):
        response = self.client.get(reverse("salon_location"))
        self.assertEqual(response.status_code, 200)

    def test_services_page(self):
        response = self.client.get(reverse("services"))
        self.assertEqual(response.status_code, 200)


class UtilityTests(TestCase):
    """Test suite for utility functions"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )

    def test_check_available_slots(self):
        self.client.login(username="testuser", password="testpass123")
        
        tomorrow = date.today() + timedelta(days=1)
        response = self.client.get(reverse("check_available_slots"), {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "duration": "60"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("slots", data)

    def test_check_available_slots_missing_params(self):
        self.client.login(username="testuser", password="testpass123")
        
        response = self.client.get(reverse("check_available_slots"))
        self.assertEqual(response.status_code, 400)

    def test_is_loyal_customer(self):
        from salon.views import is_loyal_customer
        
        for i in range(5):
            Appointment.objects.create(
                user=self.user,
                name="testuser",
                email="test@example.com",
                date=date.today() - timedelta(days=i),
                time=time(10, 0),
                service="HAIRCUT",
                total_cost=50,
                total_minutes=60,
                status="CONFIRMED"
            )
        
        self.assertTrue(is_loyal_customer(self.user))

def test_cancel_appointment_with_successful_payment(self):
    """User cannot cancel appointment that is already paid."""
    self.client.login(username='testuser', password='testpass123')

    future = timezone.now() + timedelta(hours=5)

    appt = Appointment.objects.create(
        user=self.user,
        name='Test User',
        email='test@example.com',
        date=future.date(),
        time=future.time(),
        service='HAIR',
        total_cost=50,
        total_minutes=60
    )

    Payment.objects.create(
        user=self.user,
        appointment=appt,
        amount=50,
        method="CARD",
        status="SUCCESS",
        transaction_id="tx123"
    )

    response = self.client.post(f'/appointments/{appt.pk}/cancel/')
    self.assertEqual(response.status_code, 302)

    appt.refresh_from_db()
    self.assertNotEqual(appt.status, "CANCELLED")


def test_cancel_appointment_within_two_hours(self):
    """Cancelling within 2 hours should be blocked."""
    self.client.login(username='testuser', password='testpass123')

    future = timezone.now() + timedelta(minutes=90)

    appt = Appointment.objects.create(
        user=self.user,
        name='Test User',
        email='test@example.com',
        date=future.date(),
        time=future.time(),
        service='HAIR',
        total_cost=50,
        total_minutes=60
    )

    response = self.client.post(f'/appointments/{appt.pk}/cancel/')
    self.assertEqual(response.status_code, 302)

    appt.refresh_from_db()
    self.assertNotEqual(appt.status, "CANCELLED")

def test_cancel_already_cancelled_appointment(self):
    """Cancelling an already cancelled appointment should not change anything."""
    self.client.login(username='testuser', password='testpass123')

    future = timezone.now() + timedelta(hours=5)

    appt = Appointment.objects.create(
        user=self.user,
        name='Test User',
        email='test@example.com',
        date=future.date(),
        time=future.time(),
        service='HAIR',
        total_cost=50,
        total_minutes=60,
        status='CANCELLED'
    )

    response = self.client.post(f'/appointments/{appt.pk}/cancel/')
    self.assertEqual(response.status_code, 302)

    appt.refresh_from_db()
    self.assertEqual(appt.status, "CANCELLED")

@patch("salon.views.send_mail", side_effect=Exception("Mail error"))
def test_cancel_appointment_email_failure(self, _mock_mail):
    """Cancel appointment should still succeed even if email sending fails."""
    self.client.login(username='testuser', password='testpass123')

    future = timezone.now() + timedelta(hours=5)

    appt = Appointment.objects.create(
        user=self.user,
        name='Test User',
        email='test@example.com',
        date=future.date(),
        time=future.time(),
        service='HAIR',
        total_cost=50,
        total_minutes=60
    )

    response = self.client.post(f'/appointments/{appt.pk}/cancel/')
    self.assertEqual(response.status_code, 302)

    appt.refresh_from_db()
    self.assertEqual(appt.status, "CANCELLED")

class RegisterUserTests(TestCase):

    def setUp(self):
        self.client = Client()

    @patch("salon.views.send_mail")
    def test_register_user_valid(self, mock_send):
        """Covers: success branch, send_mail, redirect"""
        response = self.client.post(reverse("register"), {
            "username": "testuser",
            "email": "abc@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="testuser").exists())
        mock_send.assert_called_once()

    def test_register_user_invalid_form(self):
        """Covers the for-loop over form errors (uncovered red area)"""
        response = self.client.post(reverse("register"), {
            "username": "",
            "email": "bad",
            "password1": "123",
            "password2": "321",
        })

        # stays on same page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_register_user_get_request(self):
        """Covers GET request block"""
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "salon/register.html")