from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, EmailProfile, TelnyxProfile


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'is_staff', 'is_active', 'can_send', 'can_use_default', 'wants_history', 'wants_random')
    list_filter = ('username', 'is_staff', 'is_active', 'can_send', 'can_use_default', 'wants_history', 'wants_random')
    readonly_fields = ("id" , "date_joined" , "last_login", "user_idno")
    fieldsets = (
        (None, {'fields': ('username', 'password', 'wants_history', 'wants_random')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'can_send', 'can_use_default', )}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_staff', 'is_active', 'can_send', 'can_use_default', 'wants_history', 'wants_random')}
        ),
    )
    search_fields = ('username',)
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(EmailProfile)
admin.site.register(TelnyxProfile)