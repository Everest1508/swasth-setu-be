from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom User Admin with doctor creation support"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_doctor', 'is_staff', 'date_joined')
    list_filter = ('is_doctor', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'location', 'is_doctor')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('phone', 'location', 'is_doctor')}),
    )
