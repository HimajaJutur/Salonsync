# ============================================
# salon/tests/__init__.py
# ============================================
# This file should be EMPTY or contain:

"""
Test suite for SalonSync application
"""

# ============================================
# salon/tests/test_models.py
# ============================================

from django.test import TestCase
from django.contrib.auth.models import User
from salon.models import Appointment, Coupon, Payment
import json
from datetime import date, time, timedelta


class AppointmentModelTests(TestCase):
    """Test Appointment model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_appointment_str_with_selected_services(self):
        """Test __str__ method with selected services"""
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='OTHER',
            date=date.today(),
            time=time(10, 0),
            selected_services=json.dumps([
                {"name": "Haircut", "price": 30, "minutes": 30}
            ]),
            total_cost=30,
            total_minutes=30
        )
        self.assertIn('Haircut', str(appt))
    
    def test_appointment_str_without_selected_services(self):
        """Test __str__ method without selected services"""
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0)
        )
        self.assertIn('Hair Styling', str(appt))
    
    def test_appointment_str_with_invalid_json(self):
        """Test __str__ method with invalid JSON"""
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0),
            selected_services='invalid json'
        )
        self.assertIn('Hair Styling', str(appt))
    
    def test_appointment_creation(self):
        """Test basic appointment creation"""
        appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0),
            total_cost=50,
            total_minutes=60
        )
        self.assertEqual(appt.user, self.user)
        self.assertEqual(appt.status, 'PENDING')
    
    def test_appointment_without_user(self):
        """Test appointment creation without user (guest booking)"""
        appt = Appointment.objects.create(
            user=None,
            name='Guest User',
            email='guest@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0)
        )
        self.assertIsNone(appt.user)


class CouponModelTests(TestCase):
    """Test Coupon model"""
    
    def test_coupon_creation(self):
        """Test coupon creation"""
        coupon = Coupon.objects.create(
            code='TEST10',
            discount=10,
            minimum_amount=20,
            active=True
        )
        self.assertEqual(str(coupon), 'TEST10')
        self.assertEqual(coupon.discount, 10)
    
    def test_coupon_unique_code(self):
        """Test coupon code uniqueness"""
        Coupon.objects.create(code='UNIQUE', discount=5, minimum_amount=10)
        
        with self.assertRaises(Exception):
            Coupon.objects.create(code='UNIQUE', discount=10, minimum_amount=20)


class PaymentModelTests(TestCase):
    """Test Payment model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.appt = Appointment.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            service='HAIR',
            date=date.today(),
            time=time(10, 0)
        )
    
    def test_payment_creation(self):
        """Test payment creation"""
        payment = Payment.objects.create(
            user=self.user,
            appointment=self.appt,
            amount=50.0,
            method='CARD',
            status='SUCCESS',
            transaction_id='TX123'
        )
        self.assertIn('TX123', str(payment))
        self.assertIn('CARD', str(payment))
        self.assertEqual(payment.status, 'SUCCESS')


# ============================================
# How to run these tests:
# ============================================
# 
# From your project root (where manage.py is):
# 
# python manage.py test salon.tests.test_models
# 
# ============================================