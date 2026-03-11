from django.contrib import admin
from .models import ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user_one", "user_two", "status", "started_at", "ended_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "started_at"]
    search_fields = ["id", "user_one__email", "user_two__email"]
