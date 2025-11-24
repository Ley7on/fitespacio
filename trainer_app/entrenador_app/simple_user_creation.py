from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from entrenador_app.auth_views import require_role
from notifications.email_service import EmailService
import logging
import re

logger = logging.getLogger(__name__)

def validate_rut(rut):
    """Validar formato de RUT chileno"""
    if not rut:
        return False
    
    # Remover puntos y guiones
    rut = re.sub(r'[.-]', '', rut.upper())
    
    # Verificar formato básico
    if not re.match(r'^\d{7,8}[0-9K]$', rut):
        return False
    
    return True

def generate_password():
    """Generar contraseña segura"""
    return get_random_string(12, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%')

@require_role('entrenador')
@csrf_protect
def crear_usuario_simple(request):
    """Crear nuevo usuario (cliente o entrenador) de forma simple"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            email = request.POST.get('email', '').strip()
            username = request.POST.get('username', '').strip()
            user_type = request.POST.get('user_type', 'cliente')
            
            # Validaciones
            if not all([nombre, email, username]):
                messages.error(request, 'Nombre, email y usuario son obligatorios')
                return render(request, 'entrenador/crear_usuario_simple.html')
            
            # Verificar si ya existe
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Ya existe un usuario con este nombre de usuario')
                return render(request, 'entrenador/crear_usuario_simple.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con este email')
                return render(request, 'entrenador/crear_usuario_simple.html')
            
            # Generar contraseña
            password = generate_password()
            
            # Determinar permisos según tipo de usuario
            is_staff = user_type == 'entrenador'
            
            # Crear usuario Django
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=nombre.split()[0] if nombre.split() else nombre,
                last_name=' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else '',
                password=password,
                is_staff=is_staff
            )
            
            # Enviar credenciales por email
            try:
                result = EmailService.send_credentials_email(user, password, user_type)
                if result:
                    messages.success(request, f'{user_type.title()} {nombre} creado exitosamente. Las credenciales han sido enviadas a {email}')
                else:
                    messages.warning(request, f'{user_type.title()} {nombre} creado exitosamente, pero hubo un problema enviando el email. Credenciales: Usuario: {username}, Contraseña: {password}')
            except Exception as e:
                logger.warning(f"Error enviando credenciales: {e}")
                messages.success(request, f'{user_type.title()} {nombre} creado exitosamente. Credenciales: Usuario: {username}, Contraseña: {password}')
            
            return redirect('alumnos_list' if user_type == 'cliente' else 'dashboard')
            
        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            messages.error(request, f'Error creando usuario: {str(e)}')
    
    return render(request, 'entrenador/crear_usuario_simple.html')

@require_role('entrenador')
def reenviar_credenciales_simple(request, user_id):
    """Reenviar credenciales a un usuario"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            
            # Generar nueva contraseña
            new_password = generate_password()
            user.set_password(new_password)
            user.save()
            
            # Determinar tipo de usuario
            user_type = 'entrenador' if user.is_staff else 'cliente'
            
            # Enviar credenciales
            try:
                result = EmailService.send_credentials_email(user, new_password, user_type)
                if result:
                    return JsonResponse({
                        'success': True, 
                        'message': f'Nuevas credenciales enviadas a {user.email}'
                    })
                else:
                    return JsonResponse({
                        'success': True, 
                        'message': f'Nueva contraseña generada: {new_password}',
                        'password': new_password
                    })
            except Exception as e:
                logger.warning(f"Error enviando credenciales: {e}")
                return JsonResponse({
                    'success': True, 
                    'message': f'Nueva contraseña generada: {new_password}',
                    'password': new_password
                })
                
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Usuario no encontrado'
            })
        except Exception as e:
            logger.error(f"Error reenviando credenciales: {e}")
            return JsonResponse({
                'success': False, 
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
def listar_usuarios(request):
    """Listar todos los usuarios del sistema"""
    try:
        usuarios = User.objects.all().order_by('username')
        
        usuarios_data = []
        for user in usuarios:
            user_type = 'superuser' if user.is_superuser else ('entrenador' if user.is_staff else 'cliente')
            usuarios_data.append({
                'user': user,
                'user_type': user_type,
                'status': 'Activo' if user.is_active else 'Inactivo'
            })
        
        context = {
            'usuarios': usuarios_data,
            'total_usuarios': len(usuarios_data)
        }
        
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        context = {
            'usuarios': [],
            'total_usuarios': 0,
            'error_message': f'Error: {str(e)}'
        }
    
    return render(request, 'entrenador/listar_usuarios.html', context)