from email.policy import default
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager
import random, string
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from cryptography.fernet import Fernet
import base64
import ast, math



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
    secret_question = models.CharField(max_length=500, verbose_name='Secret Question', null=True, blank=True, editable=False, help_text='This is a secret question that you can use to reset your password if you forget it.')
    secret_ans = models.CharField(max_length=500, verbose_name='Secret Answer', null=True, blank=True, editable=False, help_text='This is a secret answer to your secret question')
    preferred_sms_rate = models.IntegerField(verbose_name="SMS Send Rate", default=5, null=True, blank=True)
    preferred_mail_rate = models.IntegerField(verbose_name="Mail Send Rate", default=5, null=True, blank=True)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    can_use_default = models.BooleanField(default=False)
    can_send = models.BooleanField(default=False)
    message_credit = models.IntegerField(default=0, blank=True, null=True)
    wants_history = models.BooleanField(default=True)
    wants_random = models.BooleanField(default=False)
    wants_default = models.BooleanField(default=True)
    accepted_cookies = models.BooleanField(default=False)
    rejected_cookies = models.BooleanField(default=False)
    accepted_pp = models.BooleanField(default=False)
    is_privileged = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['secret_question', 'secret_ans']

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

EMAIL_CHOICES = (   
    ('Gmail', 'Gmail'),
    ('Yahoo', 'Yahoo'),
    ('Outlook', 'Outlook'),
    ('Protonmail', 'Protonmail'),
    ('AOL', 'AOL'),
    ('Virgin Media', 'Virgin Media'),
    ('AT&T', 'AT&T'),
    ('Verizon', 'Verizon'),
)


class EmailProfile(models.Model):
    email= models.EmailField(max_length=200, verbose_name="Profile Email")
    app_pass = models.CharField(max_length=500, verbose_name='App Password')
    host = models.CharField(max_length=50, default=None, null=True, blank=True, verbose_name='Email host')
    port = models.IntegerField(default=465, null=True, blank=True, verbose_name='Email port')
    use_tls = models.BooleanField(default=True, verbose_name='Use TLS')
    use_ssl = models.BooleanField(default=False, verbose_name='Use SSL')
    type = models.CharField(max_length=50, choices=EMAIL_CHOICES , default='Gmail', blank=True, null=True, verbose_name='Email type')
    is_active = models.BooleanField(default=True)
    owned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='profile owner', related_name='email_profiles')
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.email} owned by {self.owned_by}'

    class Meta:
        unique_together = ('email', 'owned_by')
        ordering = ['-date_added']
    
    def get_app_pass(self):
        key = str(self.owned_by.user_idno) * 4
        key = key[:32]
        return decrypt(key, self.app_pass)

    def get_trunc_app_pass(self):
        trunc_pass = self.get_app_pass()[:4] +  '...' + self.get_app_pass()[-4:]
        return trunc_pass


PROVIDER_CHOICES = (
    ('telnyx', 'Telnyx'),
    ('twilio', 'Twilio'),
)

class MessageProfile(models.Model):
    number = PhoneNumberField(max_length=20, verbose_name='Profile Number')
    api_key = models.CharField(max_length=500, default=None, verbose_name="API Key")
    api_provider = models.CharField(max_length=50, verbose_name="API Provider", null=True, choices=PROVIDER_CHOICES)
    account_sid = models.CharField(max_length=500, verbose_name="Account SID", default=None, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    owned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='profile owner', related_name='message_profiles')
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.number} owned by {self.owned_by}'

    class Meta:
        unique_together = ('number', 'owned_by')
        ordering = ['-date_added']

    def get_api_key(self):
        key = str(self.owned_by.user_idno) * 4
        key = key[:32]
        return decrypt(key, self.api_key)

    def get_trunc_api_key(self):
        trunc_key = self.get_api_key()[:4] +  '......' + self.get_api_key()[-4:]
        return trunc_key

    def get_account_sid(self):
        key = str(self.owned_by.user_idno) * 4
        key = key[:32]
        return decrypt(key, self.account_sid)


class CreditPackage(models.Model):
    '''Credit packages'''
    amount = models.IntegerField(default=0, unique=True, verbose_name='Credit amount')
    price = models.DecimalField(max_digits=50, decimal_places=2, default=0.00, verbose_name='Price')
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.amount} credits for ${self.price}'

    class Meta:
        ordering = ['amount']


class Purchase(models.Model):
    '''Purchases'''
    user = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=None, null=True, verbose_name='made by', related_name='purchases')
    amount = models.IntegerField(default=0, verbose_name='Amount Purchased')
    price = models.DecimalField(max_digits=50, decimal_places=2, default=0.00, verbose_name='Price')
    credit_packages = models.ManyToManyField(CreditPackage, verbose_name='credit packages', related_name='purchases')
    sid = models.CharField(max_length=500, default=None, null=True, blank=True, verbose_name='Purchase ID')
    charge_id = models.CharField(max_length=500, default=None, null=True, blank=True, verbose_name='Coinbase charge ID')
    order_code = models.CharField(max_length=500, default=None, null=True, blank=True, verbose_name='Coinbase order code')
    is_closed = models.BooleanField(default=False)
    success = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(default=None, null=True, blank=True)




    def __str__(self):
        return f'{self.user} purchased {self.amount} credits on {self.date_created}'

    class Meta:
        ordering = ['-date_created', '-date_closed']