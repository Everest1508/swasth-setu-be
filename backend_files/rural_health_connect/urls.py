from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('api.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/video-calls/', include('video_calls.urls')),
]

