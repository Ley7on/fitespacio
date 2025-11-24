from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)

class PushNotificationService:
    @staticmethod
    def send_push_notification(user, title, message, data=None):
        """Enviar notificación push a un usuario"""
        try:
            # Por ahora simulamos el envío
            # En producción aquí iría la integración con Firebase FCM
            logger.info(f"Push notification enviada a {user.username}: {title}")
            return True
        except Exception as e:
            logger.error(f"Error enviando push notification: {e}")
            return False
    
    @staticmethod
    def notify_routine_assigned(user, rutina_name):
        """Notificación de rutina asignada"""
        return PushNotificationService.send_push_notification(
            user=user,
            title="Nueva rutina asignada",
            message=f"Tu entrenador te ha asignado: {rutina_name}",
            data={'type': 'routine_assigned', 'action': 'view_routines'}
        )
    
    @staticmethod
    def notify_payment_reminder(user, days_left):
        """Notificación de recordatorio de pago"""
        return PushNotificationService.send_push_notification(
            user=user,
            title="Recordatorio de pago",
            message=f"Tu membresía vence en {days_left} días",
            data={'type': 'payment_reminder', 'action': 'view_payments'}
        )
    
    @staticmethod
    def notify_session_reminder(user, session_time):
        """Recordatorio de sesión"""
        return PushNotificationService.send_push_notification(
            user=user,
            title="Recordatorio de entrenamiento",
            message=f"Tienes una sesión programada a las {session_time}",
            data={'type': 'session_reminder', 'action': 'view_calendar'}
        )

@csrf_exempt
@require_http_methods(["POST"])
def register_push_subscription(request):
    """Registrar suscripción push del usuario"""
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')
        
        if request.user.is_authenticated and subscription:
            # Aquí guardaríamos la suscripción en la base de datos
            # Por ahora solo logueamos
            logger.info(f"Suscripción push registrada para {request.user.username}")
            return JsonResponse({'success': True})
        
        return JsonResponse({'success': False, 'error': 'Usuario no autenticado'})
        
    except Exception as e:
        logger.error(f"Error registrando suscripción push: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def send_test_notification(request):
    """Enviar notificación de prueba"""
    try:
        if request.user.is_authenticated:
            result = PushNotificationService.send_push_notification(
                user=request.user,
                title="Notificación de prueba",
                message="¡Las notificaciones están funcionando correctamente!",
                data={'type': 'test'}
            )
            return JsonResponse({'success': result})
        
        return JsonResponse({'success': False, 'error': 'Usuario no autenticado'})
        
    except Exception as e:
        logger.error(f"Error enviando notificación de prueba: {e}")
        return JsonResponse({'success': False, 'error': str(e)})