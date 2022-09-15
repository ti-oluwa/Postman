import json, random
from django.conf import settings
from django.core.mail import send_mail



def set_account():
    with open(settings.STATIC_ROOT +'/images/accounts.json', 'r') as f:
        accounts = json.load(f)
    account = random.choices(accounts, k=10)[5]
    return account['auth_user'], account['auth_pass']


# send_mail('','This is test sms with smtp', 'tholuwarlarshe2003@gmail.com', ['+2349013329333',], auth_user='tholuwarlarshe2003@gmail.com', auth_password='pdtkgscfemygmbwc')