from django                         import forms
from client.models                  import Client
from supervisor.models.project      import Project
from supervisor.models.localisation import Localisation



class CustomModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.gouvernorat_libelle}, {obj.delegation_libelle}, {obj.localite_libelle}"

class ProjectForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        required=True,
        empty_label='None',
        widget=forms.Select(attrs={
            'name': 'client',
            'class': 'form-control',
            'placeholder': 'Select Client', 
            'id': 'projectClient'
        })
    )
    city = CustomModelChoiceField(
        queryset=Localisation.objects.all(),
        required=True,
        empty_label='Select Location',
        widget=forms.Select(attrs={
            'name': 'city',
            'class': 'form-control',
            'id': 'regionName'
        })
    )

    class Meta:
        model = Project
        fields = ['name', 'city', 'descp', 'client', 'piece_joindre', 'date_debut', 'date_fin']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Project Name', 
                'required': True,
                'id': 'projectName'
            }),
            'descp': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Project Description',
                'rows': 2,  
                'id': 'projectDescription'
            }),
            'piece_joindre': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'id': 'projectContract',
                'required': True,
            }),
            'date_debut': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local',
                'id': 'projectStartDate'
            }, format='%Y-%m-%dT%H:%M'),
            'date_fin': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local',
                'id': 'projectEndDate'
            }, format='%Y-%m-%dT%H:%M')
        }

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        #? Handle the datetime-local input format for browser compatibility
        self.fields['date_debut'].input_formats = ('%Y-%m-%dT%H:%M',)
        self.fields['date_fin'].input_formats = ('%Y-%m-%dT%H:%M',)

    def clean_client(self):
        # An agent manages exactly one project (Project.client is a
        # OneToOneField) — surface that as a friendly form error instead of
        # letting the save fail with a raw IntegrityError.
        client = self.cleaned_data.get('client')
        if client is None:
            return client
        existing = Project.objects.filter(client=client).exclude(pk=self.instance.pk).first()
        if existing:
            raise forms.ValidationError(
                f"{client.firstName} {client.lastName} already manages a project ({existing.name}). "
                "An agent can only have one project."
            )
        return client