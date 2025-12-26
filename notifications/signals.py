from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from .models import Notification


@receiver(post_save, sender=Appointment)
def create_appointment_notifications(sender, instance, created, **kwargs):
    """Create notifications when appointment is created or updated"""
    if created:
        # Notify patient
        Notification.objects.create(
            user=instance.patient,
            title='Appointment Scheduled',
            message=f'Your appointment with Dr. {instance.doctor.user.get_full_name()} is scheduled for {instance.scheduled_date} at {instance.scheduled_time.strftime("%I:%M %p")}.',
            notification_type='appointment',
            related_appointment=instance,
        )
        
        # Notify doctor
        Notification.objects.create(
            user=instance.doctor.user,
            title='New Appointment',
            message=f'You have a new appointment with {instance.patient.get_full_name()} on {instance.scheduled_date} at {instance.scheduled_time.strftime("%I:%M %p")}.',
            notification_type='appointment',
            related_appointment=instance,
        )
    else:
        # Check if status changed
        if instance.status == 'confirmed':
            # Notify patient
            Notification.objects.create(
                user=instance.patient,
                title='Appointment Confirmed',
                message=f'Your appointment with Dr. {instance.doctor.user.get_full_name()} on {instance.scheduled_date} has been confirmed.',
                notification_type='appointment_confirmed',
                related_appointment=instance,
            )
        elif instance.status == 'cancelled':
            # Notify both parties
            Notification.objects.create(
                user=instance.patient,
                title='Appointment Cancelled',
                message=f'Your appointment with Dr. {instance.doctor.user.get_full_name()} on {instance.scheduled_date} has been cancelled.',
                notification_type='appointment_cancelled',
                related_appointment=instance,
            )
            
            Notification.objects.create(
                user=instance.doctor.user,
                title='Appointment Cancelled',
                message=f'Appointment with {instance.patient.get_full_name()} on {instance.scheduled_date} has been cancelled.',
                notification_type='appointment_cancelled',
                related_appointment=instance,
            )
        elif instance.status == 'completed':
            # Notify patient
            Notification.objects.create(
                user=instance.patient,
                title='Appointment Completed',
                message=f'Your appointment with Dr. {instance.doctor.user.get_full_name()} has been completed.',
                notification_type='appointment',
                related_appointment=instance,
            )


def create_appointment_reminders():
    """Create reminder notifications for upcoming appointments (run via cron/scheduled task)"""
    from datetime import datetime, timedelta
    
    tomorrow = timezone.now().date() + timedelta(days=1)
    upcoming_appointments = Appointment.objects.filter(
        scheduled_date=tomorrow,
        status__in=['scheduled', 'confirmed']
    )
    
    for appointment in upcoming_appointments:
        # Notify patient
        Notification.objects.create(
            user=appointment.patient,
            title='Appointment Reminder',
            message=f'Reminder: You have an appointment with Dr. {appointment.doctor.user.get_full_name()} tomorrow at {appointment.scheduled_time.strftime("%I:%M %p")}.',
            notification_type='appointment_reminder',
            related_appointment=appointment,
        )
        
        # Notify doctor
        Notification.objects.create(
            user=appointment.doctor.user,
            title='Appointment Reminder',
            message=f'Reminder: You have an appointment with {appointment.patient.get_full_name()} tomorrow at {appointment.scheduled_time.strftime("%I:%M %p")}.',
            notification_type='appointment_reminder',
            related_appointment=appointment,
        )

