from django.contrib import admin
from .models import TextMessage, PhoneNumber, Email, EmailAddress, Attachment, BlackListedWord

admin.site.register(PhoneNumber)
admin.site.register(Email)
admin.site.register(TextMessage)
admin.site.register(EmailAddress)
admin.site.register(Attachment)
admin.site.register(BlackListedWord)