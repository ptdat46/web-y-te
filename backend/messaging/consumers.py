import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.db import close_old_connections

from care.models import ChatRoom
from doctors.models import ConnectionStatus, DoctorPatientConnection


class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        close_old_connections()
        user = self.scope.get('user')
        if user is not None and user.is_authenticated:
            self.group_name = f"user_{user.id}"
            async_to_sync(self.channel_layer.group_add)(
                self.group_name, self.channel_name
            )
            self.accept()
        else:
            self.close(code=4401)

    def disconnect(self, close_code):
        group_name = getattr(self, 'group_name', None)
        if group_name:
            async_to_sync(self.channel_layer.group_discard)(
                group_name, self.channel_name
            )

    def notification_event(self, event):
        # Uniform discriminator so the client can filter reliably.
        payload = {
            'type': 'notification',
            'notification': {
                'id': event.get('notification_id'),
                'notification_type': event.get('notification_type'),
                'title': event.get('title'),
                'message': event.get('message'),
                'link': event.get('link', ''),
                'created_at': event.get('created_at'),
            },
        }
        self.send(text_data=json.dumps(payload))


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        close_old_connections()
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            self.close(code=4401)
            return

        room_id = self.scope['url_route']['kwargs'].get('room_id')
        try:
            room = ChatRoom.objects.select_related('connection__doctor__user', 'connection__patient').get(pk=room_id)
        except (ChatRoom.DoesNotExist, ValueError, TypeError):
            self.close(code=4404)
            return

        connection = room.connection
        # connection is SET_NULL: it may be gone even though the room remains.
        if connection is None:
            self.close(code=4404)
            return
        if not room.active or connection.status != ConnectionStatus.APPROVED:
            self.close(code=4403)
            return

        # Membership: the user must be the connection's doctor user or patient.
        is_party = (
            connection.doctor.user_id == user.id
            or connection.patient_id == user.id
        )
        if not is_party:
            self.close(code=4403)
            return

        self.group_name = f"chat_{room.id}"
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        group_name = getattr(self, 'group_name', None)
        if group_name:
            async_to_sync(self.channel_layer.group_discard)(
                group_name, self.channel_name
            )

    def chat_message(self, event):
        # Uniform payload: {"type": "chat.message", "message": {...}}
        self.send(text_data=json.dumps({
            'type': 'chat.message',
            'message': event.get('message', {}),
        }))
