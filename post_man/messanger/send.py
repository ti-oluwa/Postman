import json, random
from django.conf import settings
from django.core.mail import send_mail



# def set_account():
#     with open(settings.STATIC_ROOT +'/images/accounts.json', 'r') as f:
#         accounts = json.load(f)
#     account = random.choices(accounts, k=10)[5]
#     return account['auth_user'], account['auth_pass']

from twilio.rest import Client

# Your Account SID from twilio.com/console
account_sid = ""
# Your Auth Token from twilio.com/console
auth_token  = ""

client = Client(account_sid, auth_token)

message = client.messages.create(
    to="", 
    from_="",
    body="Hello from Python!")

print(message.sid, message.status)