"""
Script to create sample pharmacists with store locations
Run: python manage.py shell < create_pharmacists.py
Or: python manage.py shell, then copy-paste this code
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import User
from pharmacy.models import Pharmacist

def create_pharmacists():
    """Create sample pharmacists with store locations"""
    
    pharmacists_data = [
        {
            'username': 'pharma1',
            'email': 'pharma1@example.com',
            'first_name': 'Rajesh',
            'last_name': 'Kumar',
            'password': 'pharma123',
            'phone': '9876543210',
            'store_name': 'City Medical Store',
            'store_address': '123 Main Street, City Center, Mumbai',
            'latitude': 19.0759837,
            'longitude': 72.8776559,
        },
        {
            'username': 'pharma2',
            'email': 'pharma2@example.com',
            'first_name': 'Priya',
            'last_name': 'Sharma',
            'password': 'pharma123',
            'phone': '9876543211',
            'store_name': 'Health Plus Pharmacy',
            'store_address': '456 Market Road, Near Hospital, Mumbai',
            'latitude': 19.0760,
            'longitude': 72.8777,
        },
        {
            'username': 'pharma3',
            'email': 'pharma3@example.com',
            'first_name': 'Amit',
            'last_name': 'Patel',
            'password': 'pharma123',
            'phone': '9876543212',
            'store_name': 'Wellness Pharmacy',
            'store_address': '789 Station Road, Thane',
            'latitude': 19.2183,
            'longitude': 72.9781,
        },
        {
            'username': 'pharma4',
            'email': 'pharma4@example.com',
            'first_name': 'Sunita',
            'last_name': 'Singh',
            'password': 'pharma123',
            'phone': '9876543213',
            'store_name': 'MediCare Pharmacy',
            'store_address': '321 High Street, Navi Mumbai',
            'latitude': 19.0330,
            'longitude': 73.0297,
        },
        {
            'username': 'pharma5',
            'email': 'pharma5@example.com',
            'first_name': 'Vikram',
            'last_name': 'Reddy',
            'password': 'pharma123',
            'phone': '9876543214',
            'store_name': 'Apollo Pharmacy',
            'store_address': '654 Commercial Street, Pune',
            'latitude': 18.5204,
            'longitude': 73.8567,
        },
        {
            'username': 'pharma6',
            'email': 'pharma6@example.com',
            'first_name': 'Kavita',
            'last_name': 'Desai',
            'password': 'pharma123',
            'phone': '9876543215',
            'store_name': 'LifeCare Medical Store',
            'store_address': '987 MG Road, Nashik',
            'latitude': 19.9975,
            'longitude': 73.7898,
        },
        {
            'username': 'pharma7',
            'email': 'pharma7@example.com',
            'first_name': 'Ramesh',
            'last_name': 'Iyer',
            'password': 'pharma123',
            'phone': '9876543216',
            'store_name': 'QuickMed Pharmacy',
            'store_address': '147 Railway Station Road, Aurangabad',
            'latitude': 19.8762,
            'longitude': 75.3433,
        },
        {
            'username': 'pharma8',
            'email': 'pharma8@example.com',
            'first_name': 'Anjali',
            'last_name': 'Nair',
            'password': 'pharma123',
            'phone': '9876543217',
            'store_name': 'Trust Pharmacy',
            'store_address': '258 Bus Stand Road, Nagpur',
            'latitude': 21.1458,
            'longitude': 79.0882,
        },
        {
            'username': 'pharma9',
            'email': 'pharma9@example.com',
            'first_name': 'Rohit',
            'last_name': 'Joshi',
            'password': 'pharma123',
            'phone': '9876543218',
            'store_name': 'Nearby Medical Store',
            'store_address': '123 Village Road, Near Test Location',
            'latitude': 19.9670,
            'longitude': 73.7541,
        },
        {
            'username': 'pharma10',
            'email': 'pharma10@example.com',
            'first_name': 'Meera',
            'last_name': 'Verma',
            'password': 'pharma123',
            'phone': '9876543219',
            'store_name': 'Local Pharmacy',
            'store_address': '456 Main Street, Test Area',
            'latitude': 19.9680,
            'longitude': 73.7550,
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for data in pharmacists_data:
        # Create or get user
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'phone': data['phone'],
                'is_pharmacist': True,
            }
        )
        
        if created:
            user.set_password(data['password'])
            user.save()
            print(f"✅ Created user: {user.username}")
        else:
            # Update existing user
            user.is_pharmacist = True
            user.email = data['email']
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.phone = data['phone']
            user.save()
            print(f"🔄 Updated user: {user.username}")
        
        # Create or update pharmacist profile
        pharmacist, pharma_created = Pharmacist.objects.get_or_create(
            user=user,
            defaults={
                'store_name': data['store_name'],
                'store_address': data['store_address'],
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'phone': data['phone'],
                'email': data['email'],
                'is_active': True,
            }
        )
        
        if not pharma_created:
            # Update existing pharmacist
            pharmacist.store_name = data['store_name']
            pharmacist.store_address = data['store_address']
            pharmacist.latitude = data['latitude']
            pharmacist.longitude = data['longitude']
            pharmacist.phone = data['phone']
            pharmacist.email = data['email']
            pharmacist.is_active = True
            pharmacist.save()
            updated_count += 1
            print(f"🔄 Updated pharmacist: {pharmacist.store_name}")
        else:
            created_count += 1
            print(f"✅ Created pharmacist: {pharmacist.store_name}")
    
    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} pharmacists")
    print(f"   Updated: {updated_count} pharmacists")
    print(f"   Total pharmacists: {Pharmacist.objects.count()}")
    print(f"\n🔑 Login credentials:")
    print(f"   Username: pharma1, pharma2, etc.")
    print(f"   Password: pharma123")

if __name__ == '__main__':
    create_pharmacists()

