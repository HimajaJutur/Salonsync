from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm 
from django.contrib.auth.models import User
from .forms import CustomUserCreationForm, AppointmentForm
from datetime import date
from django.db import models
import json
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from django.http import HttpResponseForbidden
from .utils import generate_slots
from django.http import JsonResponse
import qrcode
import uuid
from django.conf import settings
import os
from io import BytesIO
from .models import Appointment, Coupon, Payment
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .utils import generate_bill_pdf
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods



@csrf_protect
def register_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')

            #  Send welcome email
            send_mail(
                subject='Welcome to SalonSync ',
                message=f'Hi {username},\n\nWelcome to SalonSync! Your account has been created successfully. You can now log in to book your salon sessions.\n\nWith love,\nThe SalonSync Team ',
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, f' Account created successfully for {username}! A welcome email has been sent.')
            return redirect('login')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return render(request, 'salon/register.html', {'form': form})
    else:
        form = CustomUserCreationForm()

    return render(request, 'salon/register.html', {'form': form})

@csrf_protect
def login_user(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')

        # Allow login with either username or email
        user = authenticate(request, username=username_or_email, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}! 💕')
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username/email or password.")
            return render(request, 'salon/login.html')

    return render(request, 'salon/login.html')

@require_http_methods(["GET"])
def logout_user(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_view(request):
    return render(request, 'salon/dashboard.html', {
        'is_loyal': is_loyal_customer(request.user)
    })

def profile(request):
    return render(request, 'salon/profile.html')

@csrf_protect
@login_required
def book_appointment(request):
    _ensure_coupons_exist()

    if request.method == 'POST':
        form = AppointmentForm(request.POST)

        if form.is_valid():
            appointment = _create_appointment_object(request, form)

            # Apply coupon safely
            _apply_coupon_logic(request, appointment)

            # Save + generate bill
            _save_and_generate_pdf(appointment)

            messages.success(request, "Appointment booked successfully!")
            return redirect("my_appointments")

        messages.error(request, "Please fix the form errors and try again.")
    else:
        form = AppointmentForm()

    coupons = Coupon.objects.all()

    return render(request, "salon/book_appointment.html", {
        "form": form,
        "coupons": coupons,
        "is_loyal": is_loyal_customer(request.user),
    })


# ---------------------------
# 🔽 Helper Functions Below
# ---------------------------

def _ensure_coupons_exist():
    try:
        ensure_default_coupons()
    except Exception:
        pass


def _create_appointment_object(request, form):
    appointment = form.save(commit=False)
    appointment.user = request.user

    # Auto-fill details
    appointment.name = request.user.username
    appointment.email = request.user.email or "noemail@unknown.com"

    # Read selected services
    selected_services = request.POST.get("selected_services", "[]")
    appointment.selected_services = selected_services
    appointment.total_cost = int(request.POST.get("total_cost", 0))
    appointment.total_minutes = int(request.POST.get("total_minutes", 0))

    # Determine primary service
    try:
        services_list = json.loads(selected_services)
        appointment.service = services_list[0].get("name", "OTHER") if services_list else "OTHER"
    except (json.JSONDecodeError, TypeError):
        appointment.service = "OTHER"

    return appointment


def _apply_coupon_logic(request, appointment):
    coupon_code = request.POST.get("coupon", "").strip().upper()
    discount_amount = 0

    if coupon_code:
        try:
            coupon_obj = Coupon.objects.get(code=coupon_code)

            # Min spend check
            if appointment.total_cost >= coupon_obj.minimum_amount:
                discount_amount = coupon_obj.discount
            else:
                messages.warning(
                    request,
                    f"⚠️ Coupon '{coupon_code}' requires minimum spend of €{coupon_obj.minimum_amount}."
                )
        except Coupon.DoesNotExist:
            messages.warning(request, f"⚠️ Coupon '{coupon_code}' is invalid.")

    # Loyalty rule
    if coupon_code == "LOYAL20" and not is_loyal_customer(request.user):
        messages.error(request, "This coupon is only for loyalty members.")
        discount_amount = 0

    # Apply discount
    if discount_amount > 0:
        appointment.total_cost = max(0, appointment.total_cost - int(discount_amount))
        appointment.discount_given = int(discount_amount)
        appointment.coupon_code = coupon_code
    else:
        appointment.discount_given = 0
        appointment.coupon_code = ""


def _save_and_generate_pdf(appointment):
    appointment.save()

    # Generate PDF
    generate_bill_pdf(appointment)


@login_required
def my_appointments(request):
    appointments = Appointment.objects.filter(user=request.user).order_by('-date', '-time')

    # attach payment status to each appointment
    for appt in appointments:
        payment = Payment.objects.filter(appointment=appt).order_by('-id').first()
        appt.payment_status = payment.status if payment else "NONE"

    return render(request, 'salon/my_appointments.html', {
        'appointments': appointments,
        'today': date.today(),
        'is_loyal': is_loyal_customer(request.user),
    })

@login_required
def view_bill(request, pk):
    """
    Non-CRUD Billing:
    - Read Appointment
    - Read selected_services JSON
    - Calculate subtotal, tax, grand total
    - Render bill page (NO database write)
    """

    # Allow staff to view any; customers only their own
    if request.user.is_staff:
        appt = get_object_or_404(Appointment, pk=pk)
    else:
        appt = get_object_or_404(Appointment, pk=pk, user=request.user)

    #  Block bill if appointment is cancelled
    if appt.status == "CANCELLED":
        messages.error(request, "You cannot generate a bill for a cancelled appointment.")
        return redirect('my_appointments')

    #  Load selected services from JSON
    selected_services = []
    if appt.selected_services:
        try:
            selected_services = json.loads(appt.selected_services)
        except (json.JSONDecodeError, TypeError):
            selected_services = []

    #  Subtotal in EURO (already stored correctly)
    subtotal = appt.total_cost or 0

    #  Billing rules — Europe (Usually 0% unless VAT added)
    TAX_RATE = 0
    tax_amount = round(subtotal * TAX_RATE / 100)
    grand_total = subtotal + tax_amount

    return render(
        request,
        "salon/bill.html",
        {
            "appointment": appt,
            "services": selected_services,
            "subtotal": subtotal,
            "tax_rate": TAX_RATE,
            "tax_amount": tax_amount,
            "grand_total": grand_total,
        }
    )


def contact(request):
    return render(request, 'salon/contact.html')

def salon_location(request):
    return render(request, 'salon/salon_location.html')

def services(request):
    return render(request, 'salon/services.html')

@csrf_protect
@login_required
def cancel_appointment(request, pk):
    # staff can cancel any; users only their own
    appt = get_object_or_404(
        Appointment,
        pk=pk,
        **({} if request.user.is_staff else {"user": request.user})
    )

    if request.method != "POST":
        return redirect('my_appointments')

    # NEW: block cancel if already paid
    if Payment.objects.filter(appointment=appt, status="SUCCESS").exists():
        messages.error(request, "You cannot cancel an appointment that has already been paid. Please contact the salon.")
        return redirect('my_appointments')

    if appt.status == "CANCELLED":
        messages.info(request, "This appointment is already cancelled.")
        return redirect('my_appointments')

    # don’t allow cancelling within 2 hours of start
    appt_dt = timezone.make_aware(datetime.combine(appt.date, appt.time))
    now = timezone.now()
    if appt_dt - now <= timedelta(hours=2):
        messages.warning(request, "❌ You can’t cancel within 2 hours of your appointment.")
        return redirect('my_appointments')

    # perform cancel
    appt.status = "CANCELLED"
    appt.cancelled_at = now
    appt.save()

    try:
        send_mail(
            subject=" Appointment Cancelled – SalonSync",
            message=(
                f"Hi {appt.name},\n\n"
                f"Your appointment for {appt.get_service_display()} on {appt.date} at {appt.time} "
                f"has been cancelled.\n\n"
                "If this was a mistake, please contact us to rebook.\n\n"
                "— Team SalonSync"
            ),
            from_email=None,
            recipient_list=[appt.email],
            fail_silently=False,
        )
        messages.success(request, "✅ Appointment cancelled. A confirmation email has been sent.")
    except Exception as e:
        print("Email error:", e)
        messages.warning(request, "Appointment cancelled, but email could not be sent.")

    return redirect('my_appointments')



@csrf_protect
@login_required
def reactivate_appointment(request, pk):
    # staff can reactivate any; users only their own
    appt = get_object_or_404(
        Appointment,
        pk=pk,
        **({} if request.user.is_staff else {"user": request.user})
    )

    if request.method != "POST":
        return redirect('my_appointments')

    if appt.status != "CANCELLED":
        messages.info(request, "This appointment is already active.")
        return redirect('my_appointments')

    now = timezone.now()
    appt_dt = timezone.make_aware(datetime.combine(appt.date, appt.time))

    # Do not allow re-activation after the appointment start time
    if now >= appt_dt:
        messages.warning(request, "❌ You can’t re-activate an appointment that has already started.")
        return redirect('my_appointments')

    allowed = False
    if request.user.is_staff:
        allowed = True
    else:
        # Owner can undo only within 1 hour of cancelling
        if appt.cancelled_at and (now - appt.cancelled_at) <= timedelta(hours=1):
            allowed = True

    if not allowed:
        messages.error(request, "⏳ You can only undo a cancel within 1 hour. Please contact the salon.")
        return redirect('my_appointments')

    # Reactivate
    appt.status = "PENDING"      # or "CONFIRMED"
    appt.cancelled_at = None
    appt.save()

    try:
        send_mail(
            subject="✅ Appointment Re-Activated – SalonSync",
            message=(
                f"Hi {appt.name},\n\n"
                f"Your appointment for {appt.get_service_display()} on {appt.date} at {appt.time} "
                f"has been re-activated successfully.\n\n"
                "We’re happy to see you back! 💖\n\n"
                "— Team SalonSync"
            ),
            from_email=None,
            recipient_list=[appt.email],
            fail_silently=False,
        )
        messages.success(request, "✅ Appointment reactivated and confirmation email sent.")
    except Exception as e:
        print("Email error:", e)
        messages.success(request, "✅ Appointment reactivated, but email could not be sent.")

    return redirect('my_appointments')


@login_required
def check_available_slots(request):
    date_str = request.GET.get("date")
    total_minutes = int(request.GET.get("duration", 0))

    if not date_str or total_minutes == 0:
        return JsonResponse({"error": "Missing date or duration"}, status=400)

    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Fetch all bookings for that day
    day_appts = Appointment.objects.filter(date=selected_date).order_by("time")

    # Convert to ranges (start_time, end_time)
    booked_ranges = []
    for appt in day_appts:
        start_dt = datetime.combine(selected_date, appt.time)
        end_dt = start_dt + timedelta(minutes=appt.total_minutes)
        booked_ranges.append((start_dt, end_dt))

    # Generate possible start time slots
    all_slots = generate_slots()

    free_slots = []

    for slot in all_slots:
        slot_start = datetime.combine(selected_date, slot)
        slot_end = slot_start + timedelta(minutes=total_minutes)

        # Check if slot fits BEFORE 6 PM
        if slot_end.time() > time(18, 0):
            continue

        # Check overlap with existing appointments
        overlap = False
        for b_start, b_end in booked_ranges:
            if not (slot_end <= b_start or slot_start >= b_end):
                overlap = True
                break

        if not overlap:
            free_slots.append(slot.strftime("%H:%M"))

    return JsonResponse({"slots": free_slots})

def ensure_default_coupons():
    """
    Create clean, valid default coupons for the salon.
    Automatically runs only once per coupon.
    """

    defaults = [
        {"code": "NEW10",   "discount": 10, "minimum_amount": 30},
        {"code": "GLOW5",   "discount": 5,  "minimum_amount": 20},
        {"code": "LOYAL20", "discount": 20, "minimum_amount": 30},
    ]

    for c in defaults:
        Coupon.objects.get_or_create(
            code=c["code"],
            defaults={
                "discount": c["discount"],
                "minimum_amount": c["minimum_amount"],
                "active": True,
            }
        )



def is_loyal_customer(user):
    total_spent = Appointment.objects.filter(
        user=user,
        status="CONFIRMED"
    ).aggregate(total=models.Sum("total_cost"))["total"] or 0

    return total_spent >= 200   # your threshold

@login_required
def choose_payment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)

    if appt.status == "CANCELLED":
        messages.error(request, "You cannot pay for a cancelled appointment.")
        return redirect('my_appointments')

    if Payment.objects.filter(appointment=appt, status="SUCCESS").exists():
        messages.info(request, "Payment is already completed for this appointment.")
        return redirect('my_appointments')

    return render(request, "salon/payment_method.html", {"appointment": appt})


@csrf_protect
@login_required
def qr_payment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)

    # Create transaction ID
    tx_id = str(uuid.uuid4())

    # Data encoded in QR
    qr_data = f"""
SalonSync Payment
User: {request.user.username}
Appointment ID: {appt.id}
Amount: €{appt.total_cost}
Transaction ID: {tx_id}
    """

    # Make QR image
    img = qrcode.make(qr_data)

    # Path to save
    qr_path = os.path.join(settings.MEDIA_ROOT, f"qr_{tx_id}.png")
    img.save(qr_path)

    # Create a pending payment record
    Payment.objects.create(
        user=request.user,
        appointment=appt,
        amount=appt.total_cost,
        method="QR",
        status="PENDING",
        transaction_id=tx_id
    )

    qr_url = settings.MEDIA_URL + f"qr_{tx_id}.png"

    return render(request, "salon/qr_payment.html", {
        "qr_url": qr_url,
        "appointment": appt,
        "transaction_id": tx_id
    })

@csrf_protect
@login_required
def payment_success(request, tx_id):
    payment = get_object_or_404(Payment, transaction_id=tx_id, user=request.user)

    # mark payment success
    payment.status = "SUCCESS"
    payment.save()

    # 🔄 NEW: confirm appointment (unless it was cancelled somehow)
    appt = payment.appointment
    if appt.status != "CANCELLED":
        appt.status = "CONFIRMED"
        appt.save()

    messages.success(request, "💖 Payment Successful!")
    return render(request, "salon/payment_success.html", {"payment": payment})


@login_required
def payment_page(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)

    if appt.status == "CANCELLED":
        messages.error(request, "You cannot pay for a cancelled appointment.")
        return redirect('my_appointments')

    decoded_services = json.loads(appt.selected_services or "[]")
    subtotal = appt.total_cost
    tax_rate = 0
    tax_amount = 0
    grand_total = subtotal + tax_amount

    return render(request, "salon/payment_page.html", {
        "appointment": appt,
        "services": decoded_services,
        "grand_total": grand_total,
    })


@login_required
def payment_qr(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)
    
    total = appt.total_cost    
    upi_url = f"upi://pay?pa=YOUR_UPI_ID@oksbi&pn=SalonSync&am={total}&cu=EUR"

    qr = qrcode.make(upi_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")

@csrf_protect
@login_required
def card_payment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)

    if request.method == "POST":
        tx_id = str(uuid.uuid4())

        Payment.objects.create(
            user=request.user,
            appointment=appt,
            amount=appt.total_cost,
            method="CARD",
            status="SUCCESS",
            transaction_id=tx_id
        )

        appt.status = "CONFIRMED"
        appt.save()

        return redirect("payment_success", tx_id=tx_id)

    return render(request, "salon/card_payment.html", {"appointment": appt})

@csrf_protect
@login_required
def cash_payment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)

    tx_id = str(uuid.uuid4())

    Payment.objects.create(
        user=request.user,
        appointment=appt,
        amount=appt.total_cost,
        method="CASH",
        status="SUCCESS",
        transaction_id=tx_id
    )

    appt.status = "CONFIRMED"
    appt.save()

    messages.success(request, "💵 Payment will be collected at salon. Your booking is confirmed.")
    return redirect("payment_success", tx_id=tx_id)



