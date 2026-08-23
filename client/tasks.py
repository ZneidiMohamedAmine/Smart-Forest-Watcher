from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task(name="send_client_welcome_email")
def send_client_welcome_email(client_email, client_first_name, client_last_name, password, is_temporary_password=True):
    context = {
        'client': {'firstName': client_first_name, 'lastName': client_last_name, 'email': client_email},
        'password': password,
        'is_temporary_password': is_temporary_password,
        'image_url': 'https://smartforgreen.com/wp-content/uploads/2023/07/featured_page.png',
    }
    subject = 'Welcome to Smart For Green'
    html_message = render_to_string('message.html', context)
    plain_message = strip_tags(html_message)
    from_email = 'From <mohamedhedigharbi101@gmail.com>'

    send_mail(subject, plain_message, from_email, [client_email], html_message=html_message)
