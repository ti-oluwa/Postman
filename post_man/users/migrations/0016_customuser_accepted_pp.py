# Generated by Django 4.1 on 2022-09-28 23:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_customuser_rejected_cookies'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='accepted_pp',
            field=models.BooleanField(default=False),
        ),
    ]
