# Generated by Django 4.1 on 2022-09-25 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_alter_emailprofile_app_pass_alter_emailprofile_host_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='message_credit',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]