import uuid

from django.conf import settings
from django.db import models


class Report(models.Model):
    """User-submitted report for inappropriate behavior."""

    REASON_CHOICES = [
        ("harassment", "Harassment"),
        ("explicit", "Explicit Content"),
        ("spam", "Spam"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_filed",
    )
    reported_session = models.ForeignKey(
        "chat.ChatSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_resolved",
    )

    class Meta:
        db_table = "moderation_report"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report {self.id} — {self.reason} ({self.status})"


class IPBlock(models.Model):
    """Blocked IP addresses."""

    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True, default="")
    blocked_at = models.DateTimeField(auto_now_add=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        db_table = "moderation_ip_block"

    def __str__(self):
        return f"Blocked: {self.ip_address}"
