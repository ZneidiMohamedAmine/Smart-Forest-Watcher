from django.contrib.auth.models     import User, BaseUserManager
from django.db                      import models
from django.contrib.auth.hashers    import make_password, check_password
from django.core.exceptions         import ValidationError
from django.utils.crypto            import get_random_string

#crée table client dans DB
class Client(models.Model):
    firstName   = models.CharField(max_length=25, blank=True)
    lastName    = models.CharField(max_length=25, blank=True)
    email       = models.EmailField(max_length=255, unique=True)
    phone       = models.IntegerField(blank=True)
    username    = models.CharField(max_length=30)
    password    = models.CharField(max_length=128)
    image       = models.ImageField(null=True, blank=True, upload_to='img')
    user        = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
#relation avec User
    def __str__(self):
        return f'{self.firstName} {self.lastName}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new:
            if User.objects.filter(username=self.username).exists():
                raise ValidationError(f"Username {self.username} already exists.")

            # Use the password the supervisor set in the form, if any — only
            # fall back to a random generated one (emailed for the agent to
            # change later) when the field was left blank.
            is_temporary_password = not bool(self.password)
            plain_password = self.password if self.password else get_random_string(length=12)

            self.password = make_password(plain_password)
            self.user = User.objects.create_user(username=self.username, email=self.email, password=plain_password)
            password_to_send = plain_password
        else:
            if self.user:
                self.user.username = self.username
                self.user.email = self.email
                if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$')):
                    self.user.set_password(self.password)
                    self.password = make_password(self.password)
                self.user.save()
            password_to_send = None

        super().save(*args, **kwargs)

        if is_new:
            from client.tasks import send_client_welcome_email
            send_client_welcome_email.delay(
                self.email, self.firstName, self.lastName, password_to_send, is_temporary_password
            )

    def delete(self, *args, **kwargs):
        if self.user:
            self.user.delete()
        super().delete(*args, **kwargs)

    def clean(self):
        if not self.firstName and not self.lastName:
            raise ValidationError("Either first name or last name must be provided.")
        if Client.objects.exclude(pk=self.pk).filter(email=self.email).exists():
            raise ValidationError("This email is already in use.")
#Admin يعمل client
#save() يتنفذ
#User يتخلق
#password يتخلق
#email يتبعث
#client يعمل login
# إنشاء client
# إنشاء user login
#generate password
#hash password
#send email
#update user
#delete user
#validation     


class ClientAuthToken(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='auth_token')
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, client):
        key = get_random_string(64)
        token, _ = cls.objects.update_or_create(client=client, defaults={'key': key})
        return token

    def __str__(self):
        return f'token for {self.client.email}'


class MobileNotification(models.Model):
    user_id = models.EmailField(db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    camera = models.ForeignKey(
        'camera_management.Camera',
        on_delete=models.SET_NULL,
        related_name='mobile_notifications',
        null=True,
        blank=True,
    )
    detection = models.ForeignKey(
        'camera_management.Detection',
        on_delete=models.SET_NULL,
        related_name='mobile_notifications',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.user_id} - {self.title}'
