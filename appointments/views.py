from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.db.models import Q
from .models import Doctor, Appointment, DoctorSchedule, HealthRecord
from .serializers import (
    DoctorSerializer, 
    AppointmentSerializer, 
    AppointmentCreateSerializer,
    AppointmentUpdateSerializer,
    DoctorScheduleSerializer,
    HealthRecordSerializer,
    HealthRecordCreateSerializer
)
from .models import DoctorSchedule
from .symptom_checker import SymptomCheckerService


class DoctorListView(generics.ListAPIView):
    """List all available doctors with optional filtering"""
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Start with all doctors, not just available ones
        # The 'available' filter can be applied via query param
        queryset = Doctor.objects.all()
        
        # Search query - search in name, specialty, and bio
        search_query = self.request.query_params.get('search', None)
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(specialty__icontains=search_query) |
                Q(bio__icontains=search_query)
            )
        
        # Filter by specialty
        specialty = self.request.query_params.get('specialty', None)
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
        
        # Filter by available status
        available = self.request.query_params.get('available', None)
        if available is not None:
            queryset = queryset.filter(available=available.lower() == 'true')
        # If no 'available' param, show all doctors (not just available ones)
        # This allows frontend to show all doctors and filter client-side if needed
        
        return queryset.select_related('user').order_by('-rating', '-created_at')


class DoctorDetailView(generics.RetrieveAPIView):
    """Get doctor details"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]


class DoctorProfileView(generics.RetrieveUpdateAPIView):
    """Get or update doctor's own profile"""
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if not user.is_doctor:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only doctors can access this endpoint")
        
        doctor, created = Doctor.objects.get_or_create(user=user)
        return doctor


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_availability(request, doctor_id):
    """Get doctor's available time slots for a date based on their schedule"""
    from datetime import datetime, time, timedelta
    
    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    date_str = request.query_params.get('date', None)
    if not date_str:
        return Response({'error': 'Date parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get doctor's schedule for that day of week
    day_of_week = date.weekday()
    schedule = DoctorSchedule.objects.filter(
        doctor=doctor,
        day_of_week=day_of_week,
        is_available=True
    ).first()
    
    if not schedule:
        return Response({
            'doctor_id': doctor.id,
            'date': date_str,
            'available_slots': [],
            'message': f'Doctor is not available on {date.strftime("%A")}'
        })
    
    # Get existing appointments for that date
    existing_appointments = Appointment.objects.filter(
        doctor=doctor,
        scheduled_date=date,
        status__in=['scheduled', 'confirmed', 'in_progress']
    ).values_list('scheduled_time', flat=True)
    
    # Generate available time slots based on schedule (30-minute intervals)
    available_slots = []
    current = schedule.start_time
    
    while current < schedule.end_time:
        # Check if this slot is already booked
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
        'date': date_str,
        'available_slots': available_slots,
        'schedule': {
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M')
        }
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            return Appointment.objects.filter(doctor__user=user)
        return Appointment.objects.filter(patient=user)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AppointmentUpdateSerializer
        return AppointmentSerializer

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


class DoctorScheduleView(generics.ListCreateAPIView):
    """Get or create doctor's schedule"""
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_doctor:
            return DoctorSchedule.objects.none()
        
        doctor = user.doctor_profile
        return DoctorSchedule.objects.filter(doctor=doctor)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_doctor:
            raise PermissionError("Only doctors can create schedules")
        doctor = user.doctor_profile
        serializer.save(doctor=doctor)


class DoctorScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a schedule entry"""
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_doctor:
            return DoctorSchedule.objects.none()
        doctor = user.doctor_profile
        return DoctorSchedule.objects.filter(doctor=doctor)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_symptoms(request):
    """
    Analyze symptoms using Groq API
    Expects: {'symptoms': str, 'groq_api_key': str}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log received data for debugging
    logger.info(f"Received data: {request.data}")
    logger.info(f"Data type: {type(request.data)}")
    
    # Handle both dict and QueryDict
    if hasattr(request.data, 'get'):
        symptoms = request.data.get('symptoms', '')
        groq_api_key = request.data.get('groq_api_key', '')
    else:
        symptoms = str(request.data.get('symptoms', '')) if isinstance(request.data, dict) else ''
        groq_api_key = str(request.data.get('groq_api_key', '')) if isinstance(request.data, dict) else ''
    
    # Strip whitespace
    symptoms = str(symptoms).strip() if symptoms else ''
    groq_api_key = str(groq_api_key).strip() if groq_api_key else ''
    
    logger.info(f"Parsed - symptoms length: {len(symptoms)}, groq_key length: {len(groq_api_key)}")
    
    if not symptoms:
        logger.warning("Symptoms description is missing")
        return Response(
            {'error': 'Symptoms description is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not groq_api_key:
        logger.warning("Groq API key is missing")
        return Response(
            {'error': 'Groq API key is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = SymptomCheckerService.analyze_symptoms(symptoms, groq_api_key)
    
    if 'error' in result:
        logger.error(f"Error from symptom checker: {result.get('error')}")
        return Response(
            result,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logger.info("Symptom analysis successful")
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search(request):
    """
    Universal search endpoint
    Searches across doctors, and optionally other entities
    Query params:
    - q: search query (required)
    - type: 'doctor', 'pharmacist', or 'all' (default: 'all')
    """
    search_query = request.query_params.get('q', '').strip()
    search_type = request.query_params.get('type', 'all').lower()
    
    if not search_query:
        return Response(
            {'error': 'Search query (q) is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    results = {
        'query': search_query,
        'doctors': [],
        'pharmacists': [],
    }
    
    # Search doctors
    if search_type in ['all', 'doctor', 'doctors']:
        doctors = Doctor.objects.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(specialty__icontains=search_query) |
            Q(bio__icontains=search_query)
        ).select_related('user').order_by('-rating', '-created_at')[:20]  # Limit to 20 results
        
        results['doctors'] = DoctorSerializer(doctors, many=True, context={'request': request}).data
    
    # Search pharmacists
    if search_type in ['all', 'pharmacist', 'pharmacists']:
        from pharmacy.models import Pharmacist
        from pharmacy.serializers import PharmacistSerializer
        
        pharmacists = Pharmacist.objects.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(store_name__icontains=search_query) |
            Q(store_address__icontains=search_query)
        ).filter(is_active=True).select_related('user').order_by('store_name')[:20]  # Limit to 20 results
        
        results['pharmacists'] = PharmacistSerializer(pharmacists, many=True, context={'request': request}).data
    
    return Response(results, status=status.HTTP_200_OK)


class HealthRecordListView(generics.ListCreateAPIView):
    """List or create health records"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient', None)
        if patient_id:
            # Doctors can view any patient's records, patients can only view their own
            if user.is_doctor:
                queryset = HealthRecord.objects.filter(patient_id=patient_id)
            else:
                queryset = HealthRecord.objects.filter(patient=user, patient_id=patient_id)
        else:
            # If no patient filter, show current user's records
            queryset = HealthRecord.objects.filter(patient=user)
        
        # Filter by appointment
        appointment_id = self.request.query_params.get('appointment', None)
        if appointment_id:
            queryset = queryset.filter(appointment_id=appointment_id)
        
        return queryset.select_related('patient', 'appointment', 'created_by').order_by('-date', '-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return HealthRecordCreateSerializer
        return HealthRecordSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save()


class HealthRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a health record"""
    permission_classes = [IsAuthenticated]
    serializer_class = HealthRecordSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            # Doctors can view any patient's records
            return HealthRecord.objects.all()
        # Patients can only view their own records
        return HealthRecord.objects.filter(patient=user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return HealthRecordCreateSerializer
        return HealthRecordSerializer

