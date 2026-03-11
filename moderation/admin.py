from django.contrib import admin
from .models import Report, IPBlock


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        "id", "reporter", "reason", "status", "reported_session", "created_at",
    ]
    list_filter = ["reason", "status"]
    readonly_fields = ["id", "created_at"]
    search_fields = ["reporter__email", "description"]
    actions = ["mark_reviewed", "mark_resolved", "dismiss_reports"]

    @admin.action(description="Mark as reviewed")
    def mark_reviewed(self, request, queryset):
        queryset.update(status="reviewed")

    @admin.action(description="Mark as resolved")
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(status="resolved", resolved_at=timezone.now(), resolved_by=request.user)

    @admin.action(description="Dismiss reports")
    def dismiss_reports(self, request, queryset):
        queryset.update(status="dismissed")


@admin.register(IPBlock)
class IPBlockAdmin(admin.ModelAdmin):
    list_display = ["ip_address", "reason", "blocked_at", "blocked_by"]
    search_fields = ["ip_address"]
