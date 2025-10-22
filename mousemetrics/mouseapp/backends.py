from typing import Any, override
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.http import HttpRequest


class EmailBackend(ModelBackend):

    @override
    def authenticate(
        self,
        request: HttpRequest,
        username: str | None = None,
        password: str | None = None,
        **kwargs: dict[str, Any],
    ) -> User | None:
        UserModel = get_user_model()
        try:
            user: User = UserModel.objects.get(email__exact=username)
        except UserModel.DoesNotExist:
            return None  # user not found

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
