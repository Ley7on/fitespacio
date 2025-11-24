from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from entrenador_app.auth_views import require_role
from entrenador_app.admin_gym_models import AdminGymCliente, AdminGymProfesor
from notifications.tasks import send_credentials_email_task
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
def crear_cliente(request):
    """Crear nuevo cliente y enviar credenciales"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            email = request.POST.get('email', '').strip()
            rut = request.POST.get('rut', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            membresia = request.POST.get('membresia', 'mensual')
            
            # Validaciones
            if not all([nombre, email, rut]):
                messages.error(request, 'Nombre, email y RUT son obligatorios')
                return render(request, 'entrenador/crear_cliente.html')
            
            if not validate_rut(rut):
                messages.error(request, 'Formato de RUT inválido')
                return render(request, 'entrenador/crear_cliente.html')
            
            # Verificar si ya existe
            if User.objects.filter(username=rut).exists():
                messages.error(request, 'Ya existe un usuario con este RUT')
                return render(request, 'entrenador/crear_cliente.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con este email')
                return render(request, 'entrenador/crear_cliente.html')
            
            # Generar contraseña
            password = generate_password()
            
            # Crear usuario Django
            user = User.objects.create_user(
                username=rut,
                email=email,
                first_name=nombre.split()[0] if nombre.split() else nombre,
                last_name=' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else '',
                password=password
            )
            
            # Crear cliente en admin_gym
            from datetime import date, timedelta
            fecha_vencimiento = date.today() + timedelta(days=30)  # 1 mes por defecto
            
            AdminGymCliente.objects.create(
                user_id=user.id,
                nombre=nombre,
                email=email,
                rut=rut,
                telefono=telefono,
                membresia=membresia,
                estado_membresia='activa',
                fecha_registro=date.today(),
                fecha_vencimiento=fecha_vencimiento,
                activo=True
            )
            
            # Enviar credenciales por email
            try:
                send_credentials_email_task.delay(user.id, password, 'cliente')
                messages.success(request, f'Cliente {nombre} creado exitosamente. Las credenciales han sido enviadas a {email}')
            except Exception as e:
                logger.warning(f"Error enviando credenciales: {e}")
                messages.success(request, f'Cliente {nombre} creado exitosamente. Credenciales: Usuario: {rut}, Contraseña: {password}')
            
            return redirect('alumnos_list')
            
        except Exception as e:
            logger.error(f"Error creando cliente: {e}")
            messages.error(request, f'Error creando cliente: {str(e)}')
    
    return render(request, 'entrenador/crear_cliente.html')

@require_role('entrenador')
@csrf_protect
def crear_entrenador(request):
    """Crear nuevo entrenador y enviar credenciales"""
    if not request.user.is_superuser:
        messages.error(request, 'Solo los administradores pueden crear entrenadores')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            email = request.POST.get('email', '').strip()
            rut = request.POST.get('rut', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            especialidad = request.POST.get('especialidad', '').strip()
            
            # Validaciones
            if not all([nombre, email, rut]):
                messages.error(request, 'Nombre, email y RUT son obligatorios')
                return render(request, 'entrenador/crear_entrenador.html')
            
            if not validate_rut(rut):
                messages.error(request, 'Formato de RUT inválido')
                return render(request, 'entrenador/crear_entrenador.html')
            
            # Verificar si ya existe
            if User.objects.filter(username=rut).exists():
                messages.error(request, 'Ya existe un usuario con este RUT')
                return render(request, 'entrenador/crear_entrenador.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con este email')
                return render(request, 'entrenador/crear_entrenador.html')
            
            # Generar contraseña
            password = generate_password()
            
            # Crear usuario Django con permisos de staff
            user = User.objects.create_user(
                username=rut,
                email=email,
                first_name=nombre.split()[0] if nombre.split() else nombre,
                last_name=' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else '',
                password=password,
                is_staff=True  # Dar permisos de entrenador
            )
            
            # Crear profesor en admin_gym
            AdminGymProfesor.objects.create(
                user_id=user.id,
                nombre=nombre,
                email=email,
                rut=rut,
                telefono=telefono,
                especialidad=especialidad,
                activo=True
            )
            
            # Enviar credenciales por email
            try:
                send_credentials_email_task.delay(user.id, password, 'entrenador')
                messages.success(request, f'Entrenador {nombre} creado exitosamente. Las credenciales han sido enviadas a {email}')
            except Exception as e:
                logger.warning(f"Error enviando credenciales: {e}")
                messages.success(request, f'Entrenador {nombre} creado exitosamente. Credenciales: Usuario: {rut}, Contraseña: {password}')
            
            return redirect('dashboard')
            
        except Exception as e:
            logger.error(f"Error creando entrenador: {e}")
            messages.error(request, f'Error creando entrenador: {str(e)}')
    
    return render(request, 'entrenador/crear_entrenador.html')

@require_role('entrenador')
def reenviar_credenciales(request, user_id):
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
                send_credentials_email_task.delay(user.id, new_password, user_type)
                return JsonResponse({
                    'success': True, 
                    'message': f'Nuevas credenciales enviadas a {user.email}'
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