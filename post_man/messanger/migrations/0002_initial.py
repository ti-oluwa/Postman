# Generated by Django 4.1 on 2022-09-16 23:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('messanger', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='textmessage',
            name='sent_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='text_messages', to=settings.AUTH_USER_MODEL, verbose_name='sender'),
        ),
        migrations.AddField(
            model_name='textmessage',
            name='sent_to',
            field=models.ManyToManyField(blank=True, default=None, max_length=16, related_name='sms_received', to='messanger.phonenumber', verbose_name='receivers'),
        ),
        migrations.AddField(
            model_name='phonenumber',
            name='added_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='added_phone_numbers', to=settings.AUTH_USER_MODEL, verbose_name='added by'),
        ),
        migrations.AddField(
            model_name='emailaddress',
            name='added_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='added_email_addresses', to=settings.AUTH_USER_MODEL, verbose_name='added by'),
        ),
        migrations.AddField(
            model_name='email',
            name='sent_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mails', to=settings.AUTH_USER_MODEL, verbose_name='sender'),
        ),
        migrations.AddField(
            model_name='email',
            name='sent_to',
            field=models.ManyToManyField(related_name='mails_received', to='messanger.emailaddress', verbose_name='receivers'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='added_by',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to=settings.AUTH_USER_MODEL, verbose_name='added by'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='email',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='messanger.email'),
        ),
    ]
