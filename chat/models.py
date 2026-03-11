import uuid

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """Tracks a chat session between two anonymous users."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("ended", "Ended"),
        ("skipped", "Skipped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_one = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sessions_as_one",
    )
    user_two = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sessions_as_two",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_session"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session {self.id} ({self.status})"
