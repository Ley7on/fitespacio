# views_asignar_rutinas.py - Vista para asignar rutinas usando tablas AWS

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def asignar_rutina_alumno(request):
    """Asignar rutina creada por el entrenador a un alumno específico"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from .models import Rutina, DetalleEjercicio, Ejercicio
        from alumno.models import RutinaAlumno, EjercicioRutinaAlumno, PerfilAlumno
        
        data = json.loads(request.body)
        
        # Validar datos requeridos
        nombre = data.get('nombre', '').strip()
        objetivo = data.get('objetivo', '').strip()
        alumno_id = data.get('alumno_id')
        ejercicios = data.get('ejercicios', [])
        
        if not nombre or not objetivo or not alumno_id:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan datos obligatorios: nombre, objetivo y alumno'
            })
        
        if not ejercicios:
            return JsonResponse({
                'success': False, 
                'message': 'Debe incluir al menos un ejercicio'
            })
        
        with transaction.atomic():
            # 1. Crear la rutina del entrenador
            rutina_entrenador = Rutina.objects.create(
                nombre=nombre,
                objetivo=objetivo,
                descripcion=data.get('descripcion', ''),
                entrenador=request.user,
                tipo='personalizada',
                duracion_estimada=data.get('duracion_estimada', 60),
                frecuencia_semanal=data.get('frecuencia_semanal', 3)
            )
            
            # 2. Crear los ejercicios de la rutina
            for i, ejercicio_data in enumerate(ejercicios, 1):
                # Buscar o crear el ejercicio base
                ejercicio_base, created = Ejercicio.objects.get_or_create(
                    nombre=ejercicio_data['nombre'],
                    defaults={
                        'grupo_muscular': ejercicio_data.get('grupo_muscular', 'general'),
                        'descripcion': f"Ejercicio creado por {request.user.username}"
                    }
                )
                
                # Crear el detalle del ejercicio en la rutina
                DetalleEjercicio.objects.create(
                    rutina=rutina_entrenador,
                    ejercicio=ejercicio_base,
                    nombre_ejercicio=ejercicio_data['nombre'],
                    series=ejercicio_data.get('series', 3),
                    repeticiones=ejercicio_data.get('repeticiones', '8-12'),
                    peso_inicial=ejercicio_data.get('peso', ''),
                    descanso=ejercicio_data.get('descanso', '60s'),
                    notas=ejercicio_data.get('notas', ''),
                    orden=i
                )
            
            # 3. Obtener el perfil del alumno
            alumno_user = User.objects.get(id=alumno_id)
            perfil_alumno = PerfilAlumno.objects.get(user=alumno_user)
            
            # 4. Crear la rutina asignada al alumno
            rutina_alumno = RutinaAlumno.objects.create(
                alumno=perfil_alumno,
                nombre=nombre,
                objetivo=objetivo,
                tipo='asignada',
                rutina_entrenador=rutina_entrenador,
                asignada_por=request.user,
                fecha_asignacion=timezone.now(),
                descripcion=data.get('descripcion', '')
            )
            
            # 5. Copiar ejercicios a la rutina del alumno CON REFERENCIA para sincronización
            for detalle in rutina_entrenador.ejercicios.all():
                EjercicioRutinaAlumno.objects.create(
                    rutina=rutina_alumno,
                    nombre=detalle.nombre_ejercicio,
                    series=detalle.series,
                    repeticiones=detalle.repeticiones,
                    peso=str(detalle.peso_inicial) if detalle.peso_inicial else '',
                    descanso=detalle.descanso,
                    notas=detalle.notas,
                    orden=detalle.orden,
                    ejercicio_entrenador=detalle  # ⚡ CLAVE: Mantiene referencia para auto-sync
                )
        
        logger.info(f"Rutina asignada: ID={rutina_entrenador.id}, Alumno={alumno_id}, Entrenador={request.user.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina creada y asignada exitosamente',
            'rutina_id': rutina_entrenador.id,
            'ejercicios_count': len(ejercicios)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Error en formato JSON'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Alumno no encontrado'})
    except PerfilAlumno.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil de alumno no encontrado'})
    except Exception as e:
        logger.error(f"Error asignando rutina: {e}")
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})