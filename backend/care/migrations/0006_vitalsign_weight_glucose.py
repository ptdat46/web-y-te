from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('care', '0005_medication_appointment'),
    ]

    operations = [
        migrations.AddField(
            model_name='vitalsign',
            name='weight_kg',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vitalsign',
            name='blood_glucose',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
