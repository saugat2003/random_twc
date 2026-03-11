from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def lobby(request):
    """Chat lobby — matchmaking waiting room."""
    return render(request, "chat/lobby.html")


@login_required
def room(request):
    """Active chat room (text + video)."""
    return render(request, "chat/room.html")
