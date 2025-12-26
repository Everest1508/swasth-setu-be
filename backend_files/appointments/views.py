from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.db.models import Q
from .models import Doctor, Appointment
from .serializers import (
    DoctorSerializer, 
    AppointmentSerializer, 
    AppointmentCreateSerializer
)


class DoctorListView(generics.ListAPIView):
    """List all available doctors with optional filtering"""
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Doctor.objects.filter(available=True)
        
        # Filter by specialty
        specialty = self.request.query_params.get('specialty', None)
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
        
        # Filter by available status
        available = self.request.query_params.get('available', None)
        if available is not None:
            queryset = queryset.filter(available=available.lower() == 'true')
        
        return queryset.select_related('user')


class DoctorDetailView(generics.RetrieveAPIView):
    """Get doctor details"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_availability(request, doctor_id):
    """Get doctor's available time slots for a date"""
    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    date = request.query_params.get('date', None)
    if not date:
        return Response({'error': 'Date parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get existing appointments for that date
    existing_appointments = Appointment.objects.filter(
        doctor=doctor,
        scheduled_date=date,
        status__in=['scheduled', 'confirmed']
    ).values_list('scheduled_time', flat=True)
    
    # Generate available time slots (9 AM to 6 PM, 30-minute intervals)
    from datetime import time, timedelta
    available_slots = []
    start_time = time(9, 0)
    end_time = time(18, 0)
    
    current = start_time
    while current < end_time:
        if current not in existing_appointments:
            available_slots.append(current.strftime('%H:%M'))
        # Add 30 minutes
        hour = current.hour
        minute = current.minute + 30
        if minute >= 60:
            hour += 1
            minute = 0
        current = time(hour, minute)
    
    return Response({
        'doctor_id': doctor.id,
        'date': date,
        'available_slots': available_slots
    })


class AppointmentListView(generics.ListCreateAPIView):
    """List user's appointments or create new appointment"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        # Filter by type
        type_filter = self.request.query_params.get('type', None)
        
        if user.is_doctor:
            queryset = Appointment.objects.filter(doctor__user=user)
        else:
            queryset = Appointment.objects.filter(patient=user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if type_filter:
            queryset = queryset.filter(appointment_type=type_filter)
        
        return queryset.select_related('doctor', 'doctor__user', 'patient').order_by('-scheduled_date', '-scheduled_time')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)


class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or cancel appointment"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            return Appointment.objects.filter(doctor__user=user)
        return Appointment.objects.filter(patient=user)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_status = serializer.validated_data.get('status', instance.status)
        
        # Auto-update status based on actions
        if new_status == 'completed' and instance.status != 'completed':
            instance.status = 'completed'
            instance.save()
        
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Soft delete - mark as cancelled
        instance.status = 'cancelled'
        instance.save()
        return Response({'message': 'Appointment cancelled successfully'}, status=status.HTTP_200_OK)

