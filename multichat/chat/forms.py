from django.forms import ModelForm
from .models import Room

class MyRoomForm(ModelForm):
    class Meta:
        model = Room
        fields = ['title']