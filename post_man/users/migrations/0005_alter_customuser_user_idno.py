# Generated by Django 4.1 on 2022-10-15 21:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_customuser_preferred_mail_rate_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='user_idno',
            field=models.CharField(blank=True, default=None, editable=False, max_length=50, null=True, unique=True, verbose_name='User ID'),
        ),
    ]