# Generated by Django 5.1.5 on 2025-01-25 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_alter_activitylog_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='manufacturer',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
