from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Appointment
from .models import Coupon

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'date', 'time', 'status', 'created_at')
    list_filter = ('service', 'status', 'date')
    search_fields = ('name', 'email', 'notes')

admin.site.register(Coupon)