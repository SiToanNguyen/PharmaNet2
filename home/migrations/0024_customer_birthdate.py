# Generated by Django 5.1.5 on 2025-04-10 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0023_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='birthdate',
            field=models.DateField(blank=True, null=True),
        ),
    ]
