from django.urls import path
from . import views

app_name = 'confessions'

urlpatterns = [
    path('', views.confession_list, name='list'),
]
