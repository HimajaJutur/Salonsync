# salon/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from datetime import date
from .models import Appointment   # ✅ import your Appointment model

# ---------------------------
# 1️⃣ User Registration Form
# ---------------------------
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email Address")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


# ---------------------------
# 2️⃣ Appointment Booking Form
# ---------------------------
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'time', 'notes']
        widgets = {
            
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure these fields are not required
        self.fields['date'].required = True
        # Other model fields (name, email, service) won't be shown and will be filled automatically
        
    def clean_date(self):
        """Ensure date is not in the past."""
        d = self.cleaned_data['date']
        if d < date.today():
            raise forms.ValidationError("Please choose a future date.")
        return d
