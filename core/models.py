from django.db import models
from django.conf import settings


class DoctorApplication(models.Model):
    """Application model for doctors to join Swasth Setu"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_applications'
    )
    specialty = models.CharField(max_length=100)
    experience = models.IntegerField(help_text="Years of experience")
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    bio = models.TextField(blank=True)
    qualification = models.CharField(max_length=255, help_text="Medical degree/qualification")
    license_number = models.CharField(max_length=100, blank=True, help_text="Medical license number")
    clinic_address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Doctor Application - {self.user.get_full_name() or self.user.username} - {self.status}"


class PharmacistApplication(models.Model):
    """Application model for pharmacists to join Swasth Setu"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pharmacist_applications'
    )
    store_name = models.CharField(max_length=200)
    store_address = models.TextField()
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    license_number = models.CharField(max_length=100, blank=True, help_text="Pharmacy license number")
    qualification = models.CharField(max_length=255, blank=True, help_text="Pharmacy degree/qualification")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pharmacist Application - {self.store_name} - {self.status}"


