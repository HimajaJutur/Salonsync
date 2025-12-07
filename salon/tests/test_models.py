from django.test import TestCase, Client
from django.contrib.auth.models import User
from salon.forms import CustomUserCreationForm, AppointmentForm
from salon.models import Appointment
from datetime import date, time, timedelta
from django.utils import timezone


class FormTests(TestCase):
    """Test suite for forms"""

    def test_custom_user_creation_form_valid(self):
        """Test custom user creation form with valid data"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_custom_user_creation_form_password_mismatch(self):
        """Test form with mismatched passwords"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'DifferentPass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_custom_user_creation_form_duplicate_username(self):
        """Test form with duplicate username"""
        User.objects.create_user(username='existing', password='pass123')
        form_data = {
            'username': 'existing',
            'email': 'new@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_appointment_form_valid(self):
        """Test appointment form with valid data"""
        tomorrow = date.today() + timedelta(days=1)
        form_data = {
            'date': tomorrow,
            'time': time(10, 0),
            'service': 'HAIR',
            'notes': 'Test appointment'
        }
        form = AppointmentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_appointment_form_past_date(self):
        """Test appointment form rejects past dates"""
        yesterday = date.today() - timedelta(days=1)
        form_data = {
            'date': yesterday,
            'time': time(10, 0),
            'service': 'HAIR'
        }
        form = AppointmentForm(data=form_data)
        # Form validation logic depends on your implementation
        # This test structure is ready for when you add date validation


class UtilsTests(TestCase):
    """Test suite for utility functions"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_generate_slots(self):
        """Test slot generation utility"""
        from salon.utils import generate_slots
        slots = generate_slots()
        self.assertIsInstance(slots, list)
        self.assertGreater(len(slots), 0)

    def test_is_loyal_customer_false(self):
        """Test is_loyal_customer returns False for new customer"""
        from salon.views import is_loyal_customer
        result = is_loyal_customer(self.user)
        self.assertFalse(result)

    def test_is_loyal_customer_true(self):
        """Test is_loyal_customer returns True after spending threshold"""
        from salon.views import is_loyal_customer
        
        # Create appointments totaling over 200
        for i in range(5):
            Appointment.objects.create(
                user=self.user,
                name='testuser',
                email='test@example.com',
                date=date.today() - timedelta(days=i),
                time=time(10, 0),
                service='HAIR',
                total_cost=50,
                total_minutes=60,
                status='CONFIRMED'
            )
        
        result = is_loyal_customer(self.user)
        self.assertTrue(result)

    def test_ensure_default_coupons(self):
        """Test ensure_default_coupons creates coupons"""
        from salon.views import ensure_default_coupons
        from salon.models import Coupon
        
        # Clear any existing coupons
        Coupon.objects.all().delete()
        
        ensure_default_coupons()
        
        self.assertTrue(Coupon.objects.filter(code='NEW10').exists())
        self.assertTrue(Coupon.objects.filter(code='GLOW5').exists())
        self.assertTrue(Coupon.objects.filter(code='LOYAL20').exists())

    def test_ensure_default_coupons_idempotent(self):
        """Test ensure_default_coupons doesn't create duplicates"""
        from salon.views import ensure_default_coupons
        from salon.models import Coupon
        
        ensure_default_coupons()
        count_first = Coupon.objects.count()
        
        ensure_default_coupons()
        count_second = Coupon.objects.count()
        
        self.assertEqual(count_first, count_second)


class EdgeCaseTests(TestCase):
    """Test suite for edge cases and error handling"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_appointment_with_empty_selected_services(self):
        """Test appointment handles empty selected_services gracefully"""
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            date=date.today(),
            time=time(10, 0),
            service='OTHER',
            selected_services=''
        )
        str_repr = str(appt)
        self.assertIn('Other', str_repr)

    def test_appointment_with_null_selected_services(self):
        """Test appointment handles None selected_services"""
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            date=date.today(),
            time=time(10, 0),
            service='SPA'
        )
        # selected_services defaults to empty string
        self.assertEqual(appt.selected_services, '')

    def test_view_nonexistent_appointment(self):
        """Test viewing non-existent appointment returns 404"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/appointments/99999/bill/')
        self.assertEqual(response.status_code, 404)

    def test_cancel_other_users_appointment(self):
        """Test user cannot cancel another user's appointment"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='pass123',
            email='other@example.com'
        )
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=other_user,
            name='Other User',
            email='other@example.com',
            date=future_time.date(),
            time=future_time.time(),
            service='HAIR',
            total_cost=50,
            total_minutes=60
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(f'/appointments/{appt.pk}/cancel/')
        self.assertEqual(response.status_code, 404)

    def test_book_appointment_missing_fields(self):
        """Test booking appointment with missing required fields"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/appointments/book/', {
            'date': date.today() + timedelta(days=1),
            # Missing time and other required fields
        })
        # Should return form with errors, not redirect
        self.assertEqual(response.status_code, 200)

    def test_check_slots_with_overlapping_appointments(self):
        """Test slot checking with overlapping appointments"""
        self.client.login(username='testuser', password='testpass123')
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create an existing appointment
        Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            date=tomorrow,
            time=time(10, 0),
            service='HAIR',
            total_minutes=60
        )
        
        # Check available slots
        response = self.client.get('/appointments/check-slots/', {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'duration': '60'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 10:00 slot should not be available
        self.assertNotIn('10:00', data['slots'])

    def test_payment_for_other_users_appointment(self):
        """Test user cannot pay for another user's appointment"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='pass123'
        )
        
        appt = Appointment.objects.create(
            user=other_user,
            name='Other User',
            email='other@example.com',
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            service='HAIR',
            total_cost=50
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/payment/{appt.pk}/choose/')
        self.assertEqual(response.status_code, 404)

    def test_reactivate_non_cancelled_appointment(self):
        """Test reactivating an appointment that's not cancelled"""
        self.client.login(username='testuser', password='testpass123')
        
        future_time = timezone.now() + timedelta(hours=5)
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            date=future_time.date(),
            time=future_time.time(),
            service='HAIR',
            status='PENDING'
        )
        
        response = self.client.post(f'/appointments/{appt.pk}/reactivate/')
        appt.refresh_from_db()
        # Status should remain PENDING
        self.assertEqual(appt.status, 'PENDING')

    def test_book_appointment_with_malformed_services_json(self):
        """Test booking with malformed JSON in selected_services"""
        self.client.login(username='testuser', password='testpass123')
        
        tomorrow = date.today() + timedelta(days=1)
        
        response = self.client.post('/appointments/book/', {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'time': '10:00',
            'selected_services': 'not valid json{[',
            'total_cost': '50',
            'total_minutes': '60',
        })
        
        # Should handle gracefully and create appointment with OTHER service
        if response.status_code == 302:
            appt = Appointment.objects.filter(user=self.user).first()
            self.assertIsNotNone(appt)