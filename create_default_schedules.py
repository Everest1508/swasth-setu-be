#!/usr/bin/env python
"""
Script to create default schedules for all doctors.
Run: python manage.py shell < create_default_schedules.py
Or: python create_default_schedules.py (after setting up Django)
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from appointments.models import Doctor, DoctorSchedule
from datetime import time

# Default schedule: Monday to Friday, 9 AM to 6 PM
DEFAULT_SCHEDULE = [
    (0, time(9, 0), time(18, 0)),  # Monday
    (1, time(9, 0), time(18, 0)),  # Tuesday
    (2, time(9, 0), time(18, 0)),  # Wednesday
    (3, time(9, 0), time(18, 0)),  # Thursday
    (4, time(9, 0), time(18, 0)),  # Friday
]

def create_default_schedules():
    """Create default schedules for all doctors"""
    doctors = Doctor.objects.all()
    created_count = 0
    updated_count = 0
    
    for doctor in doctors:
        for day_of_week, start_time, end_time in DEFAULT_SCHEDULE:
            schedule, created = DoctorSchedule.objects.get_or_create(
                doctor=doctor,
                day_of_week=day_of_week,
                defaults={
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_available': True,
                }
            )
            
            if not created:
                # Update existing schedule
                schedule.start_time = start_time
                schedule.end_time = end_time
                schedule.is_available = True
                schedule.save()
                updated_count += 1
            else:
                created_count += 1
        
        print(f"✅ Set schedule for Dr. {doctor.user.get_full_name() or doctor.user.username}")
    
    print(f"\n✅ Summary:")
    print(f"   - Created: {created_count} schedule entries")
    print(f"   - Updated: {updated_count} schedule entries")
    print(f"   - Total doctors: {doctors.count()}")


if __name__ == '__main__':
    create_default_schedules()

