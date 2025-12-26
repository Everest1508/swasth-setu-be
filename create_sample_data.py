#!/usr/bin/env python
"""
Script to create sample data for testing
Run: python manage.py shell < create_sample_data.py
Or: python create_sample_data.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import User
from appointments.models import Doctor, Appointment
from django.utils import timezone
from datetime import timedelta

def create_sample_data():
    print("Creating sample data...")
    
    # Create sample doctors
    doctors_data = [
        {
            'username': 'dr_gurpreet',
            'email': 'gurpreet@example.com',
            'first_name': 'Gurpreet',
            'last_name': 'Kaur',
            'phone': '+919876543210',
            'location': 'Nabha, Punjab',
            'specialty': 'General Physician',
            'experience': 12,
            'fee': 200,
            'rating': 4.8,
        },
        {
            'username': 'dr_rajinder',
            'email': 'rajinder@example.com',
            'first_name': 'Rajinder',
            'last_name': 'Sharma',
            'phone': '+919876543211',
            'location': 'Nabha, Punjab',
            'specialty': 'Pediatrician',
            'experience': 15,
            'fee': 300,
            'rating': 4.9,
        },
        {
            'username': 'dr_manpreet',
            'email': 'manpreet@example.com',
            'first_name': 'Manpreet',
            'last_name': 'Singh',
            'phone': '+919876543212',
            'location': 'Nabha, Punjab',
            'specialty': 'Dermatologist',
            'experience': 8,
            'fee': 350,
            'rating': 4.7,
        },
    ]
    
    doctors = []
    for doc_data in doctors_data:
        user, created = User.objects.get_or_create(
            username=doc_data['username'],
            defaults={
                'email': doc_data['email'],
                'first_name': doc_data['first_name'],
                'last_name': doc_data['last_name'],
                'phone': doc_data['phone'],
                'location': doc_data['location'],
                'is_doctor': True,
            }
        )
        if created:
            user.set_password('test123')
            user.save()
        
        doctor, created = Doctor.objects.get_or_create(
            user=user,
            defaults={
                'specialty': doc_data['specialty'],
                'experience': doc_data['experience'],
                'fee': doc_data['fee'],
                'rating': doc_data['rating'],
                'available': True,
            }
        )
        doctors.append(doctor)
        print(f"✓ Doctor: {user.get_full_name()} - {doc_data['specialty']}")
    
    print(f"\nCreated {len(doctors)} doctors")
    print("\nSample data created successfully!")
    print("\nYou can now:")
    print("1. Login with any doctor account (username: dr_gurpreet, password: test123)")
    print("2. Or create a patient account via registration")
    print("3. Book appointments with the doctors")

if __name__ == '__main__':
    create_sample_data()

