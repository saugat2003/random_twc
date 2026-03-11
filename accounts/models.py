import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model with college email verification."""

    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    anonymous_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    # Use email as login
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.email

    def regenerate_verification_token(self):
        self.email_verification_token = uuid.uuid4()
        self.save(update_fields=["email_verification_token"])
        return self.email_verification_token
