from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile, name='profile'),  
    path('book_appointment/', views.book_appointment, name='book_appointment'), 
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('contact/', views.contact, name='contact'),
    path('salon-location/', views.salon_location, name='salon_location'),
    path('services/', views.services, name='services'),
    path('appointments/<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/<int:pk>/reactivate/', views.reactivate_appointment, name='reactivate_appointment'),
    path('appointments/<int:pk>/bill/', views.view_bill, name='view_bill'),
    path("appointments/check-slots/", views.check_available_slots, name="check_available_slots"),

    #path("payment/<int:pk>/", views.choose_payment, name="choose_payment"),
    path("payment/qr/<int:pk>/", views.qr_payment, name="qr_payment"),
    #path('payment/<int:pk>/', views.payment_page, name='payment'),
    path('payment/<int:pk>/', views.payment_page, name='payment_page'),
    #path('payment-qr/<int:pk>/', views.payment_qr, name='payment_qr'),
    path('choose-payment/<int:pk>/', views.choose_payment, name='choose_payment'),
    #path('payment-method/<int:pk>/', views.choose_payment, name='choose_payment'),
    #path('payment/qr/<int:pk>/', views.qr_payment, name='qr_payment'),
    path('payment/card/<int:pk>/', views.card_payment, name='card_payment'),
    path('payment/cash/<int:pk>/', views.cash_payment, name='cash_payment'),
    path('payment/success/<str:tx_id>/', views.payment_success, name='payment_success'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
