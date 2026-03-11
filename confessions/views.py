from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Confession

def confession_list(request):
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            # Ensure it's not too long
            content = content[:1000]
            Confession.objects.create(content=content)
            messages.success(request, "Your anonymous confession has been posted!")
            return redirect('confessions:list')
        else:
            messages.error(request, "Confession cannot be empty.")
            
    confessions = Confession.objects.all()
    return render(request, "confessions/index.html", {"confessions": confessions})
