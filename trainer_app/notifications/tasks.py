from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_welcome_email_task(user_id):
    """Tarea para enviar email de bienvenida"""
    try:
        user = User.objects.get(id=user_id)
        result = EmailService.send_welcome_email(user)
        logger.info(f"Email de bienvenida enviado a {user.email}: {result}")
        return result
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado")
        return False
    except Exception as e:
        logger.error(f"Error enviando email de bienvenida: {e}")
        return False

@shared_task
def send_credentials_email_task(user_id, password, user_type='cliente'):
    """Tarea para enviar credenciales por email"""
    try:
        user = User.objects.get(id=user_id)
        result = EmailService.send_credentials_email(user, password, user_type)
        logger.info(f"Credenciales enviadas a {user.email}: {result}")
        return result
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado")
        return False
    except Exception as e:
        logger.error(f"Error enviando credenciales: {e}")
        return False

@shared_task
def send_payment_reminder_task(cliente_id):
    """Tarea para enviar recordatorio de pago"""
    try:
        from entrenador_app.admin_gym_models import AdminGymCliente
        cliente = AdminGymCliente.objects.get(id=cliente_id)
        result = EmailService.send_payment_reminder(cliente)
        logger.info(f"Recordatorio de pago enviado a {cliente.email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error enviando recordatorio de pago: {e}")
        return False

@shared_task
def send_routine_assigned_task(cliente_id, rutina_id, entrenador_id):
    """Tarea para notificar rutina asignada"""
    try:
        from entrenador_app.admin_gym_models import AdminGymCliente, AdminGymRutina
        cliente = AdminGymCliente.objects.get(id=cliente_id)
        rutina = AdminGymRutina.objects.get(id=rutina_id)
        entrenador = User.objects.get(id=entrenador_id)
        
        result = EmailService.send_routine_assigned(cliente, rutina, entrenador)
        logger.info(f"Notificación de rutina enviada a {cliente.email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error enviando notificación de rutina: {e}")
        return False

@shared_task
def check_payment_expiration():
    """Tarea programada para verificar vencimientos de pago"""
    try:
        from entrenador_app.admin_gym_models import AdminGymCliente
        from datetime import date
        
        # Clientes que vencen en 3 días
        fecha_limite = date.today() + timedelta(days=3)
        clientes_por_vencer = AdminGymCliente.objects.filter(
            fecha_vencimiento__lte=fecha_limite,
            estado_membresia='activa',
            activo=True
        )
        
        count = 0
        for cliente in clientes_por_vencer:
            send_payment_reminder_task.delay(cliente.id)
            count += 1
        
        logger.info(f"Enviados {count} recordatorios de pago")
        return count
        
    except Exception as e:
        logger.error(f"Error verificando vencimientos: {e}")
        return 0

@shared_task
def update_expired_memberships():
    """Tarea para actualizar membresías vencidas"""
    try:
        from entrenador_app.admin_gym_models import AdminGymCliente
        from datetime import date
        
        # Actualizar clientes vencidos
        clientes_vencidos = AdminGymCliente.objects.filter(
            fecha_vencimiento__lt=date.today(),
            estado_membresia='activa'
        )
        
        count = clientes_vencidos.update(estado_membresia='vencida')
        logger.info(f"Actualizadas {count} membresías vencidas")
        return count
        
    except Exception as e:
        logger.error(f"Error actualizando membresías: {e}")
        return 0