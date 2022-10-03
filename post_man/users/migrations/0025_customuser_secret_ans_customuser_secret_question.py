# Generated by Django 4.1 on 2022-10-02 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_purchase_order_code_alter_purchase_charge_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='secret_ans',
            field=models.CharField(blank=True, editable=False, max_length=500, null=True, unique=True, verbose_name='Secret Answer'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='secret_question',
            field=models.CharField(blank=True, editable=False, max_length=500, null=True, unique=True, verbose_name='Secret Question'),
        ),
    ]