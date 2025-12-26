from django.db import models
from django.conf import settings


class Doctor(models.Model):
    """Doctor profile model"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='doctor_profile'
    )
    specialty = models.CharField(max_length=100)
    experience = models.IntegerField(default=0, help_text="Years of experience")
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    reviews_count = models.IntegerField(default=0)
    bio = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    # Location fields for in-person appointments
    clinic_address = models.TextField(blank=True, help_text="Clinic or practice address")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Clinic latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Clinic longitude")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rating', '-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.specialty}"

    @property
    def name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email


class DoctorSchedule(models.Model):
    """Doctor's weekly schedule/availability"""
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['doctor', 'day_of_week']
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_day_of_week_display()} ({self.start_time} - {self.end_time})"


class Appointment(models.Model):
    """Appointment model"""
    APPOINTMENT_TYPE_CHOICES = [
        ('video', 'Video Consultation'),
        ('in_person', 'In-Person Visit'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='patient_appointments'
    )
    doctor = models.ForeignKey(
        Doctor, 
        on_delete=models.CASCADE, 
        related_name='appointments'
    )
    appointment_type = models.CharField(
        max_length=20, 
        choices=APPOINTMENT_TYPE_CHOICES, 
        default='video'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='scheduled'
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Notes added by patient")
    prescription = models.TextField(blank=True, help_text="Prescription added by doctor")
    google_meet_link = models.URLField(blank=True, null=True, help_text="Google Meet link for video consultations")
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Calendar event ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['scheduled_date', 'scheduled_time']),
            models.Index(fields=['doctor', 'scheduled_date', 'scheduled_time']),
        ]

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.user.get_full_name()} - {self.scheduled_date}"

    def check_overlap(self):
        """Check if this appointment overlaps with existing appointments"""
        from datetime import datetime, timedelta
        
        # Calculate appointment end time (assuming 30 min duration)
        scheduled_datetime = datetime.combine(self.scheduled_date, self.scheduled_time)
        appointment_end = scheduled_datetime + timedelta(minutes=30)
        appointment_end_time = appointment_end.time()
        
        # Check for overlapping appointments for the same doctor
        existing_doctor_appts = Appointment.objects.filter(
            doctor=self.doctor,
            scheduled_date=self.scheduled_date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        ).exclude(id=self.id if self.id else None)
        
        overlapping_doctor = False
        for apt in existing_doctor_appts:
            apt_datetime = datetime.combine(apt.scheduled_date, apt.scheduled_time)
            apt_end = apt_datetime + timedelta(minutes=30)
            apt_end_time = apt_end.time()
            
            # Check if times overlap
            if not (appointment_end_time <= apt.scheduled_time or self.scheduled_time >= apt_end_time):
                overlapping_doctor = True
                break
        
        # Check for overlapping appointments for the same patient
        existing_patient_appts = Appointment.objects.filter(
            patient=self.patient,
            scheduled_date=self.scheduled_date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        ).exclude(id=self.id if self.id else None)
        
        overlapping_patient = False
        for apt in existing_patient_appts:
            apt_datetime = datetime.combine(apt.scheduled_date, apt.scheduled_time)
            apt_end = apt_datetime + timedelta(minutes=30)
            apt_end_time = apt_end.time()
            
            # Check if times overlap
            if not (appointment_end_time <= apt.scheduled_time or self.scheduled_time >= apt_end_time):
                overlapping_patient = True
                break
        
        return overlapping_doctor or overlapping_patient
