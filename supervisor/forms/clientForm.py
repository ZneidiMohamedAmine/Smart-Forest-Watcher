from django         import forms
from client.models  import Client

class ClientForm(forms.ModelForm):
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        label="Confirm Password",
        required=False
    )

    class Meta:
        model = Client
        fields = ['firstName', 'lastName', 'email', 'phone', 'username', 'password', 'image']
        widgets = {
            'firstName': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'lastName': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file'})
        }

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        # Force required fields
        self.fields['firstName'].required = True
        self.fields['lastName'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['username'].required = True
        
        # Password is optional in both create and edit: leaving it blank on
        # create generates a random one emailed to the new agent to change
        # later, and leaving it blank on edit keeps the current password.
        self.fields['password'].required = False
        self.fields['password_confirmation'].required = False

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("password_confirmation")
        phone = cleaned_data.get("phone")

        if phone is not None:
            phone_str = str(phone)
            if not phone_str.isdigit() or len(phone_str) != 8:
                self.add_error('phone', 'Phone number must be exactly 8 digits.')

        # Password is optional — if left blank, Client.save() generates a
        # random one and emails it to the new agent. If either field is
        # filled, both must be present and match.
        if password or confirm_password:
            if not password or not confirm_password:
                raise forms.ValidationError("Fill in both password fields, or leave both blank to auto-generate one.")
            if password != confirm_password:
                raise forms.ValidationError("The passwords entered do not match.")

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.instance and self.instance.pk:
            if Client.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This email is already in use. Please provide a different email address.")
        else:
            if Client.objects.filter(email=email).exists():
                raise forms.ValidationError("This email is already in use. Please provide a different email address.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if self.instance and self.instance.pk:
            if Client.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This username is already taken. Please choose a different username.")
        else:
            if Client.objects.filter(username=username).exists():
                raise forms.ValidationError("This username is already taken. Please choose a different username.")
        return username
