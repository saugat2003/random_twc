from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "email", "username", "is_email_verified", "is_banned",
        "is_active", "is_staff", "created_at",
    ]
    list_filter = ["is_email_verified", "is_banned", "is_active", "is_staff"]
    search_fields = ["email", "username"]
    readonly_fields = ["anonymous_id", "email_verification_token", "created_at"]
    actions = ["ban_users", "unban_users", "verify_emails"]

    @admin.action(description="Ban selected users")
    def ban_users(self, request, queryset):
        queryset.update(is_banned=True)

    @admin.action(description="Unban selected users")
    def unban_users(self, request, queryset):
        queryset.update(is_banned=False)

    @admin.action(description="Mark emails as verified")
    def verify_emails(self, request, queryset):
        queryset.update(is_email_verified=True)
