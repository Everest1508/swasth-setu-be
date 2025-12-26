from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/video-call/<uuid:room_id>/', consumers.VideoCallConsumer.as_asgi()),
]

