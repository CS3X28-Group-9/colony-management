from typing import Any, override
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import HttpRequest


class EmailBackend(ModelBackend):

    @override
    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: dict[str, Any],
    ) -> User | None:
        try:
            user: User = User.objects.get(email__exact=username)
        except User.DoesNotExist:
            return None  # user not found

        if (
            password
            and user.check_password(password)
            and self.user_can_authenticate(user)
        ):
            return user
        return None
