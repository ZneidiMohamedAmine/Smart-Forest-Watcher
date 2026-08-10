from django import forms

from supervisor.models.ttn_credential import TTNCredential


class TTNCredentialForm(forms.ModelForm):
    class Meta:
        model = TTNCredential
        fields = ['name', 'username', 'api_key']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. my-weather-station'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. my-app@ttn'}),
            'api_key': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'TTN API key'}, render_value=True),
        }
