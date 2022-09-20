from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager
import random, string
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from cryptography.fernet import Fernet
import base64
import ast



def encrypt(key, value):
    f = Fernet(base64.urlsafe_b64encode(key.encode('utf-8')))
    return f.encrypt(value.encode('utf-8'))

def decrypt(key, value):
    f = Fernet(base64.urlsafe_b64encode(key.encode('utf-8')))
    try:
        return f.decrypt(ast.literal_eval(value)).decode('utf-8')
    except Exception as e:
        print(e)
        return value


class CustomUser(AbstractBaseUser, PermissionsMixin):
    user_idno = models.CharField(max_length=50, verbose_name='User ID', unique=True, null=True, blank=True, editable=False)
    username = models.CharField(unique=True, max_length=60)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    can_use_default = models.BooleanField(default=False)
    can_send = models.BooleanField(default=False)
    wants_history = models.BooleanField(default=True)
    wants_random = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        if self.username:
            return self.username

    # For checking permissions. to keep it simple all admin have ALL permissons
    def has_perm(self, perm, obj=None):
        return self.is_admin

    # Does this user have permission to view this app? (ALWAYS YES FOR SIMPLICITY)
    def has_module_perms(self, app_label):
        return True




class EmailProfile(models.Model):
    email= models.EmailField(max_length=200)
    app_pass = models.CharField(max_length=500, verbose_name='App Password')
    host = models.CharField(max_length=50, default=None, null=True, blank=True, verbose_name='Email host')
    port = models.CharField(max_length=50, default=None, null=True, blank=True, verbose_name='Email port')
    is_active = models.BooleanField(default=True)
    owned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='profile owner', related_name='email_profiles')
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.email} owned by {self.owned_by}'

    class Meta:
        unique_together = ('email', 'owned_by')
    
    def get_app_pass(self):
        key = str(self.owned_by.user_idno) * 4
        key = key[:32]
        return decrypt(key, self.app_pass)



class TelnyxProfile(models.Model):
    number = PhoneNumberField(max_length=20, verbose_name='Telnyx number')
    api_key = models.CharField(max_length=500, verbose_name="API Key")
    is_active = models.BooleanField(default=True)
    owned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='profile owner', related_name='telnyx_profiles')
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.number} owned by {self.owned_by}'

    class Meta:
        unique_together = ('number', 'owned_by')

    def get_api_key(self):
        key = str(self.owned_by.user_idno) * 4
        key = key[:32]
        return decrypt(key, self.api_key)
