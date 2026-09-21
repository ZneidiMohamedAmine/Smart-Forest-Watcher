from django import forms
from .models import Drone


class DroneForm(forms.ModelForm):
    class Meta:
        model = Drone
        fields = ['name', 'drone_id', 'api_key', 'project', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Drone Alpha'}),
            'drone_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique identifier (e.g. drone-001)'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Secret key shared with the onboard unit'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
