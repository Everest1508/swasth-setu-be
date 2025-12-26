from django.urls import path
from .views import (
    DoctorListView, 
    DoctorDetailView,
    DoctorProfileView,
    doctor_availability,
    AppointmentListView, 
    AppointmentDetailView,
    DoctorScheduleView,
    DoctorScheduleDetailView,
    check_symptoms
)

urlpatterns = [
    # Doctor endpoints
    path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('doctors/profile/', DoctorProfileView.as_view(), name='doctor-profile'),
    path('doctors/<int:doctor_id>/availability/', doctor_availability, name='doctor-availability'),
    
    # Doctor Schedule endpoints
    path('doctors/schedule/', DoctorScheduleView.as_view(), name='doctor-schedule'),
    path('doctors/schedule/<int:pk>/', DoctorScheduleDetailView.as_view(), name='doctor-schedule-detail'),
    
    # Appointment endpoints
    path('', AppointmentListView.as_view(), name='appointment-list'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),
    
    # Symptom checker endpoint
    path('symptom-checker/', check_symptoms, name='symptom-checker'),
]

