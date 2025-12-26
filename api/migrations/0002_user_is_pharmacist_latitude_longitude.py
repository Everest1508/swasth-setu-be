# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_pharmacist',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, help_text="User's current latitude", max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, help_text="User's current longitude", max_digits=9, null=True),
        ),
    ]

