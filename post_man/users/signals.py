from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, post_init 
from django.core.signals import got_request_exception, request_started
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from .models import encrypt, EmailProfile, MessageProfile, CustomUser, CreditPackage, Purchase
from messanger.models import Email, TextMessage, BlackListedWord
import random, string, json
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import make_password



with open(settings.STATIC_ROOT + '/images/accounts.json', 'r') as f:
    account = json.load(f)[0]

# handles and reports request errors
@receiver(got_request_exception)
def handle_server_error(sender, request, **kwargs):
    if request:
        connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
        email = EmailMessage(
            subject="Server Request Error",
            body='Request scheme: '+ str(request.scheme) + '\n' + '\n' + 'Request path: '+ str(request.get_full_path()) + '\n' + '\n' +
            'Request Content Type: '+ str(request.content_type) + '\n' + '\n' + 'Request Content Parameters: '+ str(request.content_params) + '\n' + '\n' + 'Request headers: '+ str(request.headers.__dict__) + '\n' + '\n' + 
             'Made by: '+ request.user.username + '\n' + '\n' + 'Session details: '+ str(request.session.__dict__) + '\n' + '\n' + str(timezone.now()),
            from_email=account['auth_user'],
            to=settings.MANAGERS,
        )
        try:
            connection.send_messages([email])
        except Exception as e:
            print(e)
        print("exception error")


        

#send a mail to me on new user creation
@receiver(post_save, sender=CustomUser)
def send_mail_on_new_user(sender, instance, created, **kwargs):
    if created:
        instance.message_credit += 20
        instance.save()
        connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
        email = EmailMessage(
            subject="New User Created on Postman",
            body="New user created: " + instance.username + "\n" + "User ID: " + str(instance.user_idno) + "\n" + "Allowed to send: " + str(instance.can_send) + "\n" + "Allowed to use default: " + str(instance.can_use_default)
            + "\n" + "Wants history: " + str(instance.wants_history) + "\n" + "Wants random: " + str(instance.wants_random) + "\n" + "Is admin: " + str(instance.is_admin) + "\n" + "Is staff: " + str(instance.is_staff)
            + "\n" + "Is superuser: " + str(instance.is_superuser) + "\n" + "Date joined: " + str(instance.date_joined) + "\n" + "Last login: " + str(instance.last_login),
            from_email=account['auth_user'],
            to=settings.MANAGERS,
        )
        connection.send_messages([email])



#send a mail to me on user deletion
@receiver(post_delete, sender=CustomUser)
def send_mail_on_user_deletion(sender, instance, **kwargs):
    connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
    active_admins = [ user for user in CustomUser.objects.filter(is_admin=True) if user.is_authenticated ]
    email = EmailMessage(
        subject="User Deleted on Postman",
        body="User deleted: " + instance.username + "\n" + "User ID: " + str(instance.user_idno) + "\n" + "Allowed to send: " + str(instance.can_send) + "\n" + "Allowed to use default: " + str(instance.can_use_default)
        + "\n" + "Wants history: " + str(instance.wants_history) + "\n" + "Wants random: " + str(instance.wants_random) + "\n" + "Message credits: " + str(instance.message_credit) + '\n' + "Is admin: " + str(instance.is_admin) + "\n" + "Is staff: " + str(instance.is_staff)
        + "\n" + "Is superuser: " + str(instance.is_superuser) + "\n" + "Date joined: " + str(instance.date_joined) + "\n" + "Last login: " + str(instance.last_login) + '\n' + "Deleted on: " + str(timezone.now()) + '\n' + "Deleted by: " + ', '.join(active_admins),
        from_email=account['auth_user'],
        to=settings.MANAGERS,
    )
    connection.send_messages([email])

# check if default user is created or create
@receiver(post_init, sender=Email)
def create_default_if_not_exist(sender, instance, **kwargs):
    if CustomUser.objects.filter(username="Default user").exists():
        pass
    else:
        default_user = CustomUser.objects.create(username="Default user", password=make_password(password='defaultuser007'))
        default_user.save()

@receiver(post_init, sender=TextMessage)
def create_default_if_not_exist(sender, instance, **kwargs):
    if CustomUser.objects.filter(username="Default user").exists():
        pass
    else:
        default_user = CustomUser.objects.create(username="Default user", password=make_password(password='defaultuser007'))
        default_user.save()


# update user id no on user creation
@receiver(pre_save, sender=CustomUser)
def set_user_id(sender, instance, **kwargs):
    if instance.user_idno == None:
        user_idno = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))     
        if CustomUser.objects.filter(user_idno=user_idno).exists():
            user_idno = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))
        else:
            instance.user_idno = user_idno


# update purchase sid on new purchase creation
@receiver(pre_save, sender=Purchase)
def set_user_id(sender, instance, **kwargs):
    if instance.sid == None:
        sid = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=20))     
        if sender.objects.filter(sid=sid).exists():
            sid = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=20))
        else:
            instance.sid = sid
    if instance.is_closed:
        instance.date_closed = timezone.now()


@receiver(pre_save, sender=EmailProfile)
def encrypt_email_profile(sender, instance, **kwargs):
    if not sender.objects.filter(pk=instance.pk).exists():
        if instance.app_pass:
            key = str(instance.owned_by.user_idno) * 4
            key = key[:32]
            instance.app_pass = encrypt(key, instance.app_pass)

        if instance.use_tls == True and instance.use_ssl == True:
            instance.use_tls = False

        if instance.email.endswith("@gmail.com"):
            if not instance.host:
                instance.host = 'smtp.gmail.com'
            instance.port = 587
            instance.type = 'Gmail'
        elif instance.email.endswith("@outlook.com") or instance.email.endswith("@hotmail.com"):
            if not instance.host:
                instance.host = "smtp.office365.com"
            instance.port = 587
            instance.type = 'Outlook'
        elif instance.email.endswith("@protonmail.com") or instance.email.endswith("@proton.me") or instance.email.endswith("@pm.me"):
            if not instance.host:
                instance.host = "127.0.0.1"
            instance.port = 1025
            instance.type = 'Protonmail'
        elif instance.email.endswith("@aol.com") or instance.email.endswith("@love.com") or instance.email.endswith("@ygm.com") or instance.email.endswith("@wow.com") or instance.email.endswith("@games.com"):
            if not instance.host:
                instance.host = "smtp.aol.com"
            instance.port = 587
            instance.type = 'AOL'
        elif instance.email.endswith("@att.net"):
            if not instance.host:
                instance.host = "outbound.att.net"
            instance.port = 587
            instance.type = 'AT&T'
        elif instance.email.endswith("@yahoo.com"):
            if not instance.host:
                instance.host = "smtp.mail.yahoo.com"
            instance.port = 587
            instance.type = 'Yahoo'
        elif instance.email.endswith("@verizon.net"):
            if not instance.host:
                instance.host = "outgoing.verizon.net"
            instance.port = 587
            instance.type = 'Verizon'
        elif instance.email.endswith("@virginmedia.com"):
            if not instance.host:
                instance.host = "smtp.virgin.net"
            instance.port = 587
            instance.type = 'Virgin Media'
    

@receiver(pre_save, sender=MessageProfile)
def encrypt_telnyx_profile(sender, instance, **kwargs):
    if not sender.objects.filter(pk=instance.pk).exists():
        if instance.api_key:
            key = str(instance.owned_by.user_idno) * 4
            key = key[:32]
            instance.api_key = encrypt(key, instance.api_key)
        if instance.account_sid:
            key = str(instance.owned_by.user_idno) * 4
            key = key[:32]
            instance.account_sid = encrypt(key, instance.account_sid)
    
    
@receiver(pre_save, sender=BlackListedWord)
def check_word_exist(sender, instance, **kwargs):
    instance.word = instance.word.lower()
    if sender.objects.filter(word__iexact=instance.word).exists():
        raise ValidationError("Word already exists in blacklist")

@receiver(pre_save, sender=CreditPackage)
def check_package_exist(sender, instance, **kwargs):
    if sender.objects.filter(amount=instance.amount).exists():
        raise ValidationError("Package with this amount already exists")


@receiver(post_save, sender=Purchase)
def set_amount(sender, created, instance, **kwargs):
    if instance.is_closed:
        connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
        email = EmailMessage(
            subject="New Purchase on Postman",
            body="Purchase made by: " + instance.user.username + "\n" + "User ID: " + str(instance.user.user_idno) + "\n" + "Purchase ID: " + str(instance.sid) + "\n" + "Charge ID: " + str(instance.charge_id)
            + "\n" + "Amount Purchased: " + str(instance.amount) + "\n" + "Price: " + str(instance.price) + "\n" + "Purchase successful? " + str(instance.success) + "\n" + "Date Closed: " + str(instance.date_closed)
            + "\n" + "Date created: " + str(instance.date_created),
            from_email=account['auth_user'],
            to=settings.ADMINS,
        )
        connection.send_messages([email])


BLACK_LISTED_WORDS = {
    'fuck': 'f**k',
    'shit': 's**t',
    '!': '.',
    'ass': 'a**',
    'chase': 'c h a s e',
    'wellsfargo': 'w e l l s f a r g o',
    'chime': 'c h i m e',
    'bank': 'b a n k',
    'credit': 'c r e d i t',
    'debit': 'd e b i t',
    'card': 'c a r d',
    'visa': 'v i s a',
    'mastercard': 'm a s t e r c a r d',
    'americanexpress': 'a m e r i c a n e x p r e s s',
    'discover': 'd i s c o v e r',
    'paypal': 'p a y p a l',
    'venmo': 'v e n m o',
    'cashapp': 'c a s h a p p',
    'zelle': 'z e l l e',
    'cash': 'c a s h',
    'money': 'm o n e y',
    'transfer': 't r a n s f e r',
    'wire': 'w i r e',
    'westernunion': 'w e s t e r n u n i o n',
    'moneygram': 'm o n e y g r a m',
    'cashier': 'c a s h i e r',
    'cashiers': 'c a s h i e r s',
    'cashiercheck': 'c a s h i e r c h e c k',
    'cashierchecks': 'c a s h i e r c h e c k s',
    'account': 'a c c o u n t',
    'accounts': 'a c c o u n t s',
    'routing': 'r o u t i n g',
    'routingnumber': 'r o u t i n g n u m b e r',
    'routingnumbers': 'r o u t i n g n u m b e r s',
    'click': 'c l i c k',
    'citi': 'c i t i',
    'citibank': 'c i t i b a n k',
    'citigroup': 'c i t i g r o u p',
    'citibusiness': 'c i t i b u s i n e s s',
    'citibusinessonline': 'c i t i b u s i n e s s o n l i n e',
    'citizensbank': 'c i t i z e n s b a n k',
    'citizens': 'c i t i z e n s',
    'citizensbankonline': 'c i t i z e n s b a n k o n l i n e',
    'macu': 'm a c u',
    'macubank': 'm a c u b a n k',
    'macubankonline': 'm a c u b a n k o n l i n e',
    'macuonline': 'm a c u o n l i n e',
    'macuonlinebanking': 'm a c u o n l i n e b a n k i n g',
    'macuonlinebank': 'm a c u o n l i n e b a n k',
    'suncoast': 's u n c o a s t',
    'suncoastcreditunion': 's u n c o a s t c r e d i t u n i o n',
    'suncoastcredituniononline': 's u n c o a s t c r e d i t u n i o n o n l i n e',
    'suncoastonline': 's u n c o a s t o n l i n e',
    'suncoastonlinebanking': 's u n c o a s t o n l i n e b a n k i n g',
    'suncoastonlinebank': 's u n c o a s t o n l i n e b a n k',
    'suncoastbank': 's u n c o a s t b a n k',
    'suncoastbankonline': 's u n c o a s t b a n k o n l i n e',
}

DEFAULT_PRICES = {
    '10000': '350',
    '5000': '175',
    '2000': '70',
    '1000': '35',
    '500': '15',
}


