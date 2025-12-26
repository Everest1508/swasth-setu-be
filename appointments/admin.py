from django.contrib import admin
from .models import Doctor, Appointment, DoctorSchedule

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'fee', 'rating', 'available')
    list_filter = ('specialty', 'available')
    search_fields = ('user__username', 'user__email', 'specialty')

@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time', 'is_available')
    list_filter = ('day_of_week', 'is_available')
    search_fields = ('doctor__user__username',)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_type', 'status', 'scheduled_date', 'scheduled_time')
    list_filter = ('status', 'appointment_type', 'scheduled_date')
    search_fields = ('patient__username', 'doctor__user__username')
    date_hierarchy = 'scheduled_date'
