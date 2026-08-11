from django.contrib.auth.models     import User
from django.db                      import models
from django.contrib.auth.hashers    import make_password
from django.core.exceptions         import ValidationError

class Supervisor(models.Model):
    firstName   = models.CharField(max_length=25)
    lastName    = models.CharField(max_length=25)
    phoneNumber = models.CharField(max_length=12)
    username    = models.CharField(max_length=30)
    password    = models.CharField(max_length=128)
    email       = models.EmailField(max_length=255, unique=True)
    user        = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    # Global admins see/manage every project (legacy behavior, preserved for
    # existing accounts via migration). Non-admins are restricted to the
    # projects explicitly assigned to them below.
    is_admin    = models.BooleanField(default=False, help_text="Can see and manage every project, not just assigned ones.")
    projects    = models.ManyToManyField('supervisor.Project', blank=True, related_name='assigned_supervisors')

    def save(self, *args, **kwargs):
        if not self.pk:  
            if User.objects.filter(username=self.username).exists():
                raise ValidationError(f"Username {self.username} already exists.")
            
            # Store plain for create_user (which hashes), then hash for self.password
            plain_password = self.password
            self.password = make_password(plain_password)
            self.user = User.objects.create_user(username=self.username, email=self.email, password=plain_password)
        else:
            if self.user:
                self.user.username = self.username
                self.user.email = self.email
                # Only update/hash if the password looks like plain text
                if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$')):
                    self.user.set_password(self.password)
                    self.password = make_password(self.password)
                self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstName} {self.lastName}"
