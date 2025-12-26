from django.urls import path
from .views import (
    VideoCallRoomCreateView,
    get_room_by_appointment,
    get_room_details,
    join_room,
    leave_room
)

urlpatterns = [
    path('create-room/', VideoCallRoomCreateView.as_view(), name='create-room'),
    path('appointment/<int:appointment_id>/room/', get_room_by_appointment, name='room-by-appointment'),
    path('room/<uuid:room_id>/', get_room_details, name='room-details'),
    path('room/<uuid:room_id>/join/', join_room, name='join-room'),
    path('room/<uuid:room_id>/leave/', leave_room, name='leave-room'),
]

