from django.contrib import admin
from .models import VideoCallRoom, CallParticipant

@admin.register(VideoCallRoom)
class VideoCallRoomAdmin(admin.ModelAdmin):
    list_display = ('room_name', 'appointment', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('room_name', 'appointment__patient__username')

@admin.register(CallParticipant)
class CallParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'is_active', 'joined_at')
    list_filter = ('is_active', 'joined_at')
    search_fields = ('user__username', 'room__room_name')
