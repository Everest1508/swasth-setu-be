import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import VideoCallRoom, CallParticipant

User = get_user_model()


class VideoCallConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for video call signaling"""
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'video_call_{self.room_id}'
        self.user = self.scope['user']
        
        # Verify user has access to this room
        has_access = await self.verify_room_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Forward signaling messages to other participants
            if message_type in ['offer', 'answer', 'ice-candidate']:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'video_call_message',
                        'message': data,
                        'sender_id': self.user.id,
                    }
                )
        except json.JSONDecodeError:
            pass
    
    async def video_call_message(self, event):
        """Send video call signaling message to WebSocket"""
        # Don't send message back to sender
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps(event['message']))
    
    async def user_joined(self, event):
        """Handle user joined event"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username'],
            }))
    
    async def user_left(self, event):
        """Handle user left event"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username'],
            }))
    
    @database_sync_to_async
    def verify_room_access(self):
        """Verify user has access to this video call room"""
        try:
            room = VideoCallRoom.objects.get(id=self.room_id)
            appointment = room.appointment
            # Check if user is patient or doctor
            return (
                appointment.patient == self.user or 
                appointment.doctor.user == self.user
            )
        except VideoCallRoom.DoesNotExist:
            return False

