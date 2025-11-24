# views_rutinas.py - Vistas para el sistema de rutinas del alumno

from django.shortcuts import render, get_object_or_404
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
    """API para obtener rutinas asignadas por el entrenador"""
    try:
        from .models import RutinaAlumno, PerfilAlumno
        
        # Obtener el perfil del alumno
        try:
            perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': True, 'rutinas': []})
        
        # Obtener rutinas asignadas
        rutinas_asignadas = RutinaAlumno.objects.filter(
            alumno=perfil_alumno,
            tipo='asignada',
            activa=True
        ).select_related('asignada_por', 'rutina_entrenador')
        
        rutinas = []
        for rutina in rutinas_asignadas:
            entrenador_nombre = rutina.asignada_por.get_full_name() or rutina.asignada_por.username if rutina.asignada_por else 'Sistema'
            
            rutinas.append({
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.get_objetivo_display(),
                'descripcion': rutina.descripcion,
                'fecha_asignacion': rutina.fecha_asignacion.strftime('%d/%m/%Y') if rutina.fecha_asignacion else '',
                'entrenador': entrenador_nombre,
                'ejercicios_count': rutina.ejercicios.count(),
                'dia_asignado': rutina.get_dia_asignado_display() if rutina.dia_asignado else None
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
    """API para obtener rutinas personales del alumno"""
    try:
        from .models import RutinaAlumno, PerfilAlumno
        
        # Obtener el perfil del alumno
        try:
            perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': True, 'rutinas': []})
        
        # Obtener rutinas personales
        rutinas_personales = RutinaAlumno.objects.filter(
            alumno=perfil_alumno,
            tipo='personal',
            activa=True
        )
        
        rutinas = []
        for rutina in rutinas_personales:
            rutinas.append({
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.get_objetivo_display(),
                'descripcion': rutina.descripcion,
                'fecha_creacion': rutina.fecha_creacion.strftime('%d/%m/%Y'),
                'ejercicios_count': rutina.ejercicios.count(),
                'dia_asignado': rutina.get_dia_asignado_display() if rutina.dia_asignado else None
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
    """API para que el alumno cree sus propias rutinas"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from .models import RutinaAlumno, EjercicioRutinaAlumno, PerfilAlumno
        
        data = json.loads(request.body)
        
        # Validar datos requeridos
        nombre = data.get('nombre', '').strip()
        objetivo = data.get('objetivo', '').strip()
        ejercicios = data.get('ejercicios', [])
        
        if not nombre or not objetivo:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan datos obligatorios: nombre y objetivo'
            })
        
        if not ejercicios:
            return JsonResponse({
                'success': False, 
                'message': 'Debe incluir al menos un ejercicio'
            })
        
        # Obtener el perfil del alumno
        perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        
        with transaction.atomic():
            # Crear la rutina personal
            rutina_personal = RutinaAlumno.objects.create(
                alumno=perfil_alumno,
                nombre=nombre,
                objetivo=objetivo,
                tipo='personal',
                descripcion=data.get('descripcion', ''),
                dia_asignado=data.get('dia_asignado')
            )
            
            # Crear los ejercicios
            for i, ejercicio_data in enumerate(ejercicios, 1):
                EjercicioRutinaAlumno.objects.create(
                    rutina=rutina_personal,
                    nombre=ejercicio_data['nombre'],
                    series=ejercicio_data.get('series', 3),
                    repeticiones=ejercicio_data.get('repeticiones', '8-12'),
                    peso=ejercicio_data.get('peso', ''),
                    descanso=ejercicio_data.get('descanso', '60s'),
                    notas=ejercicio_data.get('notas', ''),
                    orden=i
                )
        
        logger.info(f"Rutina personal creada: ID={rutina_personal.id}, Alumno={request.user.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina personal creada exitosamente',
            'rutina_id': rutina_personal.id,
            'ejercicios_count': len(ejercicios)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Error en formato JSON'})
    except Exception as e:
        logger.error(f"Error creando rutina personal: {e}")
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})

@csrf_exempt
@login_required
def asignar_rutina_a_dia(request):
    """API para asignar una rutina a un día específico de la semana"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from .models import RutinaAlumno, PerfilAlumno
        
        data = json.loads(request.body)
        rutina_id = data.get('rutina_id')
        dia = data.get('dia')
        
        if not all([rutina_id, dia]):
            return JsonResponse({'success': False, 'message': 'Faltan datos requeridos'})
        
        # Obtener el perfil del alumno
        perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        
        # Obtener la rutina
        rutina = RutinaAlumno.objects.get(id=rutina_id, alumno=perfil_alumno)
        
        # Asignar el día
        rutina.dia_asignado = dia
        rutina.save()
        
        logger.info(f"Rutina asignada a día: rutina={rutina_id}, dia={dia}, usuario={request.user.id}")
        
        return JsonResponse({
            'success': True,
            'message': f'Rutina "{rutina.nombre}" asignada al {rutina.get_dia_asignado_display()}'
        })
        
    except RutinaAlumno.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rutina no encontrada'})
    except Exception as e:
        logger.error(f"Error asignando rutina a día: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_calendario_semanal(request):
    """API para obtener el calendario semanal del alumno"""
    try:
        from .models import RutinaAlumno, PerfilAlumno
        
        # Obtener el perfil del alumno
        try:
            perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            calendario = {
                'lunes': [], 'martes': [], 'miercoles': [], 'jueves': [],
                'viernes': [], 'sabado': [], 'domingo': []
            }
            return JsonResponse({'success': True, 'calendario': calendario})
        
        # Obtener rutinas organizadas por día
        rutinas_por_dia = RutinaAlumno.objects.filter(
            alumno=perfil_alumno,
            activa=True,
            dia_asignado__isnull=False
        ).select_related('asignada_por')
        
        calendario = {
            'lunes': [], 'martes': [], 'miercoles': [], 'jueves': [],
            'viernes': [], 'sabado': [], 'domingo': []
        }
        
        for rutina in rutinas_por_dia:
            rutina_data = {
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.get_objetivo_display(),
                'tipo': rutina.get_tipo_display(),
                'ejercicios_count': rutina.ejercicios.count(),
                'entrenador': rutina.asignada_por.get_full_name() if rutina.asignada_por else None
            }
            
            if rutina.dia_asignado in calendario:
                calendario[rutina.dia_asignado].append(rutina_data)
        
        return JsonResponse({
            'success': True,
            'calendario': calendario
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo calendario semanal: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_detalle_rutina(request, rutina_id):
    """API para obtener el detalle completo de una rutina"""
    try:
        from .models import RutinaAlumno, PerfilAlumno
        
        # Obtener el perfil del alumno
        perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        
        # Obtener la rutina
        rutina = RutinaAlumno.objects.get(id=rutina_id, alumno=perfil_alumno)
        
        # Obtener ejercicios
        ejercicios = []
        for ejercicio in rutina.ejercicios.all():
            ejercicios.append({
                'id': ejercicio.id,
                'nombre': ejercicio.nombre,
                'series': ejercicio.series,
                'repeticiones': ejercicio.repeticiones,
                'peso': ejercicio.peso,
                'descanso': ejercicio.descanso,
                'notas': ejercicio.notas,
                'orden': ejercicio.orden
            })
        
        rutina_data = {
            'id': rutina.id,
            'nombre': rutina.nombre,
            'objetivo': rutina.get_objetivo_display(),
            'tipo': rutina.get_tipo_display(),
            'descripcion': rutina.descripcion,
            'dia_asignado': rutina.get_dia_asignado_display() if rutina.dia_asignado else None,
            'fecha_creacion': rutina.fecha_creacion.strftime('%d/%m/%Y'),
            'entrenador': rutina.asignada_por.get_full_name() if rutina.asignada_por else None,
            'ejercicios': ejercicios
        }
        
        return JsonResponse({
            'success': True,
            'rutina': rutina_data
        })
        
    except RutinaAlumno.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rutina no encontrada'})
    except Exception as e:
        logger.error(f"Error obteniendo detalle de rutina: {e}")
        return JsonResponse({'success': False, 'error': str(e)})