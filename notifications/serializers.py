from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()
    related_appointment_id = serializers.IntegerField(
        source='related_appointment.id',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'message', 'notification_type',
            'is_read', 'read_at', 'related_appointment_id',
            'created_at', 'updated_at', 'time_ago'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'read_at')

    def get_time_ago(self, obj):
        """Calculate time ago string"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} hour{"s" if hours > 1 else ""} ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days} day{"s" if days > 1 else ""} ago'
        elif diff < timedelta(days=30):
            weeks = diff.days // 7
            return f'{weeks} week{"s" if weeks > 1 else ""} ago'
        else:
            months = diff.days // 30
            return f'{months} month{"s" if months > 1 else ""} ago'


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification (mark as read)"""
    class Meta:
        model = Notification
        fields = ('is_read',)

