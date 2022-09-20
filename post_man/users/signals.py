from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete 
from django.core.signals import got_request_exception
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from .models import encrypt, EmailProfile, TelnyxProfile, CustomUser
import random, string, json
from django.conf import settings
from django.utils import timezone



with open(settings.STATIC_ROOT + '/images/accounts.json', 'r') as f:
    account = json.load(f)[0]

# handles and reports server errors
@receiver(got_request_exception)
def handle_server_error(sender, request, **kwargs):
    if request.status_code >= 500 and request.status_code < 600:
        connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
        email = EmailMessage(
            subject="Server Error",
            body=str(request),
            from_email=account['auth_user'],
            to=["tholuwarlarshe2003@gmail.com"],
        )
        connection.send_messages([email])
        print("500 error")
        

#send a mail to me on new user creation
@receiver(post_save, sender=CustomUser)
def send_mail_on_new_user(sender, instance, created, **kwargs):
    if created:
        connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
        email = EmailMessage(
            subject="New User Created on Postman",
            body="New user created: " + instance.username + "\n" + "User ID: " + str(instance.user_idno) + "\n" + "Allowed to send: " + str(instance.can_send) + "\n" + "Allowed to use default: " + str(instance.can_use_default)
            + "\n" + "Wants history: " + str(instance.wants_history) + "\n" + "Wants random: " + str(instance.wants_random) + "\n" + "Is admin: " + str(instance.is_admin) + "\n" + "Is staff: " + str(instance.is_staff)
            + "\n" + "Is superuser: " + str(instance.is_superuser) + "\n" + "Date joined: " + str(instance.date_joined) + "\n" + "Last login: " + str(instance.last_login),
            from_email=account['auth_user'],
            to=["tholuwarlarshe2003@gmail.com"],
        )
        connection.send_messages([email])



#send a mail to me on user deletion
@receiver(post_delete, sender=CustomUser)
def send_mail_on_user_deletion(sender, instance, **kwargs):
    connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
    email = EmailMessage(
        subject="User Deleted on Postman",
        body="User deleted: " + instance.username + "\n" + "User ID: " + str(instance.user_idno) + "\n" + "Allowed to send: " + str(instance.can_send) + "\n" + "Allowed to use default: " + str(instance.can_use_default)
        + "\n" + "Wants history: " + str(instance.wants_history) + "\n" + "Wants random: " + str(instance.wants_random) + "\n" + "Is admin: " + str(instance.is_admin) + "\n" + "Is staff: " + str(instance.is_staff)
        + "\n" + "Is superuser: " + str(instance.is_superuser) + "\n" + "Date joined: " + str(instance.date_joined) + "\n" + "Last login: " + str(instance.last_login) + '\n' + "Deleted on: " + str(timezone.now()),
        from_email=account['auth_user'],
        to=['tholuwarlarshe2003@gmail.com'],
    )
    connection.send_messages([email])



# update user id no on user creation
@receiver(pre_save, sender=CustomUser)
def set_user_id(sender, instance, **kwargs):
    if instance.user_idno == None:
        user_idno = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))     
        if CustomUser.objects.filter(user_idno=user_idno).exists():
            user_idno = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))
        else:
            instance.user_idno = user_idno

@receiver(pre_save, sender=EmailProfile)
def encrypt_email_profile(sender, instance, **kwargs):
    if not sender.objects.filter(pk=instance.pk).exists():
        if instance.app_pass:
            key = str(instance.owned_by.user_idno) * 4
            key = key[:32]
            instance.app_pass = encrypt(key, instance.app_pass)

        if instance.email.endswith("@gmail.com"):
            instance.host = 'smtp.gmail.com'
            instance.port = '587'
        elif instance.email.endswith("@outlook.com") or instance.email.endswith("@hotmail.com"):
            instance.host = "smtp.live.com"
            instance.port = '587'
        elif instance.email.endswith("@protonmail.com") or instance.email.endswith("@proton.me") or instance.email.endswith("@pm.me"):
            instance.host = "127.0.0.1"
            instance.port = '1025'
        elif instance.email.endswith("@aol.com") or instance.email.endswith("@love.com") or instance.email.endswith("@ygm.com") or instance.email.endswith("@wow.com") or instance.email.endswith("@games.com"):
            instance.host = "smtp.aol.com"
            instance.port = '587'
        elif instance.email.endswith("@att.net"):
            instance.host = "outbound.att.net"
            instance.port = '587'
        elif instance.email.endswith("@yahoo.com"):
            instance.host = "smtp.mail.yahoo.com"
            instance.port = '587'
        elif instance.email.endswith("@verizon.net"):
            instance.host = "outgoing.verizon.net"
            instance.port = '587'
        elif instance.email.endswith("@virginmedia.com"):
            instance.host = "smtp.virgin.net"
            instance.port = '587'
    

@receiver(pre_save, sender=TelnyxProfile)
def encrypt_telnyx_profile(sender, instance, **kwargs):
    if not sender.objects.filter(pk=instance.pk).exists():
        if instance.api_key:
            key = str(instance.owned_by.user_idno) * 4
            key = key[:32]
            instance.api_key = encrypt(key, instance.api_key)
    
    
