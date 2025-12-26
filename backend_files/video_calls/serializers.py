from rest_framework import serializers
from .models import VideoCallRoom, CallParticipant
from appointments.serializers import AppointmentSerializer


class CallParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = CallParticipant
        fields = ('id', 'user_id', 'user_name', 'joined_at', 'left_at', 'is_active')

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class VideoCallRoomSerializer(serializers.ModelSerializer):
    appointment = AppointmentSerializer(read_only=True)
    participants = CallParticipantSerializer(many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoCallRoom
        fields = ('id', 'room_name', 'appointment', 'status', 'started_at', 
                  'ended_at', 'duration', 'participants', 'participant_count', 
                  'created_at', 'updated_at')

    def get_participant_count(self, obj):
        return obj.participants.filter(is_active=True).count()


class VideoCallRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCallRoom
        fields = ('appointment',)

