from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import UserRegistrationForm
from .models import CustomUser, EmailProfile, MessageProfile, Purchase, CreditPackage


class CustomUserAdmin(UserAdmin):
    add_form = UserRegistrationForm
    model = CustomUser
    list_display = ('username', 'is_staff', 'is_active', 'can_send', 'can_use_default', 'wants_history', 'wants_random', 'accepted_cookies', 'rejected_cookies', 'accepted_pp', 'is_privileged')
    list_filter = ('username', 'is_staff', 'is_active', 'can_send', 'can_use_default', 'wants_history', 'wants_random', 'accepted_cookies', 'rejected_cookies', 'accepted_pp', 'is_privileged')
    readonly_fields = ("id" , "date_joined" , "last_login", "user_idno", 'accepted_cookies', 'rejected_cookies', 'accepted_pp')
    fieldsets = (
        (None, {'fields': ('username', 'password', 'wants_history', 'wants_random', 'wants_default', 'accepted_cookies', 'rejected_cookies', 'accepted_pp')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'can_send', 'can_use_default', 'message_credit', 'is_privileged')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_staff', 'is_active', 'can_send', 'can_use_default', 'wants_history', 'wants_random', 'message_credit', 'is_privileged')}
        ),
    )
    search_fields = ('username',)
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(EmailProfile)
admin.site.register(MessageProfile)
admin.site.register(Purchase)
admin.site.register(CreditPackage)