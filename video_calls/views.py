from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from .models import VideoCallRoom, CallParticipant
from appointments.models import Appointment
from .serializers import (
    VideoCallRoomSerializer, 
    VideoCallRoomCreateSerializer,
    CallParticipantSerializer
)
from .zego_token import generate_token04
import uuid
import logging

logger = logging.getLogger(__name__)


class VideoCallRoomCreateView(generics.CreateAPIView):
    """Create a video call room for an appointment"""
    serializer_class = VideoCallRoomCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        appointment = serializer.validated_data['appointment']
        
        # Verify user has access to this appointment
        if appointment.patient != self.request.user and appointment.doctor.user != self.request.user:
            raise PermissionError("You don't have access to this appointment")
        
        # Check if room already exists
        if hasattr(appointment, 'video_call_room'):
            raise ValueError("Room already exists for this appointment")
        
        room_name = f"room_{appointment.id}_{uuid.uuid4().hex[:8]}"
        room = serializer.save(room_name=room_name)
        return room

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_room_by_appointment(request, appointment_id):
    """Get or create video call room for an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Verify user has access
    is_patient = appointment.patient == request.user
    is_doctor = appointment.doctor.user == request.user
    
    logger.info(
        f"get_room_by_appointment: appointment_id={appointment_id}, "
        f"user={request.user.username}, is_patient={is_patient}, is_doctor={is_doctor}, "
        f"appointment.patient={appointment.patient.username if appointment.patient else None}, "
        f"appointment.doctor.user={appointment.doctor.user.username if appointment.doctor else None}"
    )
    
    if not is_patient and not is_doctor:
        logger.warning(
            f"Access denied for user {request.user.username} to appointment {appointment_id}"
        )
        return Response(
            {'error': 'Access denied. You must be either the patient or doctor for this appointment.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create room
    room, created = VideoCallRoom.objects.get_or_create(
        appointment=appointment,
        defaults={'room_name': f"room_{appointment.id}_{uuid.uuid4().hex[:8]}"}
    )
    
    logger.info(
        f"Room {'created' if created else 'retrieved'}: room_id={room.id}, "
        f"appointment_id={appointment_id}"
    )
    
    serializer = VideoCallRoomSerializer(room)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_room_details(request, room_id):
    """Get video call room details"""
    room = get_object_or_404(VideoCallRoom, id=room_id)
    appointment = room.appointment
    
    # Verify user has access
    if appointment.patient != request.user and appointment.doctor.user != request.user:
        return Response(
            {'error': 'Access denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = VideoCallRoomSerializer(room)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_room(request, room_id):
    """Join a video call room"""
    from notifications.models import Notification
    
    room = get_object_or_404(VideoCallRoom, id=room_id)
    appointment = room.appointment
    
    # Verify user has access
    if appointment.patient != request.user and appointment.doctor.user != request.user:
        return Response(
            {'error': 'Access denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Create or update participant
    participant, created = CallParticipant.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={'is_active': True}
    )
    
    if not created:
        participant.is_active = True
        participant.joined_at = timezone.now()
        participant.left_at = None
        participant.save()
    
    # Check if room was just activated (first person joining)
    was_scheduled = room.status == 'scheduled'
    
    # Update room status
    if was_scheduled:
        room.status = 'active'
        if not room.started_at:
            room.started_at = timezone.now()
        room.save()
    
    # Notify the other participant that someone joined the call
    # Only notify if:
    # 1. Room was just activated (first person joining), OR
    # 2. This is a new participant joining an active call
    other_user = appointment.doctor.user if appointment.patient == request.user else appointment.patient
    caller_name = request.user.get_full_name() or request.user.username
    
    # Check if other user is already in the call
    other_user_in_call = CallParticipant.objects.filter(
        room=room, 
        user=other_user, 
        is_active=True
    ).exists()
    
    # Only notify if room was just activated and other user is not already in call
    if was_scheduled and not other_user_in_call:
        Notification.objects.create(
            user=other_user,
            title='Incoming Video Call',
            message=f'{caller_name} is calling you for your appointment. Tap to join the call.',
            notification_type='video_call',
            related_appointment=appointment,
        )
    
    serializer = VideoCallRoomSerializer(room)
    return Response({
        'room': serializer.data,
        'message': 'Joined room successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_room(request, room_id):
    """Leave a video call room"""
    from wallets.models import Wallet, Transaction
    
    room = get_object_or_404(VideoCallRoom, id=room_id)
    participant = get_object_or_404(CallParticipant, room=room, user=request.user)
    
    # Mark participant as inactive
    participant.is_active = False
    participant.left_at = timezone.now()
    participant.save()
    
    # Check if all participants left
    active_participants = CallParticipant.objects.filter(
        room=room, 
        is_active=True
    ).count()
    
    payment_required = False
    payment_message = None
    
    if active_participants == 0 and room.status == 'active':
        room.status = 'ended'
        room.ended_at = timezone.now()
        if room.started_at:
            duration = (room.ended_at - room.started_at).total_seconds()
            room.duration = int(duration)
        room.save()
        
        # Check if payment is required (patient needs to pay doctor)
        appointment = room.appointment
        if appointment and appointment.appointment_type == 'video':
            # Check if payment already exists
            if not appointment.transactions.filter(status='completed').exists():
                payment_required = True
                payment_message = f"Payment of ₹{appointment.doctor.fee} is required for this consultation."
    
    return Response({
        'message': 'Left room successfully',
        'room_status': room.status,
        'payment_required': payment_required,
        'payment_message': payment_message,
        'appointment_id': room.appointment.id if room.appointment else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_zego_token(request):
    """Generate a ZEGOCLOUD authentication token for the current user"""
    zego_app_id = getattr(settings, 'ZEGO_APP_ID', None)
    zego_server_secret = getattr(settings, 'ZEGO_SERVER_SECRET', None)
    
    if not zego_app_id or not zego_server_secret:
        return Response(
            {'error': 'Zego configuration is missing on the server'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Sanitize user ID for Zego (only alphanumeric and underscores)
    import re
    raw_user_id = request.user.email or request.user.username
    user_id = re.sub(r'[^a-zA-Z0-9_]', '_', raw_user_id)
    
    try:
        token = generate_token04(
            app_id=zego_app_id,
            user_id=user_id,
            server_secret=zego_server_secret,
            effective_time_in_seconds=3600,  # 1 hour
        )
        
        logger.info(f"Generated Zego token for user: {user_id}")
        
        return Response({
            'token': token,
            'user_id': user_id,
            'expires_in': 3600,
        })
    except Exception as e:
        logger.error(f"Failed to generate Zego token: {e}")
        return Response(
            {'error': f'Failed to generate token: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

