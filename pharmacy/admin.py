from django.contrib import admin
from .models import Pharmacist, Prescription, Order


@admin.register(Pharmacist)
class PharmacistAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'store_address', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('store_name', 'user__username', 'user__email', 'store_address')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'title', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('patient__username', 'title', 'notes')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'pharmacist', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('patient__username', 'pharmacist__store_name', 'prescription_text')

