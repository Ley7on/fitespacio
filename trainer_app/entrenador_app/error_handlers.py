"""
Sistema de manejo de errores global para entrenador_app
"""
import logging
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils.html import escape
from django.conf import settings
from django.template import TemplateDoesNotExist

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Manejador centralizado de errores"""
    
    @staticmethod
    def handle_validation_error(error, context=""):
        """Maneja errores de validación"""
        error_msg = f"Error de validación{f' en {context}' if context else ''}: {str(error)}"
        logger.warning(error_msg)
        return error_msg
    
    @staticmethod
    def handle_database_error(error, context=""):
        """Maneja errores de base de datos"""
        error_msg = f"Error de base de datos{f' en {context}' if context else ''}"
        logger.error(f"{error_msg}: {str(error)}")
        return "Error interno del sistema. Intente nuevamente."
    
    @staticmethod
    def handle_permission_error(user, action):
        """Maneja errores de permisos"""
        error_msg = f"Usuario {user.username} sin permisos para: {action}"
        logger.warning(error_msg)
        return "No tiene permisos para realizar esta acción"
    
    @staticmethod
    def safe_json_response(data=None, error=None, status=200):
        """Respuesta JSON segura"""
        if error:
            return JsonResponse({
                'success': False,
                'error': escape(str(error))
            }, status=status)
        
        return JsonResponse({
            'success': True,
            'data': data or {}
        }, status=status)

def handler404(request, exception):
    """Manejador personalizado para errores 404"""
    logger.warning(f"404 - Página no encontrada: {request.path}")
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Manejador personalizado para errores 500"""
    logger.error(f"500 - Error interno del servidor en: {request.path}")
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """Manejador personalizado para errores 403"""
    logger.warning(f"403 - Acceso denegado para {request.user.username}: {request.path}")
    return render(request, 'errors/403.html', status=403)


def csrf_failure(request, reason=""):
    """Vista personalizada para fallos CSRF que registra información útil para
    depuración en desarrollo.

    Registra el token enviado en POST, el header X-CSRFToken y las cookies
    disponibles para ayudar a localizar problemas de desajuste de nombres o
    ausencia de cookies.
    """
    try:
        post_token = request.POST.get('csrfmiddlewaretoken')
    except Exception:
        post_token = None

    header_token = request.META.get('HTTP_X_CSRFTOKEN')
    cookies = dict(request.COOKIES)

    logger.error("CSRF failure: reason=%s", reason)
    logger.error("CSRF failure: POST csrfmiddlewaretoken=%s", post_token)
    logger.error("CSRF failure: HTTP_X_CSRFTOKEN=%s", header_token)
    logger.error("CSRF failure: request.COOKIES keys=%s", list(cookies.keys()))

    # In DEBUG show a simple template if available, otherwise return 403 page
    context = {
        'reason': reason,
        'post_token_present': bool(post_token),
        'header_token_present': bool(header_token),
        'cookies': cookies,
    }

    # Try to render the project's 403 template if present. If it doesn't exist
    # (TemplateDoesNotExist), return a minimal 403 response so we don't raise
    # a new template error while handling a CSRF failure.
    try:
        return render(request, 'errors/403.html', context=context, status=403)
    except TemplateDoesNotExist:
        # Do not leak tokens or cookies in the response body; point to logs
        message = (
            "403 Forbidden: CSRF verification failed. "
            "Check server logs for details (django.log)."
        )
        return HttpResponseForbidden(message)