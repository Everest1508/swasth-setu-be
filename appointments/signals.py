from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Appointment
from .google_calendar_service import get_calendar_service
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Appointment)
def create_google_calendar_event(sender, instance, created, **kwargs):
    """
    Create Google Calendar event with Meet link when a video appointment is created
    """
    # Only create calendar events for video appointments
    if instance.appointment_type != 'video':
        return
    
    # Only create if it's a new appointment and doesn't already have a calendar event
    if created and not instance.google_calendar_event_id:
        try:
            calendar_service = get_calendar_service()
            if calendar_service and calendar_service.service:
                result = calendar_service.create_calendar_event(instance)
                if result:
                    # Update appointment with calendar event info
                    instance.google_calendar_event_id = result.get('event_id')
                    instance.google_meet_link = result.get('meet_link')
                    # Save without triggering signals again
                    Appointment.objects.filter(pk=instance.pk).update(
                        google_calendar_event_id=result.get('event_id'),
                        google_meet_link=result.get('meet_link')
                    )
                    logger.info(f"Google Calendar event created for appointment {instance.id}")
            else:
                logger.warning("Google Calendar service not available. Skipping calendar event creation.")
        except Exception as e:
            # Log error but don't fail the appointment creation
            error_msg = str(e)
            if 'accessNotConfigured' in error_msg or 'API has not been used' in error_msg:
                logger.error(f"Google Calendar API not enabled. Please enable it at: https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview?project=470410220262")
            else:
                logger.error(f"Error creating Google Calendar event: {error_msg}")
            # Appointment is still created successfully, just without calendar event
    
    # Update calendar event if appointment details changed
    elif not created and instance.google_calendar_event_id:
        # Check if date or time changed (you might want to track this more precisely)
        try:
            calendar_service = get_calendar_service()
            if calendar_service and calendar_service.service:
                calendar_service.update_calendar_event(instance)
                logger.info(f"Google Calendar event updated for appointment {instance.id}")
        except Exception as e:
            logger.error(f"Error updating Google Calendar event: {str(e)}")


@receiver(pre_delete, sender=Appointment)
def delete_google_calendar_event(sender, instance, **kwargs):
    """
    Delete Google Calendar event when appointment is cancelled/deleted
    """
    if instance.google_calendar_event_id:
        try:
            calendar_service = get_calendar_service()
            if calendar_service and calendar_service.service:
                calendar_service.delete_calendar_event(instance)
                logger.info(f"Google Calendar event deleted for appointment {instance.id}")
        except Exception as e:
            logger.error(f"Error deleting Google Calendar event: {str(e)}")

