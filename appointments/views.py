from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
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
import os
import json
import logging
from io import StringIO
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


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


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow guest access
def authenticate_google_calendar(request):
    """
    API endpoint to run Google Calendar authentication.
    Returns authentication status and logs.
    Accessible to anyone (no authentication required).
    """
    logs = []
    status_info = {
        'authenticated': False,
        'token_exists': False,
        'token_valid': False,
        'credentials_exist': False,
        'authorization_url': None,
        'message': '',
        'logs': []
    }
    
    # Scopes required for Google Calendar API
    SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']
    
    # Paths
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
    credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
    
    def log(message):
        """Helper to log messages"""
        logs.append(message)
        logger.info(f"Google Calendar Auth API: {message}")
    
    log("Starting Google Calendar authentication check...")
    
    # Check if credentials.json exists
    if os.path.exists(credentials_path):
        status_info['credentials_exist'] = True
        log(f"✅ Credentials file found: {credentials_path}")
    else:
        status_info['credentials_exist'] = False
        log(f"❌ Credentials file not found: {credentials_path}")
        status_info['message'] = f"Credentials file not found. Please add credentials.json to the backend directory."
        status_info['logs'] = logs
        return Response(status_info, status=status.HTTP_200_OK)
    
    # Check if token exists
    creds = None
    if os.path.exists(token_path):
        status_info['token_exists'] = True
        log(f"✅ Token file found: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            log("✅ Token file loaded successfully")
        except Exception as e:
            log(f"⚠️  Error loading token file: {str(e)}")
            creds = None
    else:
        log(f"ℹ️  Token file not found: {token_path}")
    
    # Check if credentials are valid
    if creds and creds.valid:
        status_info['token_valid'] = True
        status_info['authenticated'] = True
        log("✅ Token is valid and not expired")
        status_info['message'] = "Google Calendar is already authenticated and ready to use."
        status_info['logs'] = logs
        return Response(status_info, status=status.HTTP_200_OK)
    
    # Token is expired or invalid - try to refresh
    if creds and creds.expired and creds.refresh_token:
        log("🔄 Token expired, attempting to refresh...")
        try:
            creds.refresh(Request())
            log("✅ Token refreshed successfully")
            # Save the refreshed token
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            log(f"✅ Refreshed token saved to {token_path}")
            status_info['token_valid'] = True
            status_info['authenticated'] = True
            status_info['message'] = "Token refreshed successfully. Google Calendar is now authenticated."
            status_info['logs'] = logs
            return Response(status_info, status=status.HTTP_200_OK)
        except RefreshError as e:
            log(f"⚠️  Refresh token is invalid: {str(e)}")
            log("The token file will be deleted and you'll need to re-authenticate.")
            # Delete the invalid token file
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    log(f"✅ Removed invalid token file: {token_path}")
                    status_info['token_exists'] = False
                except Exception as delete_error:
                    log(f"⚠️  Could not remove invalid token file: {str(delete_error)}")
            creds = None
    
    # Need to authenticate - generate authorization URL
    if not creds or not creds.valid:
        log("🔐 Starting new authentication flow...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            # Generate authorization URL
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent to get refresh token
            )
            status_info['authorization_url'] = authorization_url
            log(f"✅ Authorization URL generated")
            log(f"📋 Please visit this URL to authenticate: {authorization_url}")
            status_info['message'] = (
                "Authentication required. Please visit the authorization_url in your browser, "
                "complete the OAuth flow, and then call the callback endpoint with the authorization code."
            )
        except Exception as e:
            log(f"❌ Error generating authorization URL: {str(e)}")
            status_info['message'] = f"Error generating authorization URL: {str(e)}"
    
    status_info['logs'] = logs
    return Response(status_info, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow guest access
def google_calendar_callback(request):
    """
    API endpoint to handle Google Calendar OAuth callback.
    Receives authorization code and exchanges it for tokens.
    Accessible to anyone (no authentication required).
    """
    logs = []
    status_info = {
        'success': False,
        'message': '',
        'logs': []
    }
    
    # Scopes required for Google Calendar API
    SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']
    
    # Paths
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
    credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
    
    def log(message):
        """Helper to log messages"""
        logs.append(message)
        logger.info(f"Google Calendar Callback API: {message}")
    
    log("Processing OAuth callback...")
    
    # Get authorization code from request
    authorization_code = request.data.get('code') or request.query_params.get('code')
    state = request.data.get('state') or request.query_params.get('state')
    
    if not authorization_code:
        log("❌ No authorization code provided")
        status_info['message'] = "Authorization code is required. Please provide 'code' parameter."
        status_info['logs'] = logs
        return Response(status_info, status=status.HTTP_400_BAD_REQUEST)
    
    log(f"✅ Received authorization code")
    
    # Check if credentials exist
    if not os.path.exists(credentials_path):
        log(f"❌ Credentials file not found: {credentials_path}")
        status_info['message'] = "Credentials file not found."
        status_info['logs'] = logs
        return Response(status_info, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create flow and exchange code for token
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path, SCOPES
        )
        # Exchange authorization code for credentials
        flow.fetch_token(code=authorization_code)
        creds = flow.credentials
        
        # Save the credentials
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        log(f"✅ Token saved to {token_path}")
        
        status_info['success'] = True
        status_info['message'] = "Google Calendar authentication successful! Token saved."
        log("✅ Authentication completed successfully")
        
    except Exception as e:
        log(f"❌ Error during token exchange: {str(e)}")
        status_info['message'] = f"Error during authentication: {str(e)}"
        return Response(status_info, status=status.HTTP_400_BAD_REQUEST)
    
    status_info['logs'] = logs
    return Response(status_info, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow guest access
def google_calendar_quick_access_info(request):
    """
    API endpoint to get information about Quick Access settings for Google Meet.
    Returns the organizer email and instructions on how to enable Quick Access.
    Accessible to anyone (no authentication required).
    """
    from .google_calendar_service import get_organizer_email, get_calendar_service
    
    logs = []
    info = {
        'organizer_email': None,
        'quick_access_enabled': None,
        'instructions': [],
        'logs': []
    }
    
    def log(message):
        """Helper to log messages"""
        logs.append(message)
        logger.info(f"Google Calendar Quick Access Info: {message}")
    
    log("Checking Google Calendar organizer and Quick Access settings...")
    
    try:
        # Get organizer email
        organizer_email = get_organizer_email()
        if organizer_email:
            info['organizer_email'] = organizer_email
            log(f"✅ Organizer email: {organizer_email}")
        else:
            log("⚠️  Could not determine organizer email")
            info['instructions'].append(
                "Could not determine the organizer email. Please check your Google Calendar authentication."
            )
    except Exception as e:
        log(f"❌ Error getting organizer email: {str(e)}")
        info['instructions'].append(f"Error: {str(e)}")
    
    # Add instructions
    if info['organizer_email']:
        organizer_email = info['organizer_email']
        info['instructions'].extend([
            f"The Google account '{organizer_email}' is the meeting organizer.",
            "To enable 'Quick Access' (allow direct joining without 'ask to join'):",
            "",
            "1. Go to https://meet.google.com",
            f"2. Sign in with the account: {organizer_email}",
            "3. Click on the Settings icon (gear icon) in the top right",
            "4. Scroll down to 'Quick access' section",
            "5. Toggle 'Quick access' to ON",
            "6. This will allow invited attendees to join directly without asking",
            "",
            "Alternatively, during a meeting:",
            "1. Click the shield icon at the bottom of the meeting",
            "2. Toggle 'Quick access' to ON",
            "",
            "Note: This setting applies to all meetings created by this account."
        ])
    else:
        info['instructions'].extend([
            "To enable 'Quick Access' for Google Meet:",
            "1. Go to https://meet.google.com",
            "2. Sign in with the Google account used for Calendar authentication",
            "3. Open Settings and enable 'Quick access'",
            "4. This allows invited attendees to join directly without 'ask to join'"
        ])
    
    info['logs'] = logs
    return Response(info, status=status.HTTP_200_OK)

