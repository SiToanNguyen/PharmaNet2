# Generated by Django 5.1.5 on 2025-01-31 12:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0012_alter_purchasetransaction_purchase_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='inventory',
            options={'ordering': ['-updated_at']},
        ),
        migrations.AlterModelOptions(
            name='manufacturer',
            options={'ordering': ['-updated_at']},
        ),
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['-updated_at']},
        ),
    ]
