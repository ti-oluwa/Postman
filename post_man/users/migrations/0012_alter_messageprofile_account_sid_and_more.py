# Generated by Django 4.1 on 2022-09-26 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_remove_messageprofile_api_client_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messageprofile',
            name='account_sid',
            field=models.CharField(blank=True, default=None, max_length=500, null=True, verbose_name='Account SID'),
        ),
        migrations.AlterField(
            model_name='messageprofile',
            name='api_key',
            field=models.CharField(default=None, max_length=500, verbose_name='API Key'),
        ),
    ]
