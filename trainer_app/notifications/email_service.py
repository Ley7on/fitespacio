from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_notification_email(to_email, subject, template_name, context=None):
        """Enviar email con template HTML"""
        try:
            if context is None:
                context = {}
            
            # Renderizar template HTML
            html_content = render_to_string(f'emails/{template_name}.html', context)
            text_content = strip_tags(html_content)
            
            # Crear email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar
            email.send()
            logger.info(f"Email enviado a {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email a {to_email}: {e}")
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """Email de bienvenida"""
        return EmailService.send_notification_email(
            to_email=user.email,
            subject="¡Bienvenido a FitSpace!",
            template_name="welcome",
            context={'user': user}
        )
    
    @staticmethod
    def send_payment_reminder(cliente):
        """Recordatorio de pago"""
        return EmailService.send_notification_email(
            to_email=cliente.email,
            subject="Recordatorio de Pago - FitSpace",
            template_name="payment_reminder",
            context={'cliente': cliente}
        )
    
    @staticmethod
    def send_payment_confirmation(cliente, pago):
        """Confirmación de pago"""
        return EmailService.send_notification_email(
            to_email=cliente.email,
            subject="Pago Confirmado - FitSpace",
            template_name="payment_confirmation",
            context={'cliente': cliente, 'pago': pago}
        )
    
    @staticmethod
    def send_routine_assigned(cliente, rutina, entrenador):
        """Nueva rutina asignada"""
        return EmailService.send_notification_email(
            to_email=cliente.email,
            subject="Nueva Rutina Asignada - FitSpace",
            template_name="routine_assigned",
            context={
                'cliente': cliente,
                'rutina': rutina,
                'entrenador': entrenador
            }
        )
    
    @staticmethod
    def send_credentials_email(user, password, user_type='cliente'):
        """Enviar credenciales de acceso"""
        return EmailService.send_notification_email(
            to_email=user.email,
            subject="Tus credenciales de acceso - FitSpace",
            template_name="credentials",
            context={
                'user': user,
                'password': password,
                'user_type': user_type,
                'login_url': 'http://localhost:8001/login/'
            }
        )