from django.urls import path
from .views import (
    DoctorListView, 
    DoctorDetailView, 
    doctor_availability,
    AppointmentListView, 
    AppointmentDetailView
)

urlpatterns = [
    # Doctor endpoints
    path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('doctors/<int:doctor_id>/availability/', doctor_availability, name='doctor-availability'),
    
    # Appointment endpoints
    path('', AppointmentListView.as_view(), name='appointment-list'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),
]

