from django.contrib import admin
from .models import TextMessage, PhoneNumber, Email, EmailAddress, Attachment

admin.site.register(PhoneNumber)
admin.site.register(Email)
admin.site.register(TextMessage)
admin.site.register(EmailAddress)
admin.site.register(Attachment)