from django                         import forms
from client.models                  import Client
from supervisor.models.supervisor   import Supervisor
from django.contrib.auth.hashers    import check_password

class SupervisorLoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'id': 'email',
                'name': 'email',
                'placeholder': 'Email',
                'class': 'login__input'
            }
        )
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                'id': 'password',
                'name': 'password',
                'placeholder': 'Password',
                'class': 'login__input'
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                supervisor = Supervisor.objects.get(email=email)
            except Supervisor.DoesNotExist:
                raise forms.ValidationError("Invalid email or password!!!")

            if not supervisor.user or not check_password(password, supervisor.user.password):
                raise forms.ValidationError("Invalid email or password!!!")
        
        return cleaned_data


class ClientLoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'id': 'email',
                'name': 'email',
                'placeholder': 'Email',
                'class': 'login__input'
            }
        )
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                'id': 'password',
                'name': 'password',
                'placeholder': 'Password',
                'class': 'login__input'
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                client = Client.objects.get(email=email)
            except Client.DoesNotExist:
                raise forms.ValidationError("Invalid email or password!!!")

            if not client.user or not check_password(password, client.user.password):
                raise forms.ValidationError("Invalid email or password!!!")
        
        return cleaned_data