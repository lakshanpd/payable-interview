from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with a required, unique email.

    We keep ``username`` (inherited from AbstractUser) as the login
    identifier for Django internals, but registration/login in this API
    are keyed on email for a friendlier mobile UX.
    """

    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.username
