from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import VideoCallRoom, CallParticipant
from appointments.models import Appointment
from .serializers import (
    VideoCallRoomSerializer, 
    VideoCallRoomCreateSerializer,
    CallParticipantSerializer
)
import uuid


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
    if appointment.patient != request.user and appointment.doctor.user != request.user:
        return Response(
            {'error': 'Access denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create room
    room, created = VideoCallRoom.objects.get_or_create(
        appointment=appointment,
        defaults={'room_name': f"room_{appointment.id}_{uuid.uuid4().hex[:8]}"}
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
    
    # Update room status
    if room.status == 'scheduled':
        room.status = 'active'
        if not room.started_at:
            room.started_at = timezone.now()
        room.save()
    
    serializer = VideoCallRoomSerializer(room)
    return Response({
        'room': serializer.data,
        'message': 'Joined room successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_room(request, room_id):
    """Leave a video call room"""
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
    
    if active_participants == 0 and room.status == 'active':
        room.status = 'ended'
        room.ended_at = timezone.now()
        if room.started_at:
            duration = (room.ended_at - room.started_at).total_seconds()
            room.duration = int(duration)
        room.save()
    
    return Response({
        'message': 'Left room successfully',
        'room_status': room.status
    })

