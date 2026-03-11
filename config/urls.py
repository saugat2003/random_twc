"""
Root URL configuration for Antigravity project.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("accounts/", include("accounts.urls")),
    path("chat/", include("chat.urls")),
    path("confessions/", include("confessions.urls")),
    path("moderation/", include("moderation.urls")),
    path("api/accounts/", include("accounts.api_urls")),
    path("api/moderation/", include("moderation.api_urls")),
]
