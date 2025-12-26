from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Notification
from .serializers import NotificationSerializer, NotificationUpdateSerializer


class NotificationListView(generics.ListAPIView):
    """List user's notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Filter by read status
        is_read = self.request.query_params.get('read', None)
        queryset = Notification.objects.filter(user=user)
        
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Filter by type
        notification_type = self.request.query_params.get('type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete notification"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        """Mark notification as read"""
        instance = self.get_object()
        serializer = NotificationUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data.get('is_read'):
            instance.mark_as_read()
        else:
            serializer.save()
        
        return Response(NotificationSerializer(instance).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    """Mark all notifications as read for the user"""
    updated = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)
    
    return Response({
        'message': f'{updated} notifications marked as read',
        'count': updated
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Get count of unread notifications"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return Response({'unread_count': count})
