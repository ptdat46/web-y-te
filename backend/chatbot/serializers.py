from rest_framework import serializers

from .models import ChatConversation, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'role', 'content', 'red_flag', 'created_at')
        read_only_fields = ('role', 'content', 'red_flag', 'created_at')


class ChatConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = ('id', 'title', 'created_at', 'updated_at', 'is_active', 'last_message', 'message_count')
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_active')

    def _messages(self, obj):
        # Works with both a prefetched queryset and a plain list
        msgs = getattr(obj, 'messages', None)
        if msgs is None:
            return []
        if isinstance(msgs, list):
            return msgs
        return list(msgs.all())

    def get_last_message(self, obj):
        msgs = self._messages(obj)
        if msgs:
            return msgs[-1].content[:120]
        return None

    def get_message_count(self, obj):
        return len(self._messages(obj))


class ChatConversationDetailSerializer(ChatConversationSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatConversationSerializer.Meta):
        fields = ChatConversationSerializer.Meta.fields + ('messages',)


class ChatSendSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, min_length=1)

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Thông báo không được rỗng.')
        return value