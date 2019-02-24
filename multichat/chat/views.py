from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Room
from .forms import MyRoomForm

@login_required
def index(request):
    """
    Root page view. This is essentially a single-page app, if you ignore the
    login and admin parts.
    """
    # Get a list of rooms, ordered alphabetically
    rooms = Room.objects.order_by("title")

    if request.method == "POST":
        form = MyRoomForm(request.POST)
        if form.is_valid():
            model_instance = form.save(commit=False)
            model_instance.save()
            return redirect('/')
    else:
        form = MyRoomForm()

        # Render that in the index template
        return render(request, "index.html", {
            "rooms": rooms,
            "createRoomForm": form
        })
