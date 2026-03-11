from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.lobby, name="lobby"),
    path("room/", views.room, name="room"),
]
