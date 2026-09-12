from asgiref.sync import async_to_sync

from care.models import Notification


def _channel_layer():
    from channels.layers import get_channel_layer
    return get_channel_layer()


def create_notification(recipient, notification_type, title, message, link=''):
    """Persist a Notification and push it to the recipient over WebSocket."""
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )
    channel_layer = _channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"user_{recipient.pk}",
            {
                'type': 'notification_event',
                'notification_id': notification.pk,
                'notification_type': notification_type,
                'title': title,
                'message': message,
                'link': link,
                'created_at': notification.created_at.isoformat(),
            },
        )
    return notification


def push_chat_message(room_id, message_dict):
    """Broadcast a saved chat message to everyone in the room group."""
    channel_layer = _channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_id}",
            {
                'type': 'chat_message',
                'message': message_dict,
            },
        )
