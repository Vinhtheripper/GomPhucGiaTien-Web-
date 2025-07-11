# Generated by Django 5.2.3 on 2025-07-02 11:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_stocktransaction_price_productpricehistory'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productpricehistory',
            options={},
        ),
        migrations.RemoveField(
            model_name='productpricehistory',
            name='changed_by',
        ),
        migrations.RemoveField(
            model_name='productpricehistory',
            name='note',
        ),
        migrations.RemoveField(
            model_name='productpricehistory',
            name='price',
        ),
        migrations.AddField(
            model_name='productpricehistory',
            name='new_price',
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productpricehistory',
            name='old_price',
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productpricehistory',
            name='reason',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='productpricehistory',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.product'),
        ),
        migrations.CreateModel(
            name='ProductPriceConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base_cost_type', models.CharField(choices=[('last_import', 'Giá nhập gần nhất'), ('average_import', 'Giá nhập trung bình'), ('manual', 'Nhập tay (giữ nguyên giá product)')], default='last_import', max_length=20)),
                ('profit_margin', models.FloatField(default=20)),
                ('vat_percent', models.FloatField(default=8)),
                ('discount_percent', models.FloatField(default=0)),
                ('active', models.BooleanField(default=True)),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.product')),
            ],
        ),
    ]
