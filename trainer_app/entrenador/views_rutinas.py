from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import datetime, date
from django.conf import settings
from django.db.models import Sum, Max

# filesystem and subprocess for ffmpeg
import os
import uuid
import subprocess
import logging
import json
import re
import csv
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from entrenador_app.admin_gym_models import (
    AdminGymRutina,
    AdminGymEjercicio,
    AdminGymEjercicioRutina,
    AdminGymCliente,
    AdminGymRutinaCliente,
    EntrenamientoLog,
)
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Ejercicio
from entrenador.models import Rutina, DetalleEjercicio
from alumno.models import RutinaAlumno, EjercicioRutinaAlumno

logger = logging.getLogger(__name__)

# Helpers for objective mapping and metadata packing
OBJ_MAP = {
    'fuerza': 'fuerza',
    'resistencia': 'resistencia',
    'hipertrofia': 'ganancia_muscular',
    'ganancia_muscular': 'ganancia_muscular',
    'perdida_grasa': 'perdida_peso',
    'perdida_peso': 'perdida_peso',
    'funcional': 'general',
    'rehabilitacion': 'general',
    'general': 'general',
}


def _pack_rutina_descripcion(data: dict) -> str:
    """Store extra trainer-only metadata into descripcion as JSON string."""
    meta = {
        'descripcion_text': data.get('descripcion', ''),
        'tipo': data.get('tipo', 'personalizada'),
        'dificultad': data.get('dificultad', 'intermedio'),
        'status': data.get('status', 'activa'),
        'duracion_estimada': int(data.get('duracion_estimada', 60) or 60),
        'frecuencia_semanal': int(data.get('frecuencia_semanal', 3) or 3),
        'semanas_duracion': int(data.get('semanas_duracion', 4) or 4),
        'tags': data.get('tags', ''),
        'notas_entrenador': data.get('notas_entrenador', ''),
    }
    return json.dumps(meta, ensure_ascii=False)


def _unpack_rutina_descripcion(desc: str) -> dict:
    try:
        meta = json.loads(desc or '{}')
        if isinstance(meta, dict):
            return meta
        return {}
    except Exception:
        return {}


def _parse_int(value, default=None):
    try:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        # extract first integer found
        m = re.search(r"\d+", str(value))
        return int(m.group(0)) if m else default
    except Exception:
        return default


def _get_or_create_ejercicio(nombre: str) -> AdminGymEjercicio:
    nombre = (nombre or '').strip()
    if not nombre:
        raise ValueError('Nombre de ejercicio requerido')
    ej = AdminGymEjercicio.objects.filter(nombre=nombre).first()
    if ej:
        return ej
    # Create with safe defaults
    return AdminGymEjercicio.objects.create(
        nombre=nombre,
        descripcion=f'Ejercicio creado automáticamente',
        tipo='fuerza',
        grupo_muscular='general',
        instrucciones='',
        activo=True,
    )


def _cliente_from_user_id(user_id):
    if not user_id:
        return None
    return AdminGymCliente.objects.filter(user_id=user_id).first()


@login_required
@transaction.atomic
def crear_rutina(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        logger.info(f"[RUTINA] crear_rutina request.user=%s", request.user)
        
        if not getattr(request.user, 'is_staff', False):
            logger.warning('[RUTINA] permisos insuficientes para usuario %s', request.user)
            return JsonResponse({'success': False, 'error': 'Permisos insuficientes'}, status=403)

        data = json.loads(request.body or '{}')
        nombre = (data.get('nombre') or '').strip()
        if not nombre:
            return JsonResponse({'success': False, 'error': 'Nombre de rutina requerido'}, status=400)

        # Verificar si ya existe
        if Rutina.objects.filter(nombre=nombre, entrenador=request.user).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe una rutina con ese nombre'}, status=400)

        objetivo_src = (data.get('objetivo') or 'hipertrofia').strip()
        tipo = (data.get('tipo') or 'personalizada').strip()
        status = (data.get('status') or 'activa').strip()
        semanas = int(data.get('semanas_duracion', 4) or 4)
        duracion = int(data.get('duracion_estimada', 60) or 60)
        frecuencia = int(data.get('frecuencia_semanal', 3) or 3)
        dificultad = (data.get('dificultad') or 'intermedio').strip()
        descripcion = data.get('descripcion', '')
        notas_entrenador = data.get('notas_entrenador', '')
        tags = data.get('tags', '')
        ejercicios = data.get('ejercicios', [])

        # Crear rutina con el modelo NEW (Rutina en entrenador.models)
        rutina = Rutina.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            objetivo=objetivo_src,
            tipo=tipo,
            status=status,
            dificultad=dificultad,
            semanas_duracion=semanas,
            duracion_estimada=duracion,
            frecuencia_semanal=frecuencia,
            notas_entrenador=notas_entrenador,
            tags=tags,
            entrenador=request.user,
            fecha_creacion=timezone.now(),
        )

        logger.info(f'[RUTINA] creada id={rutina.id} nombre={rutina.nombre} por={request.user}')

        # Crear ejercicios de la rutina
        for i, ejercicio_data in enumerate(ejercicios):
            ejercicio_nombre = ejercicio_data.get('nombre', '').strip()
            if ejercicio_nombre:
                # Obtener o crear el ejercicio
                try:
                    from entrenador.models import Ejercicio as EjercicioEntrenador
                    ejercicio, _ = EjercicioEntrenador.objects.get_or_create(
                        nombre=ejercicio_nombre,
                        defaults={'grupo_muscular': 'general', 'categoria': 'fuerza'}
                    )
                except Exception as e:
                    # Fallback si hay problemas
                    logger.warning(f"No se pudo obtener/crear ejercicio: {ejercicio_nombre}, error: {e}")
                    continue

                DetalleEjercicio.objects.create(
                    rutina=rutina,
                    ejercicio=ejercicio,
                    nombre_ejercicio=ejercicio_nombre,
                    series=int(ejercicio_data.get('series', 3) or 3),
                    repeticiones=str(ejercicio_data.get('repeticiones', 10) or 10),  # CharField
                    peso_inicial=ejercicio_data.get('peso', ''),
                    descanso=ejercicio_data.get('descanso', '60s'),
                    notas=ejercicio_data.get('notas', ''),
                    orden=i + 1,
                )

        logger.info(f"[RUTINA] rutina creada exitosamente con {len(ejercicios)} ejercicios")

        return JsonResponse({
            'success': True,
            'message': f'Rutina "{nombre}" creada exitosamente',
            'rutina_id': rutina.id
        })

    except Exception as e:
        logger.error(f"Error creando rutina: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)


@login_required
def obtener_rutinas(request):
    try:
        rutinas_qs = (
            AdminGymRutina.objects
            .filter(creado_por=request.user)
            .order_by('-id')
        )

        data = []
        for r in rutinas_qs:
            try:
                meta = _unpack_rutina_descripcion(r.descripcion)
            except Exception:
                meta = {}

            ejercicios_qs = AdminGymEjercicioRutina.objects.filter(rutina=r).select_related('ejercicio').order_by('orden')

            asignacion = AdminGymRutinaCliente.objects.filter(rutina=r).order_by('-fecha_asignacion').first()
            alumno_info = None
            if asignacion and getattr(asignacion, 'cliente', None):
                cliente = asignacion.cliente
                alumno_info = {
                    'id': getattr(cliente, 'user_id', None),
                    'nombre': getattr(cliente, 'nombre', None) or str(cliente)
                }

            data.append({
                'id': r.id,
                'nombre': r.nombre,
                'objetivo': r.objetivo,
                'dificultad': meta.get('dificultad', 'intermedio'),
                'tipo': 'plantilla' if getattr(r, 'es_plantilla', False) else meta.get('tipo', 'personalizada'),
                'status': meta.get('status', 'activa'),
                'duracion_estimada': int(meta.get('duracion_estimada', 60)),
                'frecuencia_semanal': int(meta.get('frecuencia_semanal', 3)),
                'semanas_duracion': int(meta.get('semanas_duracion', 4)),
                'tags': meta.get('tags', ''),
                'descripcion': meta.get('descripcion_text', '') or '',
                'notas_entrenador': meta.get('notas_entrenador', ''),
                'fecha_creacion': None,
                'ejercicios': [
                    {
                        'id': er.id,
                        'nombre': getattr(er.ejercicio, 'nombre', 'Ejercicio'),
                        'series': int(er.series) if er.series is not None else 3,
                        'repeticiones': int(er.repeticiones) if er.repeticiones is not None else 10,
                        'peso_inicial': er.peso_sugerido or '',
                        'descanso': er.tiempo_descanso or 60,
                        'orden': er.orden,
                    } for er in ejercicios_qs
                ],
                'alumno': alumno_info,
                'es_plantilla': bool(getattr(r, 'es_plantilla', False)),
                'activa': bool(getattr(r, 'activa', True)),
                'total_ejercicios': ejercicios_qs.count(),
            })

        logger.info('[OBTENER_RUTINAS] usuario=%s rutinas=%d', request.user, len(data))
        return JsonResponse({'success': True, 'rutinas': data})
        
    except Exception as e:
        logger.exception('[OBTENER_RUTINAS] error: %s', e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)





@login_required
@csrf_exempt
@transaction.atomic
def editar_rutina(request, rutina_id):
    """Soporta GET (serializar rutina) y PUT (actualizar rutina y ejercicios).
    URL: /api/rutinas/<id>/editar/
    Ahora incluye video_url y video_duration_s en GET y persiste esos campos en PUT.
    """
    try:
        rutina = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
    except AdminGymRutina.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rutina no encontrada'}, status=404)

    # GET -> serializar
    if request.method == 'GET':
        try:
            meta = _unpack_rutina_descripcion(rutina.descripcion)
            ejercicios_qs = AdminGymEjercicioRutina.objects.filter(rutina=rutina).order_by('orden')

            ejercicios = []
            for er in ejercicios_qs:
                ejercicios.append({
                    'id': er.id,
                    'nombre': getattr(er.ejercicio, 'nombre', '') if getattr(er, 'ejercicio', None) else '',
                    'series': int(er.series) if er.series is not None else 0,
                    'repeticiones': int(er.repeticiones) if er.repeticiones is not None else None,
                    'peso_sugerido': str(er.peso_sugerido) if getattr(er, 'peso_sugerido', None) is not None else '',
                    'descanso': int(er.tiempo_descanso) if er.tiempo_descanso is not None else None,
                    'orden': int(er.orden) if getattr(er, 'orden', None) is not None else 0,
                    'notas': er.notas or '',
                    'video_url': er.video_url or '',
                    'video_duration_s': int(er.video_duration_s or 0),
                })

            payload = {
                'id': rutina.id,
                'nombre': rutina.nombre,
                'descripcion': meta.get('descripcion_text', ''),
                'objetivo': rutina.objetivo,
                'tipo': 'plantilla' if getattr(rutina, 'es_plantilla', False) else 'personalizada',
                'frecuencia_semanal': int(meta.get('frecuencia_semanal', 3)),
                'semanas_duracion': int(meta.get('semanas_duracion', 4)),
                'duracion_estimada': int(meta.get('duracion_estimada', 60)),
                'ejercicios': ejercicios,
            }
            return JsonResponse({'success': True, 'rutina': payload}, status=200)
        except Exception as e:
            logger.exception('[RUTINA] error serializando rutina %s: %s', rutina_id, e)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # PUT -> actualizar
    if request.method == 'PUT':
        try:
            payload = json.loads(request.body or '{}')

            # Permisos: solo entrenadores pueden editar
            if not getattr(request.user, 'is_staff', False):
                return JsonResponse({'success': False, 'error': 'Permisos insuficientes'}, status=403)

            # Actualizar metadatos de rutina
            nombre = (payload.get('nombre') or rutina.nombre).strip()
            descripcion_text = payload.get('descripcion', None)
            objetivo_src = (payload.get('objetivo') or rutina.objetivo)
            objetivo = OBJ_MAP.get(objetivo_src, objetivo_src)
            tipo = payload.get('tipo', 'personalizada')

            # Reempaquetar descripcion con meta si se proveyó o mantener existentes
            meta = _unpack_rutina_descripcion(rutina.descripcion)
            if descripcion_text is not None:
                meta['descripcion_text'] = descripcion_text
            # actualizar otros campos si vienen en payload
            for f in ('duracion_estimada', 'frecuencia_semanal', 'semanas_duracion', 'dificultad', 'tags', 'notas_entrenador'):
                if f in payload:
                    meta[f] = payload.get(f)

            rutina.nombre = nombre
            rutina.descripcion = _pack_rutina_descripcion({
                'descripcion': meta.get('descripcion_text', ''),
                'tipo': tipo,
                'dificultad': meta.get('dificultad', 'intermedio'),
                'status': meta.get('status', 'activa'),
                'duracion_estimada': int(meta.get('duracion_estimada', 60) or 60),
                'frecuencia_semanal': int(meta.get('frecuencia_semanal', 3) or 3),
                'semanas_duracion': int(meta.get('semanas_duracion', 4) or 4),
                'tags': meta.get('tags', ''),
                'notas_entrenador': meta.get('notas_entrenador', ''),
            })
            rutina.objetivo = objetivo
            rutina.es_plantilla = (tipo == 'plantilla')
            rutina.save()

            # Manejar ejercicios: reemplazar todo para simplificar coherencia
            ejercicios_in = payload.get('ejercicios', []) or []

            # Eliminar existentes
            AdminGymEjercicioRutina.objects.filter(rutina=rutina).delete()

            from decimal import Decimal
            created = []
            for idx, ej in enumerate(ejercicios_in):
                nombre_ej = (ej.get('nombre') or '').strip()
                if not nombre_ej:
                    # saltar entradas vacías
                    continue
                # conseguir o crear ejercicio canonico
                ejercicio_obj = _get_or_create_ejercicio(nombre_ej)

                series = _parse_int(ej.get('series'), 0) or 0
                repeticiones = _parse_int(ej.get('repeticiones'), None)
                peso = ej.get('peso_sugerido', '')
                try:
                    peso_val = Decimal(str(peso)) if peso not in (None, '', False) else None
                except Exception:
                    peso_val = None
                descanso = _parse_int(ej.get('descanso') or ej.get('tiempo_descanso'), None)
                notas = ej.get('notas', '') or ''
                video_url = ej.get('video_url', '') or ''
                video_duration_s = _parse_int(ej.get('video_duration_s'), 0) or 0

                er = AdminGymEjercicioRutina.objects.create(
                    series=series,
                    repeticiones=repeticiones,
                    peso_sugerido=peso_val,
                    tiempo_descanso=descanso,
                    orden=idx,
                    notas=notas,
                    ejercicio=ejercicio_obj,
                    rutina=rutina,
                    video_url=video_url,
                    video_duration_s=video_duration_s,
                )
                created.append(er.id)

            logger.info('[RUTINA] rutina %s actualizada por %s; ejercicios_creados=%d', rutina.id, request.user, len(created))
            return JsonResponse({'success': True, 'rutina_id': rutina.id, 'total_ejercicios': len(created)})

        except AdminGymRutina.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Rutina no encontrada'}, status=404)
        except Exception as e:
            logger.exception('[RUTINA] error actualizando rutina %s: %s', rutina_id, e)
            transaction.set_rollback(True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # Método no permitido
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


@login_required
def obtener_rutina_detalle(request, rutina_id):
    """Obtener detalles completos de una rutina (intenta modelo nuevo, luego antiguo)"""
    try:
        from entrenador.models import Rutina, DetalleEjercicio
        
        # Intentar con modelo nuevo primero
        try:
            rutina = Rutina.objects.get(id=rutina_id)
            
            # Verificar permiso
            if rutina.entrenador_id != request.user.id:
                return JsonResponse(
                    {'success': False, 'message': 'No tienes acceso a esta rutina'},
                    status=403
                )
            
            # Obtener ejercicios
            ejercicios = []
            for det_ej in rutina.ejercicios.all().order_by('orden'):
                ejercicio_nombre = det_ej.ejercicio.nombre if det_ej.ejercicio else det_ej.nombre_ejercicio or 'Ejercicio'
                # Formatear repeticiones como "3x12"
                repeticiones_formateadas = f"{det_ej.series}x{det_ej.repeticiones}"
                
                ejercicios.append({
                    'id': det_ej.id,
                    'nombre': ejercicio_nombre,
                    'ejercicio_nombre': ejercicio_nombre,
                    'series': det_ej.series,
                    'repeticiones': repeticiones_formateadas,
                    'peso': str(det_ej.peso_inicial) if det_ej.peso_inicial else '',
                    'descanso': det_ej.descanso or '60s',
                    'notas': det_ej.notas or ''
                })
            
            rutina_data = {
                'id': rutina.id,
                'nombre': rutina.nombre,
                'descripcion': rutina.descripcion or '',
                'objetivo': rutina.objetivo,
                'tipo': rutina.tipo,
                'duracion': rutina.semanas_duracion or 4,
                'duracion_semanas': rutina.semanas_duracion or 4,
                'status': rutina.status,
                'fecha_creacion': rutina.fecha_creacion.strftime('%Y-%m-%d') if rutina.fecha_creacion else '',
                'ejercicios': ejercicios
            }
            
            return JsonResponse({
                'success': True,
                **rutina_data
            })
        except Rutina.DoesNotExist:
            pass
        
        # Si no existe en modelo nuevo, intenta con antiguo
        rutina_antigua = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
        
        # Obtener ejercicios del modelo antiguo
        ejercicios = []
        for ej_rutina in AdminGymEjercicioRutina.objects.filter(rutina=rutina_antigua).order_by('orden'):
            ejercicio_nombre = ej_rutina.ejercicio.nombre if ej_rutina.ejercicio else 'Ejercicio'
            series = ej_rutina.series or 3
            repeticiones = ej_rutina.repeticiones or 10
            repeticiones_formateadas = f"{series}x{repeticiones}"
            
            ejercicios.append({
                'id': ej_rutina.id,
                'nombre': ejercicio_nombre,
                'ejercicio_nombre': ejercicio_nombre,
                'series': series,
                'repeticiones': repeticiones_formateadas,
                'peso': str(ej_rutina.peso_sugerido) if ej_rutina.peso_sugerido else '',
                'descanso': str(ej_rutina.tiempo_descanso) if ej_rutina.tiempo_descanso else '60s',
                'notas': ej_rutina.notas or ''
            })
        
        # Parsear metadata del modelo antiguo
        meta = {}
        try:
            meta = _unpack_rutina_descripcion(rutina_antigua.descripcion) if rutina_antigua.descripcion else {}
        except:
            meta = {}
        
        rutina_data = {
            'id': rutina_antigua.id,
            'nombre': rutina_antigua.nombre,
            'descripcion': meta.get('descripcion_text', ''),
            'objetivo': rutina_antigua.objetivo,
            'tipo': 'plantilla' if getattr(rutina_antigua, 'es_plantilla', False) else meta.get('tipo', 'personalizada'),
            'duracion': meta.get('semanas_duracion', 4),
            'status': meta.get('status', 'activa'),
            'ejercicios': ejercicios
        }
        
        return JsonResponse({
            'success': True,
            **rutina_data
        })
        
    except AdminGymRutina.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Rutina no encontrada'},
            status=404
        )
    except Exception as e:
        logger.error(f"Error obteniendo detalle de rutina: {e}", exc_info=True)
        return JsonResponse(
            {'success': False, 'message': f'Error: {str(e)}'},
            status=500
        )


@login_required
def actualizar_rutina(request, rutina_id):
    """Actualizar datos de una rutina existente. PUT esperado."""
    if request.method != 'PUT':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        from entrenador.models import Rutina
        import json
        
        # Parsear JSON del request
        data = json.loads(request.body)
        
        # Intentar con modelo nuevo primero
        try:
            rutina = Rutina.objects.get(id=rutina_id)
            
            # Verificar que el entrenador tiene permiso
            if rutina.entrenador_id != request.user.id:
                return JsonResponse(
                    {'success': False, 'message': 'No tienes permiso para editar esta rutina'},
                    status=403
                )
            
            # Actualizar campos permitidos
            if 'nombre' in data:
                rutina.nombre = data['nombre'].strip()
            
            if 'descripcion' in data:
                rutina.descripcion = data['descripcion'].strip()
            
            if 'objetivo' in data:
                rutina.objetivo = data['objetivo']
            
            if 'tipo' in data:
                rutina.tipo = data['tipo']
            
            if 'duracion' in data or 'duracion_semanas' in data:
                duracion = data.get('duracion') or data.get('duracion_semanas')
                rutina.semanas_duracion = int(duracion) if duracion else 4
            
            # Validar nombre
            if not rutina.nombre:
                return JsonResponse(
                    {'success': False, 'message': 'El nombre de la rutina es obligatorio'},
                    status=400
                )
            
            # Guardar cambios básicos primero
            rutina.save()
            
            # Agregar nuevos ejercicios si se proporcionan
            if 'nuevos_ejercicios' in data and data['nuevos_ejercicios']:
                from .models import Ejercicio
                for ejercicio_data in data['nuevos_ejercicios']:
                    nombre = ejercicio_data.get('nombre', '').strip()
                    repeticiones = ejercicio_data.get('repeticiones', '3x12').strip()
                    
                    if nombre:
                        # Buscar o crear el ejercicio
                        ejercicio, _ = Ejercicio.objects.get_or_create(
                            nombre=nombre,
                            defaults={'grupo_muscular': 'general', 'categoria': 'fuerza'}
                        )
                        
                        # Parsear repeticiones en formato "3x12" -> series=3, repeticiones=12
                        series = 3
                        reps = '12'
                        if 'x' in repeticiones.lower():
                            parts = repeticiones.lower().split('x')
                            try:
                                series = int(parts[0].strip())
                                reps = parts[1].strip()
                            except:
                                pass
                        
                        # Crear detalle de ejercicio
                        DetalleEjercicio.objects.create(
                            rutina=rutina,
                            ejercicio=ejercicio,
                            nombre_ejercicio=nombre,
                            series=series,
                            repeticiones=reps,
                            orden=rutina.ejercicios.count() + 1
                        )
            
            logger.info(f"Rutina {rutina_id} actualizada por {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Rutina actualizada correctamente',
                'rutina': {
                    'id': rutina.id,
                    'nombre': rutina.nombre,
                    'descripcion': rutina.descripcion,
                    'objetivo': rutina.objetivo,
                    'tipo': rutina.tipo,
                    'duracion': rutina.semanas_duracion,
                    'duracion_semanas': rutina.semanas_duracion
                }
            })
        except Rutina.DoesNotExist:
            pass
        
        # Si no existe en modelo nuevo, intenta con antiguo
        rutina_antigua = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
        
        # Actualizar nombre
        if 'nombre' in data:
            rutina_antigua.nombre = data['nombre'].strip()
        
        # Actualizar metadata en descripción
        meta = {}
        try:
            meta = _unpack_rutina_descripcion(rutina_antigua.descripcion) if rutina_antigua.descripcion else {}
        except:
            meta = {}
        
        if 'descripcion' in data:
            meta['descripcion_text'] = data['descripcion'].strip()
        
        if 'objetivo' in data:
            rutina_antigua.objetivo = data['objetivo']
        
        if 'tipo' in data:
            meta['tipo'] = data['tipo']
        
        if 'duracion' in data:
            meta['semanas_duracion'] = int(data['duracion']) if data['duracion'] else 4
        
        # Validar nombre
        if not rutina_antigua.nombre:
            return JsonResponse(
                {'success': False, 'message': 'El nombre de la rutina es obligatorio'},
                status=400
            )
        
        # Guardar metadata actualizada
        rutina_antigua.descripcion = json.dumps(meta) if meta else ''
        rutina_antigua.save()
        
        # Agregar nuevos ejercicios si se proporcionan
        if 'nuevos_ejercicios' in data and data['nuevos_ejercicios']:
            for ejercicio_data in data['nuevos_ejercicios']:
                nombre = ejercicio_data.get('nombre', '').strip()
                repeticiones_str = ejercicio_data.get('repeticiones', '3x12').strip()
                
                if nombre:
                    # Buscar o crear el ejercicio
                    ejercicio = _get_or_create_ejercicio(nombre)
                    
                    # Parsear repeticiones en formato "3x12" -> series=3, repeticiones=12
                    series = 3
                    reps = 12
                    if 'x' in repeticiones_str.lower():
                        parts = repeticiones_str.lower().split('x')
                        try:
                            series = int(parts[0].strip())
                            reps = int(parts[1].strip())
                        except:
                            pass
                    
                    # Obtener el último orden
                    ultimo_orden = AdminGymEjercicioRutina.objects.filter(
                        rutina=rutina_antigua
                    ).aggregate(max_orden=Max('orden'))['max_orden'] or 0
                    
                    # Crear ejercicio rutina
                    AdminGymEjercicioRutina.objects.create(
                        rutina=rutina_antigua,
                        ejercicio=ejercicio,
                        series=series,
                        repeticiones=reps,
                        orden=ultimo_orden + 1
                    )
        
        logger.info(f"Rutina antigua {rutina_id} actualizada por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina actualizada correctamente',
            'rutina': {
                'id': rutina_antigua.id,
                'nombre': rutina_antigua.nombre,
                'descripcion': meta.get('descripcion_text', ''),
                'objetivo': rutina_antigua.objetivo,
                'tipo': meta.get('tipo', 'personalizada'),
                'duracion': meta.get('semanas_duracion', 4)
            }
        })
        
    except AdminGymRutina.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Rutina no encontrada'},
            status=404
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'JSON inválido'},
            status=400
        )
    except Exception as e:
        logger.error(f"Error actualizando rutina: {e}", exc_info=True)
        return JsonResponse(
            {'success': False, 'message': f'Error: {str(e)}'},
            status=500
        )


@login_required
@transaction.atomic
def duplicar_rutina(request, rutina_id):
    """Duplicar una rutina y sus ejercicios asociados. POST esperado."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    try:
        rutina = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
        nueva = AdminGymRutina.objects.create(
            nombre=f"{rutina.nombre} (copia)",
            descripcion=rutina.descripcion,
            objetivo=rutina.objetivo,
            es_plantilla=getattr(rutina, 'es_plantilla', False),
            fecha_creacion=timezone.now(),
            activa=True,
            creado_por=request.user,
        )

        ejercicios = AdminGymEjercicioRutina.objects.filter(rutina=rutina)
        for er in ejercicios:
            AdminGymEjercicioRutina.objects.create(
                rutina=nueva,
                ejercicio=er.ejercicio,
                series=er.series,
                repeticiones=er.repeticiones,
                peso_sugerido=er.peso_sugerido,
                tiempo_descanso=er.tiempo_descanso,
                notas=er.notas,
                orden=er.orden,
            )

        logger.info('[RUTINA] duplicada %s -> %s', rutina.id, nueva.id)
        return JsonResponse({'success': True, 'nueva_id': nueva.id})
    except AdminGymRutina.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rutina no encontrada'}, status=404)
    except Exception as e:
        logger.exception('[RUTINA] duplicar_rutina error: %s', e)
        transaction.set_rollback(True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def eliminar_rutina(request, rutina_id):
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        from entrenador.models import Rutina, DetalleEjercicio
        from alumno.models import RutinaAlumno
        from django.db import connection
        
        # Intentar con modelo nuevo primero
        try:
            rutina = Rutina.objects.get(id=rutina_id)
            
            # Verificar permiso
            if rutina.entrenador_id != request.user.id:
                return JsonResponse(
                    {'success': False, 'error': 'No tienes permiso para eliminar esta rutina'},
                    status=403
                )
            
            # Usar SQL directo para evitar problemas con tablas que no existen
            with connection.cursor() as cursor:
                # Eliminar relaciones con alumnos
                cursor.execute("DELETE FROM alumno_rutinaalumno WHERE rutina_entrenador_id = %s", [rutina_id])
                
                # Eliminar ejercicios de la rutina
                cursor.execute("DELETE FROM entrenador_detalleejercicio WHERE rutina_id = %s", [rutina_id])
                
                # Eliminar la rutina
                cursor.execute("DELETE FROM entrenador_rutina WHERE id = %s", [rutina_id])
            
            logger.info(f"Rutina {rutina_id} eliminada por {request.user.username}")
            
            return JsonResponse({'success': True, 'mensaje': 'Rutina eliminada exitosamente'})
            
        except Rutina.DoesNotExist:
            pass
        
        # Si no existe en modelo nuevo, intenta con antiguo
        rutina = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
        AdminGymEjercicioRutina.objects.filter(rutina=rutina).delete()
        AdminGymRutinaCliente.objects.filter(rutina=rutina).delete()
        rutina.delete()
        
        logger.info(f"Rutina antigua {rutina_id} eliminada por {request.user.username}")
        
        return JsonResponse({'success': True, 'mensaje': 'Rutina eliminada exitosamente'})
        
    except AdminGymRutina.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Rutina no encontrada'},
            status=404
        )
    except Exception as e:
        logger.error(f"Error eliminando rutina: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@transaction.atomic
def eliminar_ejercicio_rutina(request, rutina_id, ejercicio_id):
    """Eliminar un ejercicio específico de una rutina"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        from entrenador.models import Rutina, DetalleEjercicio
        
        # Intentar con modelo nuevo primero
        try:
            rutina = Rutina.objects.get(id=rutina_id)
            
            # Verificar permiso
            if rutina.entrenador_id != request.user.id:
                return JsonResponse(
                    {'success': False, 'message': 'No tienes permiso para editar esta rutina'},
                    status=403
                )
            
            # Eliminar el ejercicio
            ejercicio = DetalleEjercicio.objects.get(id=ejercicio_id, rutina=rutina)
            ejercicio.delete()
            
            logger.info(f"Ejercicio {ejercicio_id} eliminado de rutina {rutina_id} por {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Ejercicio eliminado correctamente'
            })
        except Rutina.DoesNotExist:
            pass
        except DetalleEjercicio.DoesNotExist:
            return JsonResponse(
                {'success': False, 'message': 'Ejercicio no encontrado'},
                status=404
            )
        
        # Si no existe en modelo nuevo, intenta con antiguo
        rutina_antigua = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
        
        # Eliminar el ejercicio del modelo antiguo
        ejercicio_rutina = AdminGymEjercicioRutina.objects.get(id=ejercicio_id, rutina=rutina_antigua)
        ejercicio_rutina.delete()
        
        logger.info(f"Ejercicio antiguo {ejercicio_id} eliminado de rutina {rutina_id} por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Ejercicio eliminado correctamente'
        })
        
    except AdminGymRutina.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Rutina no encontrada'},
            status=404
        )
    except AdminGymEjercicioRutina.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Ejercicio no encontrado'},
            status=404
        )
    except Exception as e:
        logger.error(f"Error eliminando ejercicio: {e}", exc_info=True)
        transaction.set_rollback(True)
        return JsonResponse(
            {'success': False, 'message': f'Error: {str(e)}'},
            status=500
        )


@login_required
def exportar_rutinas_csv(request):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = 'rutinas_{}.csv'.format(timestamp)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(['ID Rutina', 'Nombre Rutina', 'Objetivo', 'Tipo', 'Estado', 'Fecha Creación', 'Ejercicio', 'Series', 'Repeticiones', 'Peso Sugerido', 'Descanso (s)'])

        rutinas = AdminGymRutina.objects.filter(creado_por=request.user).order_by('-fecha_creacion')
        for r in rutinas:
            meta = _unpack_rutina_descripcion(r.descripcion)
            ejercicios = AdminGymEjercicioRutina.objects.filter(rutina=r).select_related('ejercicio').order_by('orden')

            if ejercicios.exists():
                for er in ejercicios:
                    writer.writerow([
                        r.id,
                        r.nombre,
                        r.objetivo,
                        meta.get('tipo', 'personalizada'),
                        meta.get('status', 'activa'),
                        r.fecha_creacion.strftime('%Y-%m-%d %H:%M') if getattr(r, 'fecha_creacion', None) else '',
                        getattr(er.ejercicio, 'nombre', 'Ejercicio'),
                        er.series or '',
                        er.repeticiones or '',
                        er.peso_sugerido or '',
                        er.tiempo_descanso or '',
                    ])
            else:
                writer.writerow([
                    r.id,
                    r.nombre,
                    r.objetivo,
                    meta.get('tipo', 'personalizada'),
                    meta.get('status', 'activa'),
                    r.fecha_creacion.strftime('%Y-%m-%d %H:%M') if getattr(r, 'fecha_creacion', None) else '',
                    'Sin ejercicios', '', '', '', ''
                ])

        return response
    except Exception as e:
        logger.exception('[RUTINA] error exportando rutinas CSV: %s', e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@transaction.atomic
def upload_ejercicio_video(request):
    """Recibe multipart POST con campo 'video' y opcional 'ejercicio_id'.
    Guarda el archivo en MEDIA_ROOT/exercises/ y, si se proporciona ejercicio_id,
    asigna el archivo al campo Ejercicio.video y actualiza ejercicio.video_url.
    Retorna JSON con la url pública y duración (si se pudo calcular con ffprobe).
    """
    if request.method != 'POST' or 'video' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No video provided'}, status=400)

    video_file = request.FILES['video']
    ejercicio_id = request.POST.get('ejercicio_id')

    # Validar tamaño (máx 100 MB)
    MAX_SIZE = 100 * 1024 * 1024
    if video_file.size > MAX_SIZE:
        return JsonResponse({'success': False, 'error': 'Archivo demasiado grande (máx 100MB)'}, status=400)

    # Guardar archivo con nombre único
    filename = f"{uuid.uuid4()}_{video_file.name}"
    save_path = os.path.join('exercises', filename)
    full_path = os.path.join(settings.MEDIA_ROOT, save_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        # Usar default_storage para ser compatible con storages remotas en el futuro
        with default_storage.open(save_path, 'wb+') as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)
    except Exception as e:
        logger.exception('Error al guardar archivo de video: %s', e)
        return JsonResponse({'success': False, 'error': 'Error saving file'}, status=500)

    # Obtener duración con ffprobe (si está disponible)
    duration = None
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', full_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
        )
        out = result.stdout.decode().strip()
        if out:
            try:
                duration = float(out)
            except Exception:
                duration = None
    except Exception:
        # ffprobe puede no estar disponible; no bloquear la subida
        duration = None

    # Construir URL pública
    video_url = request.build_absolute_uri(settings.MEDIA_URL + save_path)

    # Guardar en el modelo si se envió ejercicio_id
    if ejercicio_id:
        try:
            ejercicio = Ejercicio.objects.filter(id=ejercicio_id).first()
            if ejercicio:
                ejercicio.video.name = save_path
                ejercicio.video_url = video_url
                ejercicio.save()
        except Exception as e:
            logger.exception('Error al asociar video al Ejercicio %s: %s', ejercicio_id, e)

    return JsonResponse({
        'success': True,
        'video_url': video_url,
        'video_duration_s': duration
    })


@login_required
@transaction.atomic
def completar_ejercicio(request):
    """POST /api/entrenamientos/completar/
    Payload esperado (JSON): {"rutina_id": 7, "ejercicio": "Flexiones", "repeticiones": 12, "peso": "10kg", "notas": "..."}
    Registra una fila en la tabla administrativa `entrenamiento_log` (modelo AdminGymEntrenamientoLog mapeado como EntrenamientoLog).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body or '{}')
        rutina_id = data.get('rutina_id')
        ejercicio_nombre = (data.get('ejercicio') or '').strip()
        repeticiones = _parse_int(data.get('repeticiones'), None)
        peso = data.get('peso', '')
        notas = data.get('notas', '')

        if not ejercicio_nombre:
            return JsonResponse({'success': False, 'error': 'Nombre de ejercicio requerido'}, status=400)

        rutina_obj = None
        if rutina_id:
            rutina_obj = AdminGymRutina.objects.filter(id=rutina_id).first()

        # Crear registro en la tabla administradora
        EntrenamientoLog.objects.create(
            usuario=request.user,
            rutina=rutina_obj,
            ejercicio_nombre=ejercicio_nombre,
            repeticiones=repeticiones or None,
            fecha=timezone.now(),
        )

        logger.info('[ENTRENAMIENTO] completar_ejercicio user=%s rutina=%s ejercicio=%s reps=%s', request.user, rutina_id, ejercicio_nombre, repeticiones)
        return JsonResponse({'success': True})
    except Exception as e:
        logger.exception('[ENTRENAMIENTO] completar_ejercicio error: %s', e)
        transaction.set_rollback(True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def volumen_ejercicio(request):
    """GET /api/analytics/volumen-ejercicio/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
    Retorna sumatoria de repeticiones por ejercicio_nombre para el usuario autenticado.
    """
    try:
        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        if not desde or not hasta:
            # por defecto, última semana (lunes a domingo)
            hoy = date.today()
            inicio_semana = hoy - timezone.timedelta(days=hoy.weekday())
            fin_semana = inicio_semana + timezone.timedelta(days=6)
            desde = inicio_semana.isoformat()
            hasta = fin_semana.isoformat()

        desde_date = datetime.strptime(desde, '%Y-%m-%d').date()
        hasta_date = datetime.strptime(hasta, '%Y-%m-%d').date()

        qs = EntrenamientoLog.objects.filter(usuario=request.user, fecha__range=[desde_date, hasta_date])
        agg = qs.values('ejercicio_nombre').annotate(total_reps=Sum('repeticiones')).order_by('-total_reps')
        result = [{'ejercicio': a['ejercicio_nombre'], 'total_repeticiones': int(a['total_reps'] or 0)} for a in agg]
        return JsonResponse({'success': True, 'desde': desde, 'hasta': hasta, 'volumen': result})
    except Exception as e:
        logger.exception('[ANALYTICS] volumen_ejercicio error: %s', e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def obtener_alumnos(request):
    """GET /api/alumnos/ -> lista de clientes del gimnasio con asistencias reales
    Devuelve: [{id, cliente_id, nombre, email, ultima_asistencia, ...}, ...]
    """
    logger.info(f'[ALUMNOS] obtener_alumnos llamado - Method: {request.method}')
    
    # MODO DEBUG: Devolver datos hardcodeados primero para probar el frontend
    debug_mode = True  # Cambiar a False cuando funcione
    
    if debug_mode:
        logger.info('[ALUMNOS] MODO DEBUG - Devolviendo datos hardcodeados')
        alumnos_debug = [
            {
                'id': 28,
                'cliente_id': 28,
                'nombre': 'brandon',
                'email': 'riotytmc@gmail.com',
                'username': '21.515.841-1',
                'rut': '21.515.841-1',
                'telefono': '918288312',
                'membresia': 'anual',
                'rutinas_asignadas': 1,
                'total_asistencias': 0,
                'ultima_asistencia': None,
                'activo': True
            },
            {
                'id': 29,
                'cliente_id': 29,
                'nombre': 'Branko Alejandro Plaza Gonzalez',
                'email': 'branko.plaza@inacapmail.cl',
                'username': '21.473.865-1',
                'rut': '21.473.865-1',
                'telefono': '962607213',
                'membresia': '6m',
                'rutinas_asignadas': 1,
                'total_asistencias': 2,
                'ultima_asistencia': '2025-11-04',
                'activo': True
            },
            {
                'id': 30,
                'cliente_id': 30,
                'nombre': 'feer',
                'email': 'fernandresp12@gmail.com',
                'username': '21.415.345-9',
                'rut': '21.415.345-9',
                'telefono': '962607213',
                'membresia': 'anual',
                'rutinas_asignadas': 2,
                'total_asistencias': 0,
                'ultima_asistencia': None,
                'activo': True
            }
        ]
        
        logger.info(f'[ALUMNOS] DEBUG - Devolviendo {len(alumnos_debug)} alumnos hardcodeados')
        response = JsonResponse(alumnos_debug, safe=False)
        response['Content-Type'] = 'application/json; charset=utf-8'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
        return response
    
    # MODO NORMAL: Consultar base de datos
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Obtener clientes con última asistencia real
            cursor.execute("""
                SELECT c.id, c.nombre, c.email, c.rut, c.telefono, c.membresia,
                       COUNT(DISTINCT rc.id) as rutinas_asignadas,
                       COUNT(DISTINCT a.id) as total_asistencias,
                       MAX(a.fecha) as ultima_asistencia,
                       c.activo
                FROM admin_gym_cliente c
                LEFT JOIN admin_gym_rutinacliente rc ON c.id = rc.cliente_id AND rc.activa = 1
                LEFT JOIN admin_gym_asistencia a ON c.id = a.cliente_id
                WHERE c.activo = 1
                GROUP BY c.id, c.nombre, c.email, c.rut, c.telefono, c.membresia, c.activo
                ORDER BY c.nombre
            """)
            
            clientes_data = cursor.fetchall()
        
        logger.info(f'[ALUMNOS] Encontrados {len(clientes_data)} clientes activos')
        
        alumnos = []
        for cliente in clientes_data:
            cliente_id, nombre, email, rut, telefono, membresia, rutinas_asignadas, total_asistencias, ultima_asistencia, activo = cliente
            
            alumno = {
                'id': cliente_id,
                'cliente_id': cliente_id,
                'nombre': nombre or 'Sin nombre',
                'email': email or 'Sin email',
                'username': rut or f'cliente_{cliente_id}',
                'rut': rut or '',
                'telefono': telefono or 'No registrado',
                'membresia': membresia or 'Sin membresía',
                'rutinas_asignadas': int(rutinas_asignadas or 0),
                'total_asistencias': int(total_asistencias or 0),
                'ultima_asistencia': ultima_asistencia.strftime('%Y-%m-%d') if ultima_asistencia else None,
                'activo': bool(activo)
            }
            alumnos.append(alumno)
            logger.info(f'[ALUMNOS] Procesado alumno: {nombre} (ID: {cliente_id})')
        
        logger.info(f'[ALUMNOS] Devolviendo {len(alumnos)} alumnos')
        response = JsonResponse(alumnos, safe=False)
        response['Content-Type'] = 'application/json; charset=utf-8'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
        return response
        
    except Exception as e:
        logger.exception('[ALUMNOS] error obteniendo alumnos: %s', e)
        error_response = JsonResponse({
            'error': str(e),
            'message': 'Error interno del servidor'
        }, status=500)
        error_response['Content-Type'] = 'application/json; charset=utf-8'
        return error_response


@login_required
@require_http_methods(["GET"])
def obtener_alumnos_rutina(request, rutina_id):
    """GET /api/rutinas/<id>/alumnos/ -> ids de alumnos asignados a la rutina (int array)
    """
    try:
        # Intentar obtener la rutina administrativa
        try:
            rut = AdminGymRutina.objects.get(id=rutina_id)
        except AdminGymRutina.DoesNotExist:
            rut = None

        # Primero intentar obtener asignaciones desde AdminGymRutinaCliente
        asignados_ids = []
        try:
            if rut is not None:
                asignados = AdminGymRutinaCliente.objects.filter(rutina=rut)
                # AdminGymRutinaCliente usualmente apunta a AdminGymCliente, que contiene user_id
                for a in asignados:
                    uid = getattr(a, 'cliente_id', None) or getattr(getattr(a, 'cliente', None), 'user_id', None)
                    if uid:
                        asignados_ids.append(int(uid))
        except Exception:
            asignados_ids = []

        # También intentar obtener desde modelo local 'Rutina' si existe
        try:
            from .models import Rutina as LocalRutina
            local = LocalRutina.objects.filter(pk=rutina_id).first()
            if local:
                local_ids = list(local.alumnos.values_list('id', flat=True))
                # combinar y deduplicar
                asignados_ids = sorted(set(asignados_ids) | set(local_ids))
        except Exception:
            pass

        return JsonResponse({'success': True, 'alumnos': asignados_ids})
    except Exception as e:
        logger.exception('[ALUMNOS_RUTINA] error: %s', e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def asignar_rutina_a_alumnos(request, rutina_id):
    """POST /api/rutinas/<id>/asignar/  body: { "alumnos": [1,2,3] }
    Intenta asignar tanto en modelos administrativos como en el modelo local Rutina.
    """
    try:
        try:
            rutina = AdminGymRutina.objects.get(id=rutina_id, creado_por=request.user)
        except AdminGymRutina.DoesNotExist:
            # Es posible que el flujo use el modelo local; intentar obtener solo por id
            rutina = None

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

        ids = payload.get('alumnos')
        if not isinstance(ids, list):
            return JsonResponse({'success': False, 'error': 'Campo "alumnos" requerido como lista de ids'}, status=400)

        User = get_user_model()
        usuarios_qs = User.objects.filter(id__in=ids, is_active=True)

        # Intentar aplicar a AdminGymRutinaCliente (modelo administrativo)
        try:
            if rutina is not None:
                # eliminar asignaciones previas y crear nuevas
                AdminGymRutinaCliente.objects.filter(rutina=rutina).delete()
                clientes = AdminGymCliente.objects.filter(user_id__in=[u.id for u in usuarios_qs])
                for c in clientes:
                    try:
                        AdminGymRutinaCliente.objects.create(
                            rutina=rutina, 
                            cliente=c,
                            asignado_por=request.user,
                            fecha_asignacion=timezone.now(),
                            activa=True
                        )
                    except Exception:
                        # campo/estructura diferente en admin model, ignorar
                        continue
        except Exception:
            logger.exception('[ASIGNAR] error actualizando AdminGymRutinaCliente')

        # Intentar aplicar también al modelo local 'Rutina' si existe
        applied_count = 0
        try:
            from .models import Rutina as LocalRutina
            local = LocalRutina.objects.filter(pk=rutina_id).first()
            if local:
                local.alumnos.set(usuarios_qs)
                local.save()
                applied_count = usuarios_qs.count()
        except Exception:
            # si falla, intentar contar al menos los usuarios encontrados
            applied_count = usuarios_qs.count()

        return JsonResponse({'success': True, 'count': applied_count})
    except Exception as e:
        logger.exception('[ASIGNAR] error asignando alumnos: %s', e)
        transaction.set_rollback(True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
