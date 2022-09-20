
from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, username=None, password=None):
        if not password:
            raise ValueError("User must have a Password!")

        if not username:
            raise ValueError("User must have a username!")
        
        user = self.model(
            username=username,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        user = self.create_user(
            username=username,
            password=password,
     
        )
        user.can_send=True
        user.can_use_default=True
        user.wants_history=True
        user.wants_random=True
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    



