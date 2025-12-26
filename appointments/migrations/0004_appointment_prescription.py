# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0003_appointment_google_calendar_event_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='prescription',
            field=models.TextField(blank=True, help_text='Prescription added by doctor'),
        ),
    ]

