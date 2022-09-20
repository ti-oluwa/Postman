# Generated by Django 4.1 on 2022-09-19 20:35

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_emailprofile_owned_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailprofile',
            name='app_pass',
            field=models.CharField(max_length=500, verbose_name='App Password'),
        ),
        migrations.AlterField(
            model_name='emailprofile',
            name='host',
            field=models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Email host'),
        ),
        migrations.AlterField(
            model_name='emailprofile',
            name='port',
            field=models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Email port'),
        ),
        migrations.AlterField(
            model_name='telnyxprofile',
            name='api_key',
            field=models.CharField(max_length=500, verbose_name='API Key'),
        ),
        migrations.AlterField(
            model_name='telnyxprofile',
            name='number',
            field=phonenumber_field.modelfields.PhoneNumberField(max_length=20, region=None, verbose_name='Telnyx number'),
        ),
        migrations.AlterUniqueTogether(
            name='emailprofile',
            unique_together={('email', 'owned_by')},
        ),
        migrations.AlterUniqueTogether(
            name='telnyxprofile',
            unique_together={('number', 'owned_by')},
        ),
    ]