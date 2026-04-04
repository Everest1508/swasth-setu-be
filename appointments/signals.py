from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Appointment)
def ensure_jitsi_link_for_video_appointment(sender, instance, **kwargs):
    """Assign a Jitsi Meet URL to video appointments when missing (create or legacy rows)."""
    if instance.appointment_type != "video":
        return
    if instance.google_meet_link:
        return
    try:
        from .jitsi import create_jitsi_meeting_link

        instance.google_meet_link = create_jitsi_meeting_link()
        instance.save(update_fields=["google_meet_link"])
        logger.info("Set Jitsi link for video appointment %s", instance.pk)
    except Exception as e:
        logger.error("Could not set Jitsi link for appointment %s: %s", instance.pk, e)
