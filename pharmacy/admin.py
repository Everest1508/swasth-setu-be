from django.contrib import admin
from .models import Pharmacist, Prescription, Order, Medicine, MedicineStock, OrderItem


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


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'manufacturer', 'unit', 'created_at')
    list_filter = ('unit', 'created_at')
    search_fields = ('name', 'generic_name', 'manufacturer')


@admin.register(MedicineStock)
class MedicineStockAdmin(admin.ModelAdmin):
    list_display = ('pharmacist', 'medicine', 'quantity', 'price_per_unit', 'is_available', 'expiry_date')
    list_filter = ('is_available', 'pharmacist', 'expiry_date')
    search_fields = ('medicine__name', 'pharmacist__store_name', 'batch_number')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'medicine', 'quantity', 'price_per_unit', 'total_price')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'medicine__name')

