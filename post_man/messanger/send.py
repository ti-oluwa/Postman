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
account_sid = "AC5cacfa4472bd3612fe6fbed7e58f2538"
# Your Auth Token from twilio.com/console
auth_token  = "62fa2d38dbdf19b120dc3d861b287e39"

client = Client(account_sid, auth_token)

message = client.messages.create(
    to="+23409013329333", 
    from_="+18065831058",
    body="Hello from Python!")

print(message.sid, message.status)