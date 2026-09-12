from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('care', '0002_auditlog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('ALERT', 'Cảnh báo sức khỏe'), ('MEDICAL_RECORD', 'Hồ sơ bệnh án'), ('CONNECTION', 'Kết nối'), ('SYSTEM', 'Hệ thống')], max_length=30)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField(blank=True)),
                ('link', models.CharField(blank=True, max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['recipient', 'is_read', 'created_at'], name='care_notifi_recipie_6d9a42_idx')],
            },
        ),
    ]
