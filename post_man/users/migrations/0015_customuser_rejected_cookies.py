# Generated by Django 4.1 on 2022-09-28 20:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_customuser_is_privileged'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='rejected_cookies',
            field=models.BooleanField(default=False),
        ),
    ]
