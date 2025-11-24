from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from .models import NotificacionEnviada, NotificacionTemplate, Cliente
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Servicio para envío real de notificaciones"""
    
    @staticmethod
    def enviar_email(cliente, template, contexto_extra=None):
        """Enviar email usando template"""
        try:
            contexto = {
                'cliente': cliente,
                'nombre': cliente.nombre,
                **(contexto_extra or {})
            }
            
            # Renderizar mensaje con contexto
            mensaje_html = template.mensaje.format(**contexto)
            mensaje_texto = strip_tags(mensaje_html)
            
            # Crear email
            email = EmailMultiAlternatives(
                subject=template.asunto.format(**contexto),
                body=mensaje_texto,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[cliente.email]
            )
            email.attach_alternative(mensaje_html, "text/html")
            
            # Enviar
            resultado = email.send()
            
            # Registrar envío
            NotificacionEnviada.objects.create(
                cliente=cliente,
                template=template,
                exitoso=resultado > 0
            )
            
            return resultado > 0
            
        except Exception as e:
            logger.error(f"Error enviando email a {cliente.email}: {e}")
            NotificacionEnviada.objects.create(
                cliente=cliente,
                template=template,
                exitoso=False
            )
            return False
    
    @staticmethod
    def enviar_notificacion_racha(cliente, dias_consecutivos):
        """Enviar notificación de racha de asistencia"""
        try:
            template = NotificacionTemplate.objects.get(tipo='racha', activo=True)
            contexto = {'dias_consecutivos': dias_consecutivos}
            return NotificationService.enviar_email(cliente, template, contexto)
        except NotificacionTemplate.DoesNotExist:
            logger.warning("Template de racha no encontrado")
            return False
    
    @staticmethod
    def enviar_recordatorio_pago(cliente, dias_vencimiento):
        """Enviar recordatorio de pago"""
        try:
            template = NotificacionTemplate.objects.get(tipo='recordatorio', activo=True)
            contexto = {'dias_vencimiento': dias_vencimiento}
            return NotificationService.enviar_email(cliente, template, contexto)
        except NotificacionTemplate.DoesNotExist:
            logger.warning("Template de recordatorio no encontrado")
            return False
    
    @staticmethod
    def enviar_credenciales(email, username, password):
        """Enviar credenciales de acceso"""
        try:
            mensaje = f"""
            Bienvenido al sistema del gimnasio.
            
            Tus credenciales de acceso son:
            Usuario: {username}
            Contraseña temporal: {password}
            
            Por favor cambia tu contraseña al ingresar por primera vez.
            """
            
            send_mail(
                subject='Credenciales de acceso - Gimnasio',
                message=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )
            return True
            
        except Exception as e:
            logger.error(f"Error enviando credenciales a {email}: {e}")
            return False