# Generated by Django 5.1.5 on 2025-02-09 16:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0019_productcategory_alter_product_category'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ProductCategory',
            new_name='Category',
        ),
    ]
