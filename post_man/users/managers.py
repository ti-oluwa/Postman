
from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, secret_question=None, secret_ans=None, username=None, password=None):
        if not password:
            raise ValueError("User must have a Password!")

        if not username:
            raise ValueError("User must have a username!")

        if not secret_question:
            raise ValueError("User must have a secret question!")

        if not secret_ans:
            raise ValueError("User must have a secret answer!")
        
        user = self.model(
            username=username,
        )
        user.secret_question = secret_question
        user.secret_ans = secret_ans
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, secret_question, secret_ans):
        user = self.create_user(
            username=username,
            password=password,
            secret_question=secret_question,
            secret_ans=secret_ans,
     
        )
        user.can_send=True
        user.can_use_default=True
        user.wants_history=True
        user.wants_random=True
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.is_privileged = True
        user.accepted_cookies = True
        user.save(using=self._db)
        return user

    



