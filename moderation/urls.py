from django.urls import path
from . import views

app_name = "moderation"

urlpatterns = [
    path("report/", views.submit_report, name="submit_report"),
]
