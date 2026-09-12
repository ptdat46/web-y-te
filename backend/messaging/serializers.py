from __future__ import annotations

import re
from pathlib import Path
from django.db.models import Sum
from rest_framework import serializers
from care.models import ChatRoom, P2PMessage, PatientFile


CHAT_ALLOWED = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}
CHAT_MAX = 5 * 1024 * 1024
FILE_MAX = 10 * 1024 * 1024
QUOTA_MAX = 100 * 1024 * 1024

SAFE_FILENAME_RE = re.compile(r'^[A-Za-z0-9_\-.]+$')

MAGIC_SIGNATURES = {
    '.pdf': b'%PDF-',
    '.jpg': b'\xff\xd8\xff',
    '.jpeg': b'\xff\xd8\xff',
    '.png': b'\x89PNG\r\n\x1a\n',
    '.docx': b'PK\x03\x04',
    '.doc': b'\xd0\xcf\x11\xe0',
}

EXPECTED_CONTENT_TYPES = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def _is_allowed_content_type(ext: str, content_type: str) -> bool:
    if not content_type or content_type == 'application/octet-stream':
        return True
    expected = EXPECTED_CONTENT_TYPES.get(ext)
    if expected is None:
        return True
    return content_type == expected


def _validate_magic(ext: str, head: bytes) -> None:
    signature = MAGIC_SIGNATURES.get(ext)
    if signature is None:
        return
    if not head.startswith(signature):
        raise serializers.ValidationError('File signature does not match its extension.')


def _sanitize_filename(name: str, fallback: str) -> str:
    base = Path(name).name.strip()
    base = base.replace(' ', '_')
    if not base or not SAFE_FILENAME_RE.match(base):
        base = fallback
    return base


def validate_upload(upload, *, max_size: int, allowed: set[str] = CHAT_ALLOWED) -> None:
    if not upload:
        return
    if upload.size > max_size:
        raise serializers.ValidationError(f'File must be {max_size // (1024 * 1024)}MB or smaller.')
    ext = Path(upload.name).suffix.lower()
    if ext not in allowed:
        raise serializers.ValidationError('Unsupported file type. Allowed: PDF, JPG, PNG, DOC, DOCX.')
    content_type = (getattr(upload, 'content_type', '') or '').lower()
    if not _is_allowed_content_type(ext, content_type):
        raise serializers.ValidationError('File content type does not match its extension.')
    try:
        pos = upload.tell()
        head = upload.read(16)
        upload.seek(pos)
    except (AttributeError, IOError):
        head = b''
    _validate_magic(ext, head)


class P2PMessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField(read_only=True)
    attachment_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = P2PMessage
        fields = ('id', 'room', 'sender', 'content', 'attachment', 'attachment_url', 'created_at')
        read_only_fields = ('id', 'room', 'sender', 'attachment_url', 'created_at')

    def get_sender(self, obj):
        return {
            'id': obj.sender_id,
            'username': obj.sender.username,
            'full_name': obj.sender.get_full_name() or obj.sender.username,
        }

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url

    def validate(self, attrs):
        if not attrs.get('content') and not attrs.get('attachment'):
            raise serializers.ValidationError('Message must contain text or an attachment.')
        validate_upload(attrs.get('attachment'), max_size=CHAT_MAX)
        return attrs


class ChatRoomSerializer(serializers.ModelSerializer):
    connection_id = serializers.IntegerField(source='connection.id', read_only=True)
    doctor = serializers.SerializerMethodField(read_only=True)
    patient = serializers.SerializerMethodField(read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = ('id', 'connection_id', 'doctor', 'patient', 'active', 'created_at', 'updated_at', 'last_message')
        read_only_fields = fields

    def get_doctor(self, obj):
        if not obj.connection:
            return None
        user = obj.connection.doctor.user
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
        }

    def get_patient(self, obj):
        if not obj.connection:
            return None
        user = obj.connection.patient
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
        }

    def get_last_message(self, obj):
        last = obj.messages.first()
        if not last:
            return None
        sender = last.sender
        return {
            'id': last.id,
            'content': last.content,
            'sender': {'id': sender.id, 'username': sender.username, 'full_name': sender.get_full_name() or sender.username},
            'created_at': last.created_at,
        }


class PatientFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)
    patient = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PatientFile
        fields = (
            'id', 'patient', 'original_name', 'content_type', 'size',
            'file', 'file_url', 'uploaded_at',
        )
        read_only_fields = ('id', 'patient', 'file_url', 'uploaded_at')

    def get_patient(self, obj):
        user = obj.patient
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
        }

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def validate(self, attrs):
        upload = attrs.get('file') if self.instance is None else attrs.get('file', self.instance.file)
        if upload is not None:
            validate_upload(upload, max_size=FILE_MAX)
            sanitized = _sanitize_filename(
                getattr(upload, 'name', '') or 'upload',
                f'file_{self.instance.pk if self.instance else "new"}',
            )
            attrs['original_name'] = sanitized
        if self.instance is None:
            current_used = PatientFile.objects.filter(patient_id=self.context['request'].user.pk).aggregate(total=Sum('size'))['total'] or 0
            if (current_used + (upload.size if upload else 0)) > QUOTA_MAX:
                raise serializers.ValidationError('Patient storage quota is 100MB.')
        return attrs
