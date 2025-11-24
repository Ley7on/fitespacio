"""
Sistema de manejo de errores global para admin_gym
"""
import logging
from django.http import JsonResponse, HttpResponseServerError
from django.shortcuts import render
from django.utils.html import escape
from django.conf import settings

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
    return render(request, 'admin_gym/errors/404.html', status=404)

def handler500(request):
    """Manejador personalizado para errores 500"""
    logger.error(f"500 - Error interno del servidor en: {request.path}")
    return render(request, 'admin_gym/errors/500.html', status=500)

def handler403(request, exception):
    """Manejador personalizado para errores 403"""
    logger.warning(f"403 - Acceso denegado para {request.user.username}: {request.path}")
    return render(request, 'admin_gym/errors/403.html', status=403)