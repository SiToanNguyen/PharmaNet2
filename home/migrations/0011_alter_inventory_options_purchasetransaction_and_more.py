# Generated by Django 5.1.5 on 2025-01-28 07:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0010_inventory'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='inventory',
            options={},
        ),
        migrations.CreateModel(
            name='PurchaseTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purchase_date', models.DateTimeField(auto_now_add=True)),
                ('invoice_number', models.CharField(max_length=100, unique=True)),
                ('total_cost', models.DecimalField(decimal_places=2, max_digits=15)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('manufacturer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='home.manufacturer')),
            ],
        ),
        migrations.CreateModel(
            name='PurchasedProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(blank=True, max_length=100, null=True)),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('expiry_date', models.DateField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='home.product')),
                ('purchase_transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchased_products', to='home.purchasetransaction')),
            ],
        ),
    ]
