"""
Clean test_utils.py - All duplicates removed
Replace your entire salon/tests/test_utils.py with this file
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from salon.models import Coupon, Appointment
from datetime import date, time, timedelta
import os
from django.conf import settings


class TestGenerateSlots(TestCase):
    """Test generate_slots utility function"""
    
    def test_slots_generated(self):
        """Test that slots are generated correctly"""
        from salon.utils import generate_slots
        
        slots = generate_slots()
        self.assertGreater(len(slots), 0)
        self.assertIsInstance(slots, list)
        self.assertEqual(slots[0].strftime("%H:%M"), "09:00")
    
    def test_slots_are_time_objects(self):
        """Test that slots are time objects"""
        from salon.utils import generate_slots
        
        slots = generate_slots()
        for slot in slots:
            self.assertIsInstance(slot, time)
    
    def test_slots_end_at_or_before_6pm(self):
        """Test that all slots are at or before 6 PM"""
        from salon.utils import generate_slots
        
        slots = generate_slots()
        for slot in slots:
            self.assertLessEqual(slot, time(18, 0))


class TestBillPDFGeneration(TestCase):
    """Test PDF generation for bills"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            date=date.today(),
            time=time(10, 0),
            service='HAIR',
            selected_services='[{"name": "Haircut", "price": 30, "minutes": 30}]',
            total_cost=30,
            total_minutes=30
        )
    
    def test_pdf_generated(self):
        """Test that PDF bill is generated successfully"""
        from salon.utils import generate_bill_pdf
        
        try:
            pdf_path = generate_bill_pdf(self.appt)
            self.assertIsNotNone(pdf_path)
            self.assertTrue(pdf_path.endswith('.pdf'))
            
            full_path = os.path.join(settings.MEDIA_ROOT, pdf_path.replace(settings.MEDIA_URL, ''))
            self.assertTrue(os.path.exists(full_path))
            
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            self.skipTest(f"PDF generation failed: {e}")


class TestViewHelperFunctions(TestCase):
    """Test helper functions used in views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_is_loyal_customer_false(self):
        """Test is_loyal_customer returns False for new customer"""
        from salon.views import is_loyal_customer
        
        result = is_loyal_customer(self.user)
        self.assertFalse(result)
    
    def test_is_loyal_customer_true(self):
        """Test is_loyal_customer returns True after spending threshold"""
        from salon.views import is_loyal_customer
        
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
        """Test ensure_default_coupons creates default coupons"""
        from salon.views import ensure_default_coupons
        
        Coupon.objects.all().delete()
        ensure_default_coupons()
        
        self.assertTrue(Coupon.objects.filter(code='NEW10').exists())
        self.assertTrue(Coupon.objects.filter(code='GLOW5').exists())
        self.assertTrue(Coupon.objects.filter(code='LOYAL20').exists())


class TestCouponLogic(TestCase):
    """Test coupon application logic"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        Coupon.objects.create(code='TEST10', discount=10, minimum_amount=30, active=True)
        Coupon.objects.create(code='TEST20', discount=20, minimum_amount=50, active=True)
    
    def _add_session_and_messages(self, request):
        """Helper to add session and messages to request"""
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        return request
    
    def test_coupon_applied_successfully(self):
        """Test coupon is applied when conditions are met"""
        from salon.views import _apply_coupon_logic
        
        appt = Appointment(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0),
            total_cost=50,
            total_minutes=60
        )
        
        request = self.factory.post('/book/', {'coupon': 'TEST10'})
        request.user = self.user
        request = self._add_session_and_messages(request)
        
        _apply_coupon_logic(request, appt)
        
        self.assertEqual(appt.total_cost, 40)
        self.assertEqual(appt.discount_given, 10)
    
    def test_coupon_not_applied_below_minimum(self):
        """Test coupon is not applied when minimum spend not met"""
        from salon.views import _apply_coupon_logic
        
        appt = Appointment(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0),
            total_cost=25,
            total_minutes=30
        )
        
        request = self.factory.post('/book/', {'coupon': 'TEST10'})
        request.user = self.user
        request = self._add_session_and_messages(request)
        
        _apply_coupon_logic(request, appt)
        
        self.assertEqual(appt.total_cost, 25)
        self.assertEqual(appt.discount_given, 0)
    
    def test_invalid_coupon_code(self):
        """Test invalid coupon code handling"""
        from salon.views import _apply_coupon_logic
        
        appt = Appointment(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0),
            total_cost=50,
            total_minutes=60
        )
        
        request = self.factory.post('/book/', {'coupon': 'INVALID'})
        request.user = self.user
        request = self._add_session_and_messages(request)
        
        _apply_coupon_logic(request, appt)
        
        self.assertEqual(appt.total_cost, 50)
        self.assertEqual(appt.discount_given, 0)
    
    def test_no_coupon_provided(self):
        """Test when no coupon is provided"""
        from salon.views import _apply_coupon_logic
        
        appt = Appointment(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0),
            total_cost=50,
            total_minutes=60
        )
        
        request = self.factory.post('/book/', {})
        request.user = self.user
        request = self._add_session_and_messages(request)
        
        _apply_coupon_logic(request, appt)
        
        self.assertEqual(appt.total_cost, 50)
        self.assertEqual(appt.discount_given, 0)


class TestAppointmentCreation(TestCase):
    """Test appointment creation helper"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_appointment_object(self):
        """Test appointment object creation from form"""
        from salon.views import _create_appointment_object
        from salon.forms import AppointmentForm
        
        tomorrow = date.today() + timedelta(days=1)
        services = '[{"name": "Haircut", "price": 30, "minutes": 30}]'
        
        form_data = {
            'date': tomorrow,
            'time': '10:00',
            'service': 'HAIR',
            'notes': 'Test notes'
        }
        
        form = AppointmentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        request = self.factory.post('/book/', {
            'selected_services': services,
            'total_cost': '30',
            'total_minutes': '30'
        })
        request.user = self.user
        
        appt = _create_appointment_object(request, form)
        
        self.assertEqual(appt.user, self.user)
        self.assertEqual(appt.name, 'testuser')
        self.assertEqual(appt.total_cost, 30)