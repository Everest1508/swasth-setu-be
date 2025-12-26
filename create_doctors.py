#!/usr/bin/env python
"""
Script to create sample doctors for testing.
Run: python manage.py shell < create_doctors.py
Or: python create_doctors.py (after setting up Django)
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import User
from appointments.models import Doctor

# Sample doctors data
DOCTORS_DATA = [
    {
        'username': 'dr_gurpreet',
        'email': 'gurpreet.kaur@ruralhealth.com',
        'first_name': 'Gurpreet',
        'last_name': 'Kaur',
        'phone': '+91 98765 43210',
        'location': 'Punjab, India',
        'specialty': 'General Physician',
        'experience': 12,
        'fee': 500.00,
        'rating': 4.8,
        'reviews_count': 245,
        'bio': 'Experienced general physician with expertise in rural healthcare. Specializes in preventive medicine and chronic disease management.',
        'available': True,
    },
    {
        'username': 'dr_rajinder',
        'email': 'rajinder.sharma@ruralhealth.com',
        'first_name': 'Rajinder',
        'last_name': 'Sharma',
        'phone': '+91 98765 43211',
        'location': 'Haryana, India',
        'specialty': 'Pediatrician',
        'experience': 15,
        'fee': 600.00,
        'rating': 4.9,
        'reviews_count': 312,
        'bio': 'Pediatric specialist with extensive experience in child healthcare. Passionate about providing quality care to children in rural areas.',
        'available': True,
    },
    {
        'username': 'dr_manpreet',
        'email': 'manpreet.singh@ruralhealth.com',
        'first_name': 'Manpreet',
        'last_name': 'Singh',
        'phone': '+91 98765 43212',
        'location': 'Punjab, India',
        'specialty': 'Dermatologist',
        'experience': 10,
        'fee': 700.00,
        'rating': 4.7,
        'reviews_count': 189,
        'bio': 'Dermatology expert specializing in skin conditions common in rural areas. Provides both in-person and video consultations.',
        'available': True,
    },
    {
        'username': 'dr_priya',
        'email': 'priya.sharma@ruralhealth.com',
        'first_name': 'Priya',
        'last_name': 'Sharma',
        'phone': '+91 98765 43213',
        'location': 'Rajasthan, India',
        'specialty': 'Gynecologist',
        'experience': 14,
        'fee': 650.00,
        'rating': 4.9,
        'reviews_count': 278,
        'bio': 'Women\'s health specialist with focus on maternal and reproductive health. Committed to serving rural communities.',
        'available': True,
    },
    {
        'username': 'dr_amit',
        'email': 'amit.kumar@ruralhealth.com',
        'first_name': 'Amit',
        'last_name': 'Kumar',
        'phone': '+91 98765 43214',
        'location': 'Uttar Pradesh, India',
        'specialty': 'Cardiologist',
        'experience': 18,
        'fee': 800.00,
        'rating': 4.8,
        'reviews_count': 156,
        'bio': 'Cardiologist with expertise in heart health. Provides comprehensive cardiac care through telemedicine.',
        'available': True,
    },
]


def create_doctors():
    """Create sample doctors"""
    created_count = 0
    updated_count = 0
    
    for doctor_data in DOCTORS_DATA:
        user_data = {
            'username': doctor_data['username'],
            'email': doctor_data['email'],
            'first_name': doctor_data['first_name'],
            'last_name': doctor_data['last_name'],
            'phone': doctor_data['phone'],
            'location': doctor_data['location'],
            'is_doctor': True,
        }
        
        # Create or get user
        user, created = User.objects.get_or_create(
            username=doctor_data['username'],
            defaults=user_data
        )
        
        if not created:
            # Update existing user
            for key, value in user_data.items():
                setattr(user, key, value)
            user.save()
            updated_count += 1
        else:
            # Set password for new user
            user.set_password('doctor123')  # Default password
            user.save()
            created_count += 1
        
        # Create or update doctor profile
        doctor_profile, doc_created = Doctor.objects.get_or_create(
            user=user,
            defaults={
                'specialty': doctor_data['specialty'],
                'experience': doctor_data['experience'],
                'fee': doctor_data['fee'],
                'rating': doctor_data['rating'],
                'reviews_count': doctor_data['reviews_count'],
                'bio': doctor_data['bio'],
                'available': doctor_data['available'],
            }
        )
        
        if not doc_created:
            # Update existing doctor profile
            doctor_profile.specialty = doctor_data['specialty']
            doctor_profile.experience = doctor_data['experience']
            doctor_profile.fee = doctor_data['fee']
            doctor_profile.rating = doctor_data['rating']
            doctor_profile.reviews_count = doctor_data['reviews_count']
            doctor_profile.bio = doctor_data['bio']
            doctor_profile.available = doctor_data['available']
            doctor_profile.save()
        
        print(f"{'Created' if created else 'Updated'}: Dr. {doctor_data['first_name']} {doctor_data['last_name']} - {doctor_data['specialty']}")
    
    print(f"\n✅ Summary:")
    print(f"   - Created: {created_count} new doctors")
    print(f"   - Updated: {updated_count} existing doctors")
    print(f"   - Total: {len(DOCTORS_DATA)} doctors")
    print(f"\n📝 Default password for all doctors: doctor123")
    print(f"   Doctors can login with their username/email and this password.")


if __name__ == '__main__':
    create_doctors()

