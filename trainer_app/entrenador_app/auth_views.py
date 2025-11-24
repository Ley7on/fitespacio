from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def is_profesor(user):
    """Verifica si el usuario es profesor consultando la BD"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM admin_gym_profesor WHERE user_id = %s",
                [user.id]
            )
            return cursor.fetchone()[0] > 0
    except:
        return False

def is_cliente(user):
    """Verifica si el usuario es cliente consultando la BD"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM admin_gym_cliente WHERE user_id = %s AND activo = 1",
                [user.id]
            )
            return cursor.fetchone()[0] > 0
    except:
        return False

def require_role(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if role == 'alumno':
                if is_cliente(request.user) or (not request.user.is_staff and not request.user.is_superuser and not is_profesor(request.user)):
                    return view_func(request, *args, **kwargs)
            elif role == 'entrenador':
                if request.user.is_staff or request.user.is_superuser or is_profesor(request.user):
                    return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permisos para acceder a esta página")
        return _wrapped_view
    return decorator

def validar_rut(rut):
    """Valida formato y dígito verificador de RUT chileno"""
    import re
    if not re.match(r'^[0-9]{7,8}-[0-9kK]{1}$', rut):
        return False
    
    numero, dv = rut.split('-')
    suma = 0
    multiplicador = 2
    
    for i in range(len(numero) - 1, -1, -1):
        suma += int(numero[i]) * multiplicador
        multiplicador = 7 if multiplicador == 7 else multiplicador + 1
        if multiplicador > 7:
            multiplicador = 2
    
    resto = suma % 11
    dv_calculado = str(resto) if resto < 2 else 'k' if resto == 10 else str(11 - resto)
    
    return dv.lower() == dv_calculado.lower()

def formatear_rut_con_puntos(rut):
    """Convierte RUT sin puntos a formato con puntos"""
    # Remover guión y espacios
    rut_limpio = rut.replace('-', '').replace(' ', '').upper()
    
    if len(rut_limpio) < 2:
        return rut
    
    # Separar número y dígito verificador
    numero = rut_limpio[:-1]
    dv = rut_limpio[-1]
    
    # Agregar puntos cada 3 dígitos desde la derecha
    numero_formateado = ''
    for i, digito in enumerate(reversed(numero)):
        if i > 0 and i % 3 == 0:
            numero_formateado = '.' + numero_formateado
        numero_formateado = digito + numero_formateado
    
    return f"{numero_formateado}-{dv}"

@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on user role
        if request.user.is_staff or request.user.is_superuser or is_profesor(request.user):
            return redirect('dashboard')  # Entrenador dashboard
        else:
            return redirect('alumno:dashboard')  # Alumno dashboard

    if request.method == 'POST':
        username_input = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        logger.info(f"Intento de login - Entrada: {username_input}")

        # Buscar por RUT en todas las tablas
        username_for_auth = None
        
        # Generar variantes del RUT para búsqueda
        rut_sin_puntos = username_input.replace('.', '').replace(' ', '')
        rut_con_puntos = formatear_rut_con_puntos(rut_sin_puntos)
        variantes_rut = [username_input, rut_sin_puntos, rut_con_puntos]
        
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                logger.info(f"Buscando RUT con variantes: {variantes_rut}")
                
                # Buscar en clientes
                for rut_variant in variantes_rut:
                    cursor.execute(
                        "SELECT user_id, nombre, activo FROM admin_gym_cliente WHERE rut = %s",
                        [rut_variant]
                    )
                    cliente_result = cursor.fetchone()
                    
                    if cliente_result:
                        logger.info(f"Cliente encontrado - RUT: {rut_variant}, Nombre: {cliente_result[1]}, Activo: {cliente_result[2]}, User_ID: {cliente_result[0]}")
                        if cliente_result[2]:  # Solo si está activo
                            try:
                                user_obj = User.objects.get(id=cliente_result[0])
                                username_for_auth = user_obj.username
                                logger.info(f"Usuario cliente mapeado: {username_for_auth}")
                                break
                            except User.DoesNotExist:
                                logger.error(f"Usuario Django no existe para cliente ID: {cliente_result[0]}")
                        else:
                            logger.warning(f"Cliente inactivo: {rut_variant}")
                
                # Buscar en profesores
                if not username_for_auth:
                    for rut_variant in variantes_rut:
                        cursor.execute(
                            "SELECT user_id, nombre FROM admin_gym_profesor WHERE rut = %s",
                            [rut_variant]
                        )
                        profesor_result = cursor.fetchone()
                        
                        if profesor_result:
                            logger.info(f"Profesor encontrado - RUT: {rut_variant}, Nombre: {profesor_result[1]}, User_ID: {profesor_result[0]}")
                            try:
                                user_obj = User.objects.get(id=profesor_result[0])
                                username_for_auth = user_obj.username
                                logger.info(f"Usuario profesor mapeado: {username_for_auth}")
                                break
                            except User.DoesNotExist:
                                logger.error(f"Usuario Django no existe para profesor ID: {profesor_result[0]}")
                            
        except Exception as e:
            logger.error(f"Error buscando usuario por RUT: {e}")
        
        # Si no se encontró por RUT, intentar username/email directo
        if not username_for_auth:
            logger.info(f"No se encontró por RUT, intentando username/email: {username_input}")
            username_for_auth = username_input
            
            # Si parece email, buscar por email
            if '@' in username_input and not User.objects.filter(username=username_input).exists():
                try:
                    user_by_email = User.objects.get(email=username_input)
                    username_for_auth = user_by_email.username
                    logger.info(f"Usuario encontrado por email: {username_for_auth}")
                except User.DoesNotExist:
                    logger.warning(f"No se encontró usuario con email: {username_input}")

        if username_for_auth:
            user = authenticate(request, username=username_for_auth, password=password)
            logger.info(f"Resultado de authenticate: {user is not None}")

            if user is not None:
                logger.info(f"Login exitoso para {username_input}")
                login(request, user)
                if user.is_staff or user.is_superuser or is_profesor(user):
                    return redirect('dashboard')
                else:
                    return redirect('alumno:dashboard')
            else:
                logger.warning(f"Credenciales incorrectas para {username_input} (username_for_auth: {username_for_auth})")
                messages.error(request, 'RUT o contraseña incorrectos')
        else:
            logger.warning(f"No se encontró usuario para: {username_input}")
            messages.error(request, 'RUT no registrado en el sistema')

    # Render the login template and explicitly set the CSRF cookie to the
    # current token to avoid mismatches when the browser has stale cookies
    # (e.g., previously used custom cookie name). This does not disable CSRF
    # protection; it simply ensures the response contains the cookie that the
    # middleware and template token expect.
    response = render(request, 'login.html')
    try:
        token = get_token(request)
        # Set cookie using settings for SameSite/secure/httponly
        response.set_cookie(
            settings.CSRF_COOKIE_NAME,
            token,
            secure=getattr(settings, 'CSRF_COOKIE_SECURE', False),
            httponly=getattr(settings, 'CSRF_COOKIE_HTTPONLY', False),
            samesite=getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')
        )
    except Exception as e:
        logger.exception(f"Error setting CSRF cookie explicitly: {e}")
    return response

# Agregar URL para debug: /debug-rut/?rut=22047993-5

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_view(request):
    return render(request, 'profile.html')

def debug_rut_view(request):
    """Vista de debug para verificar RUTs en la base de datos"""
    from django.http import HttpResponse
    from django.db import connection
    
    debug_info = []
    rut_buscar = request.GET.get('rut', '22047993-5')
    
    try:
        with connection.cursor() as cursor:
            debug_info.append(f"Buscando RUT: {rut_buscar}")
            debug_info.append("")
            
            # Ver estructura de tabla profesor
            debug_info.append("ESTRUCTURA admin_gym_profesor:")
            cursor.execute("DESCRIBE admin_gym_profesor")
            columnas = cursor.fetchall()
            for col in columnas:
                debug_info.append(f"  {col[0]} - {col[1]}")
            debug_info.append("")
            
            # Ver todos los profesores
            debug_info.append("TODOS LOS PROFESORES:")
            cursor.execute("SELECT * FROM admin_gym_profesor LIMIT 10")
            profesores = cursor.fetchall()
            for prof in profesores:
                debug_info.append(f"  {prof}")
            debug_info.append("")
            
            # Ver estructura de tabla cliente
            debug_info.append("ESTRUCTURA admin_gym_cliente:")
            cursor.execute("DESCRIBE admin_gym_cliente")
            columnas = cursor.fetchall()
            for col in columnas:
                debug_info.append(f"  {col[0]} - {col[1]}")
            debug_info.append("")
            
            # Ver algunos clientes
            debug_info.append("ALGUNOS CLIENTES:")
            cursor.execute("SELECT id, nombre, rut, email FROM admin_gym_cliente LIMIT 5")
            clientes = cursor.fetchall()
            for cliente in clientes:
                debug_info.append(f"  {cliente}")
                
    except Exception as e:
        debug_info.append(f"Error: {e}")
    
    return HttpResponse("<br>".join(debug_info))


def root_redirect(request):
    """Redirecciona la raíz a /login/ sin cachear - usando JavaScript para evitar caché de HTTP redirect"""
    from django.http import HttpResponse
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <script>
        // Redirect inmediatamente sin cachear
        window.location.replace('/login/');
    </script>
</head>
<body>
    <p>Redirigiendo a login...</p>
</body>
</html>'''
    response = HttpResponse(html)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response


def catchall_redirect(request):
    """Redirige cualquier ruta no reconocida a /login/"""
    return root_redirect(request)


def public_root(request):
    """Página raíz mínima que no toca la base de datos.
    Muestra un enlace al login y evita que la aplicación falle si
    la conexión a la base de datos está caída (útil como fallback).
    """
    html = (
        "<html><head><meta charset='utf-8'><title>FitSpace</title></head>"
        "<body style='font-family:Arial,sans-serif;background:#f6f7fb;color:#222;margin:40px;'>"
        "<h1>Bienvenido a FitSpace</h1>"
        "<p>Si ya tienes cuenta, <a href='/login/'>inicia sesión aquí</a>.</p>"
        "<p>Si el servicio principal está temporalmente caído, inténtalo nuevamente más tarde.</p>"
        "</body></html>"
    )
    return HttpResponse(html)
