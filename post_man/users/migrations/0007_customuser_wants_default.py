# Generated by Django 4.1 on 2022-09-25 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_customuser_message_credit'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='wants_default',
            field=models.BooleanField(default=True),
        ),
    ]