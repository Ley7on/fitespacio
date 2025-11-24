# views_rutinas_aws.py - Vistas usando tablas AWS existentes

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def rutinas_dashboard(request):
    """Vista principal de rutinas del alumno"""
    return render(request, 'alumno/rutinas.html')

@login_required
def obtener_rutinas_asignadas(request):
    """API para obtener rutinas asignadas usando tablas AWS"""
    try:
        from entrenador_app.admin_gym_models import AdminGymRutinaCliente, AdminGymCliente
        
        # Obtener cliente
        cliente = AdminGymCliente.objects.filter(user_id=request.user.id).first()
        if not cliente:
            return JsonResponse({'success': True, 'rutinas': []})
        
        # Obtener rutinas asignadas
        asignaciones = AdminGymRutinaCliente.objects.filter(
            cliente=cliente,
            activa=True
        ).select_related('rutina', 'asignado_por')
        
        rutinas = []
        for asig in asignaciones:
            rutina = asig.rutina
            entrenador = asig.asignado_por.get_full_name() or asig.asignado_por.username if asig.asignado_por else 'Sistema'
            
            from entrenador_app.admin_gym_models import AdminGymEjercicioRutina
            ejercicios_count = AdminGymEjercicioRutina.objects.filter(rutina=rutina).count()
            
            rutinas.append({
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.objetivo,
                'descripcion': rutina.descripcion,
                'fecha_asignacion': 'Reciente',
                'entrenador': entrenador,
                'ejercicios_count': ejercicios_count
            })
        
        return JsonResponse({
            'success': True,
            'rutinas': rutinas,
            'total': len(rutinas)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo rutinas asignadas: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_rutinas_personales(request):
    """API para rutinas personales - usando tablas AWS"""
    try:
        from entrenador_app.admin_gym_models import AdminGymRutina
        
        # Rutinas creadas por el propio usuario
        rutinas_personales = AdminGymRutina.objects.filter(
            creado_por=request.user,
            activa=True
        )
        
        rutinas = []
        for rutina in rutinas_personales:
            from entrenador_app.admin_gym_models import AdminGymEjercicioRutina
            ejercicios_count = AdminGymEjercicioRutina.objects.filter(rutina=rutina).count()
            
            rutinas.append({
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.objetivo,
                'descripcion': rutina.descripcion,
                'fecha_creacion': 'Reciente',
                'ejercicios_count': ejercicios_count
            })
        
        return JsonResponse({
            'success': True,
            'rutinas': rutinas,
            'total': len(rutinas)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo rutinas personales: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@login_required
def crear_rutina_personal(request):
    """API para crear rutinas personales usando tablas AWS"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from entrenador_app.admin_gym_models import AdminGymRutina, AdminGymEjercicio, AdminGymEjercicioRutina
        
        data = json.loads(request.body)
        
        nombre = data.get('nombre', '').strip()
        objetivo = data.get('objetivo', '').strip()
        ejercicios = data.get('ejercicios', [])
        
        if not nombre or not objetivo:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan datos obligatorios'
            })
        
        with transaction.atomic():
            # Crear rutina personal
            rutina = AdminGymRutina.objects.create(
                nombre=nombre,
                descripcion=data.get('descripcion', ''),
                objetivo=objetivo,
                creado_por=request.user,
                activa=True,
                es_plantilla=False,
                fecha_creacion=timezone.now()
            )
            
            # Crear ejercicios
            for i, ej_data in enumerate(ejercicios, 1):
                ejercicio, created = AdminGymEjercicio.objects.get_or_create(
                    nombre=ej_data['nombre'],
                    defaults={
                        'descripcion': '',
                        'tipo': 'fuerza',
                        'grupo_muscular': 'general',
                        'instrucciones': '',
                        'activo': True
                    }
                )
                
                AdminGymEjercicioRutina.objects.create(
                    rutina=rutina,
                    ejercicio=ejercicio,
                    series=ej_data.get('series', 3),
                    repeticiones=ej_data.get('repeticiones', 10),
                    peso_sugerido=ej_data.get('peso', 0),
                    tiempo_descanso=ej_data.get('descanso', 60),
                    notas=ej_data.get('notas', ''),
                    orden=i,
                    video_url='',
                    video_duration_s=0
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina creada exitosamente',
            'rutina_id': rutina.id,
            'ejercicios_count': len(ejercicios)
        })
        
    except Exception as e:
        logger.error(f"Error creando rutina personal: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
@login_required
def asignar_rutina_a_dia(request):
    """API para asignar rutina a día - funcionalidad simplificada"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        data = json.loads(request.body)
        rutina_id = data.get('rutina_id')
        dia = data.get('dia')
        
        if not all([rutina_id, dia]):
            return JsonResponse({'success': False, 'message': 'Faltan datos requeridos'})
        
        # Por ahora solo confirmamos la acción
        return JsonResponse({
            'success': True,
            'message': f'Rutina programada para {dia}'
        })
        
    except Exception as e:
        logger.error(f"Error asignando rutina a día: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_calendario_semanal(request):
    """API para calendario semanal - versión simplificada"""
    try:
        # Calendario vacío por ahora
        calendario = {
            'lunes': [], 'martes': [], 'miercoles': [], 'jueves': [],
            'viernes': [], 'sabado': [], 'domingo': []
        }
        
        return JsonResponse({
            'success': True,
            'calendario': calendario
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo calendario semanal: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_detalle_rutina(request, rutina_id):
    """API para obtener detalle de rutina usando tablas AWS"""
    try:
        from entrenador_app.admin_gym_models import AdminGymRutina, AdminGymEjercicioRutina
        
        # Obtener rutina
        rutina = AdminGymRutina.objects.get(id=rutina_id)
        
        # Obtener ejercicios
        ejercicios_rutina = AdminGymEjercicioRutina.objects.filter(
            rutina=rutina
        ).select_related('ejercicio').order_by('orden')
        
        ejercicios = []
        for ej_rutina in ejercicios_rutina:
            ejercicios.append({
                'id': ej_rutina.id,
                'nombre': ej_rutina.ejercicio.nombre,
                'series': ej_rutina.series,
                'repeticiones': ej_rutina.repeticiones,
                'peso': ej_rutina.peso_sugerido,
                'descanso': f"{ej_rutina.tiempo_descanso}s",
                'notas': ej_rutina.notas,
                'orden': ej_rutina.orden
            })
        
        rutina_data = {
            'id': rutina.id,
            'nombre': rutina.nombre,
            'objetivo': rutina.objetivo,
            'descripcion': rutina.descripcion,
            'fecha_creacion': 'Reciente',
            'ejercicios': ejercicios
        }
        
        return JsonResponse({
            'success': True,
            'rutina': rutina_data
        })
        
    except AdminGymRutina.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rutina no encontrada'})
    except Exception as e:
        logger.error(f"Error obteniendo detalle de rutina: {e}")
        return JsonResponse({'success': False, 'error': str(e)})