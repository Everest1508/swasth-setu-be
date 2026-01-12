from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Appointment
import logging
import uuid

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Appointment)
def create_video_call_room(sender, instance, created, **kwargs):
    """
    Create Agora video call room when a video appointment is created
    """
    # Only create video call rooms for video appointments
    if instance.appointment_type != 'video':
        return
    
    # Only create if it's a new appointment
    if created:
        try:
            from video_calls.models import VideoCallRoom
            
            # Check if room already exists
            if hasattr(instance, 'video_call_room'):
                logger.info(f"Video call room already exists for appointment {instance.id}")
                return
            
            # Create video call room
            room_name = f"room_{instance.id}_{uuid.uuid4().hex[:8]}"
            VideoCallRoom.objects.create(
                appointment=instance,
                room_name=room_name,
                status='scheduled'
            )
            logger.info(f"Agora video call room created for appointment {instance.id}: {room_name}")
        except Exception as e:
            # Log error but don't fail the appointment creation
            logger.error(f"Error creating Agora video call room: {str(e)}")
            # Appointment is still created successfully, just without video call room


@receiver(pre_delete, sender=Appointment)
def delete_video_call_room(sender, instance, **kwargs):
    """
    Delete video call room when appointment is cancelled/deleted
    """
    try:
        if hasattr(instance, 'video_call_room'):
            instance.video_call_room.delete()
            logger.info(f"Video call room deleted for appointment {instance.id}")
    except Exception as e:
        logger.error(f"Error deleting video call room: {str(e)}")
