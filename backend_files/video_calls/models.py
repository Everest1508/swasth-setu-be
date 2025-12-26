from django.db import models
from django.conf import settings
from appointments.models import Appointment
import uuid


class VideoCallRoom(models.Model):
    """Video call room for appointments"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.OneToOneField(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='video_call_room'
    )
    room_name = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='scheduled'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Room: {self.room_name} - {self.appointment}"

    def save(self, *args, **kwargs):
        if not self.room_name:
            self.room_name = f"room_{self.appointment.id}_{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)


class CallParticipant(models.Model):
    """Track participants in video calls"""
    room = models.ForeignKey(
        VideoCallRoom, 
        on_delete=models.CASCADE, 
        related_name='participants'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['room', 'user']
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.room.room_name}"

