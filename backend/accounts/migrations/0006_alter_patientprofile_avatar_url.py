from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_patientprofile_health_background'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patientprofile',
            name='avatar_url',
            field=models.TextField(blank=True, max_length=5000000),
        ),
    ]
