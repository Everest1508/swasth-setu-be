from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    mark_all_as_read,
    unread_count,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('mark-all-read/', mark_all_as_read, name='mark-all-read'),
    path('unread-count/', unread_count, name='unread-count'),
]

