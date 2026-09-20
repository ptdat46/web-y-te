from rest_framework import serializers

from accounts.models import User
from accounts.serializers import PublicUserSerializer

from .models import ChatConversation, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'role', 'content', 'red_flag', 'created_at')
        read_only_fields = ('role', 'content', 'red_flag', 'created_at')


class ChatConversationSerializer(serializers.ModelSerializer):
    target_patient = PublicUserSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        source='target_patient',
        queryset=User.objects.filter(role='PATIENT'),
        write_only=True,
        required=False,
    )
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = (
            'id', 'title', 'target_patient', 'patient_id', 'created_at', 'updated_at',
            'is_active', 'last_message', 'message_count',
        )
        read_only_fields = (
            'id', 'title', 'created_at', 'updated_at', 'is_active', 'target_patient',
        )

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        target = attrs.get('target_patient')
        if user is None or not user.is_authenticated:
            raise serializers.ValidationError('Yêu cầu đăng nhập.')
        if user.role == 'PATIENT':
            if target is not None and target.pk != user.pk:
                raise serializers.ValidationError({'patient_id': 'Bệnh nhân chỉ được chat về hồ sơ của chính mình.'})
            attrs['target_patient'] = user
        elif user.role == 'DOCTOR':
            if target is None:
                raise serializers.ValidationError({'patient_id': 'Bác sĩ cần chọn một bệnh nhân.'})
        else:
            raise serializers.ValidationError('Vai trò này không được sử dụng chatbot.')
        return attrs

    def create(self, validated_data):
        return super().create(validated_data)

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
