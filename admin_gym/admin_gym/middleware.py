from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import AuditoriaEvento
import json

class AuditMiddleware(MiddlewareMixin):
    """
    Middleware para auditoría de eventos críticos
    RNF-05: Logs de auditoría de eventos críticos
    """
    
    def process_request(self, request):
        # Guardar IP y timestamp para auditoría
        request.audit_ip = self.get_client_ip(request)
        request.audit_timestamp = timezone.now()
        return None
    
    def process_response(self, request, response):
        # Auditar accesos denegados (403, 401)
        if response.status_code in [401, 403]:
            self.log_audit_event(
                request=request,
                tipo_evento='acceso_denegado',
                descripcion=f'Acceso denegado a {request.path}',
                datos_adicionales={
                    'status_code': response.status_code,
                    'path': request.path,
                    'method': request.method
                }
            )
        
        return response
    
    def get_client_ip(self, request):
        """Obtener IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_audit_event(self, request, tipo_evento, descripcion, datos_adicionales=None):
        """Registrar evento de auditoría"""
        try:
            AuditoriaEvento.objects.create(
                usuario=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                tipo_evento=tipo_evento,
                descripcion=descripcion,
                ip_address=getattr(request, 'audit_ip', None),
                datos_adicionales=datos_adicionales or {}
            )
        except Exception as e:
            # No fallar si hay error en auditoría
            print(f"Error en auditoría: {e}")

class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware de seguridad adicional
    RNF-05: Control de acceso basado en roles
    """
    
    def process_request(self, request):
        # Agregar headers de seguridad
        return None
    
    def process_response(self, request, response):
        # Headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HTTPS en producción
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response

# Signals para auditoría de login/logout
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Auditar inicio de sesión"""
    try:
        AuditoriaEvento.objects.create(
            usuario=user,
            tipo_evento='login',
            descripcion=f'Usuario {user.username} inició sesión',
            ip_address=request.META.get('REMOTE_ADDR'),
            datos_adicionales={
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat()
            }
        )
    except Exception as e:
        print(f"Error auditando login: {e}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Auditar cierre de sesión"""
    try:
        if user:
            AuditoriaEvento.objects.create(
                usuario=user,
                tipo_evento='logout',
                descripcion=f'Usuario {user.username} cerró sesión',
                ip_address=request.META.get('REMOTE_ADDR'),
                datos_adicionales={
                    'timestamp': timezone.now().isoformat()
                }
            )
    except Exception as e:
        print(f"Error auditando logout: {e}")

class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware para monitoreo de rendimiento
    RNF-01: Validaciones de QR deben responder en <5 segundos
    """
    
    def process_request(self, request):
        request.start_time = timezone.now()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = (timezone.now() - request.start_time).total_seconds()
            
            # Log requests lentos (>5 segundos)
            if duration > 5.0:
                try:
                    AuditoriaEvento.objects.create(
                        usuario=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                        tipo_evento='performance_warning',
                        descripcion=f'Request lento: {request.path} ({duration:.2f}s)',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        datos_adicionales={
                            'duration_seconds': duration,
                            'path': request.path,
                            'method': request.method
                        }
                    )
                except Exception as e:
                    print(f"Error logging performance: {e}")
            
            # Agregar header de tiempo de respuesta
            response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response

class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware básico de rate limiting
    RNF-05: Seguridad - prevenir ataques de fuerza bruta
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}  # En producción usar Redis/Memcached
        super().__init__(get_response)
    
    def process_request(self, request):
        # Rate limiting básico para APIs críticas
        if request.path.startswith('/api/validate-qr/'):
            client_ip = self.get_client_ip(request)
            current_time = timezone.now()
            
            # Limpiar contadores antiguos (>1 minuto)
            self.cleanup_old_requests(current_time)
            
            # Contar requests del último minuto
            if client_ip not in self.request_counts:
                self.request_counts[client_ip] = []
            
            recent_requests = [
                req_time for req_time in self.request_counts[client_ip]
                if (current_time - req_time).total_seconds() < 60
            ]
            
            if len(recent_requests) >= 30:  # Máximo 30 requests por minuto
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': 60
                }, status=429)
            
            # Agregar request actual
            self.request_counts[client_ip].append(current_time)
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def cleanup_old_requests(self, current_time):
        """Limpiar requests antiguos para evitar memory leak"""
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                req_time for req_time in self.request_counts[ip]
                if (current_time - req_time).total_seconds() < 60
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]