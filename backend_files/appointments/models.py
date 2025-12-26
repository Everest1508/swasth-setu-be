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
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['scheduled_date', 'scheduled_time']),
        ]

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.user.get_full_name()} - {self.scheduled_date}"

