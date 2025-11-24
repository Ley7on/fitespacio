# views_rutinas_personalizadas.py - Manejo de rutinas personalizadas del entrenador

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import connection, transaction
import json
import logging
import random
from datetime import date, timedelta

logger = logging.getLogger(__name__)

@login_required
@csrf_protect
def crear_rutina_personalizada(request):
    """Crear rutina personalizada completa con ejercicios para un cliente específico"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        data = json.loads(request.body)
        
        # Validar datos requeridos
        nombre = data.get('nombre', '').strip()
        objetivo = data.get('objetivo', '').strip()
        cliente_id = data.get('cliente_id')
        ejercicios = data.get('ejercicios', [])
        
        if not nombre or not objetivo or not cliente_id:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan datos obligatorios: nombre, objetivo y cliente'
            })
        
        if not ejercicios:
            return JsonResponse({
                'success': False, 
                'message': 'Debe incluir al menos un ejercicio'
            })
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                # 1. Crear la rutina principal - incluir es_plantilla y fecha_creacion
                cursor.execute("""
                    INSERT INTO admin_gym_rutina 
                    (nombre, descripcion, objetivo, creado_por_id, activa, es_plantilla, fecha_creacion)
                    VALUES (%s, %s, %s, %s, 1, 0, NOW())
                """, [
                    nombre,
                    data.get('descripcion', ''),
                    objetivo,
                    request.user.id
                ])
                
                rutina_id = cursor.lastrowid
                
                # 2. Crear los ejercicios de la rutina
                for i, ejercicio_data in enumerate(ejercicios, 1):
                    # Primero verificar si el ejercicio existe, si no, crearlo
                    cursor.execute("""
                        SELECT id FROM admin_gym_ejercicio WHERE nombre = %s LIMIT 1
                    """, [ejercicio_data['nombre']])
                    
                    ejercicio_row = cursor.fetchone()
                    
                    if ejercicio_row:
                        ejercicio_id = ejercicio_row[0]
                    else:
                        # Crear nuevo ejercicio - incluir todos los campos requeridos
                        cursor.execute("""
                            INSERT INTO admin_gym_ejercicio 
                            (nombre, descripcion, tipo, grupo_muscular, instrucciones, activo)
                            VALUES (%s, %s, %s, %s, %s, 1)
                        """, [
                            ejercicio_data['nombre'],
                            f"Ejercicio creado por {request.user.username}",
                            ejercicio_data.get('tipo', 'fuerza'),
                            ejercicio_data.get('grupo_muscular', 'general'),
                            ejercicio_data.get('instrucciones', '')
                        ])
                        ejercicio_id = cursor.lastrowid
                    
                    # Crear la relación ejercicio-rutina
                    cursor.execute("""
                        INSERT INTO admin_gym_ejerciciorutina 
                        (rutina_id, ejercicio_id, series, repeticiones, peso_sugerido, 
                         tiempo_descanso, notas, orden, video_url, video_duration_s)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        rutina_id,
                        ejercicio_id,
                        ejercicio_data.get('series', 3),
                        ejercicio_data.get('repeticiones', 10),
                        ejercicio_data.get('peso_sugerido', 0),
                        ejercicio_data.get('tiempo_descanso', 60),
                        ejercicio_data.get('notas', ''),
                        i,  # orden secuencial
                        '',
                        0
                    ])
                
                # 3. Asignar la rutina al cliente
                cursor.execute("""
                    INSERT INTO admin_gym_rutinacliente 
                    (cliente_id, rutina_id, asignado_por_id, activa, fecha_asignacion, fecha_inicio)
                    VALUES (%s, %s, %s, 1, NOW(), CURDATE())
                """, [
                    cliente_id,
                    rutina_id,
                    request.user.id
                ])
        
        logger.info(f"Rutina personalizada creada: ID={rutina_id}, Cliente={cliente_id}, Entrenador={request.user.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina creada y asignada exitosamente',
            'rutina_id': rutina_id,
            'ejercicios_count': len(ejercicios)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Error en formato JSON'})
    except Exception as e:
        logger.error(f"Error creando rutina personalizada: {e}")
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})

@login_required
def obtener_rutinas_asignadas_alumno(request):
    """API para que el alumno obtenga sus rutinas asignadas por entrenadores"""
    try:
        with connection.cursor() as cursor:
            # Obtener el cliente asociado al usuario actual
            cursor.execute("""
                SELECT id FROM admin_gym_cliente WHERE user_id = %s LIMIT 1
            """, [request.user.id])

            cliente_row = cursor.fetchone()
            if not cliente_row:
                return JsonResponse({'success': True, 'rutinas': [], 'total': 0})

            cliente_id = cliente_row[0]

            # Obtener rutinas asignadas al cliente (agrupadas y con conteo de ejercicios)
            cursor.execute("""
                SELECT 
                    r.id, r.nombre, r.objetivo, r.descripcion, 
                    rc.fecha_asignacion, rc.activa,
                    u.first_name, u.last_name, u.username,
                    COUNT(DISTINCT e.id) as ejercicios_count
                FROM admin_gym_rutina r
                LEFT JOIN admin_gym_rutinacliente rc ON r.id = rc.rutina_id
                LEFT JOIN admin_gym_ejerciciorutina er ON r.id = er.rutina_id
                LEFT JOIN admin_gym_ejercicio e ON er.ejercicio_id = e.id
                LEFT JOIN auth_user u ON rc.asignado_por_id = u.id
                WHERE rc.cliente_id = %s AND rc.activa = 1
                GROUP BY r.id, r.nombre, r.objetivo, r.descripcion, rc.fecha_asignacion, rc.activa, u.first_name, u.last_name, u.username
                ORDER BY rc.fecha_asignacion DESC
            """, [cliente_id])

            rutinas_rows = cursor.fetchall()

        rutinas = []
        for row in rutinas_rows:
            entrenador_nombre = f"{row[6]} {row[7]}".strip() if row[6] or row[7] else (row[8] or '')
            if not entrenador_nombre.strip():
                entrenador_nombre = 'Sistema'

            rutinas.append({
                'id': row[0],
                'nombre': row[1],
                'objetivo': row[2].replace('_', ' ').title() if row[2] else 'General',
                'descripcion': row[3] or '',
                'fecha_asignacion': row[4].strftime('%d/%m/%Y') if row[4] else 'Reciente',
                'fecha_inicio': row[4].strftime('%d/%m/%Y') if row[4] else 'Reciente',
                'activa': bool(row[5]),
                'tipo': 'asignada',
                'dia_asignado': None,
                'notas': '',
                'entrenador': entrenador_nombre,
                'ejercicios_count': row[9] or 0
            })

        return JsonResponse({
            'success': True,
            'rutinas': rutinas,
            'total': len(rutinas)
        })

    except Exception as e:
        logger.error(f"Error obteniendo rutinas asignadas: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_rutinas_personales_alumno(request):
    """API para que el alumno obtenga sus rutinas personales creadas por él mismo"""
    try:
        from alumno.models import PerfilAlumno, RutinaAlumno
        
        # Obtener perfil del alumno
        try:
            perfil = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': True, 'rutinas': [], 'total': 0})
        
        # Obtener rutinas personales (tipo='personal') con conteo de ejercicios para evitar N+1
        from django.db.models import Count

        rutinas_query = RutinaAlumno.objects.filter(
            alumno=perfil,
            tipo='personal',
            activa=True
        ).annotate(ejercicios_count=Count('ejercicios')).order_by('-fecha_creacion')

        rutinas = []
        for rutina in rutinas_query:
            rutinas.append({
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.objetivo.replace('_', ' ').title(),
                'descripcion': rutina.descripcion or '',
                'fecha_creacion': rutina.fecha_creacion.strftime('%d/%m/%Y'),
                'fecha_inicio': rutina.fecha_creacion.strftime('%d/%m/%Y'),
                'activa': rutina.activa,
                'tipo': 'personal',
                'dia_asignado': rutina.dia_asignado.title() if rutina.dia_asignado else None,
                'ejercicios_count': getattr(rutina, 'ejercicios_count', 0)
            })
        
        return JsonResponse({
            'success': True,
            'rutinas': rutinas,
            'total': len(rutinas)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo rutinas personales: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_calendario_semanal_alumno(request):
    """API para obtener el calendario semanal del alumno con rutinas asignadas a días"""
    try:
        from alumno.models import PerfilAlumno, RutinaAlumno
        
        # Obtener perfil del alumno
        try:
            perfil = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            calendario = {
                'lunes': [], 'martes': [], 'miercoles': [], 'jueves': [],
                'viernes': [], 'sabado': [], 'domingo': []
            }
            return JsonResponse({'success': True, 'calendario': calendario})
        
        # Obtener rutinas activas con día asignado
        rutinas_query = RutinaAlumno.objects.filter(
            alumno=perfil,
            activa=True,
            dia_asignado__isnull=False
        )
        
        # Mapear días en español a keys del calendario
        dias_map = {
            'lunes': 'lunes',
            'martes': 'martes',
            'miercoles': 'miercoles',
            'jueves': 'jueves',
            'viernes': 'viernes',
            'sábado': 'sabado',
            'sabado': 'sabado',
            'domingo': 'domingo'
        }
        
        calendario = {
            'lunes': [], 'martes': [], 'miercoles': [], 'jueves': [],
            'viernes': [], 'sabado': [], 'domingo': []
        }
        
        for rutina in rutinas_query:
            dia_key = dias_map.get(rutina.dia_asignado.lower(), None)
            if dia_key and dia_key in calendario:
                calendario[dia_key].append({
                    'id': rutina.id,
                    'nombre': rutina.nombre,
                    'tipo': rutina.tipo,
                    'objetivo': rutina.objetivo,
                    'ejercicios_count': rutina.ejercicios.count()
                })
        
        return JsonResponse({
            'success': True,
            'calendario': calendario
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo calendario semanal: {e}", exc_info=True)
        calendario = {
            'lunes': [], 'martes': [], 'miercoles': [], 'jueves': [],
            'viernes': [], 'sabado': [], 'domingo': []
        }
        return JsonResponse({'success': False, 'error': str(e), 'calendario': calendario})

@login_required
def obtener_detalle_rutina(request, rutina_id):
    """API para obtener detalle completo de una rutina específica"""
    try:
        with connection.cursor() as cursor:
            # Verificar que el usuario tenga acceso a esta rutina
            cursor.execute("""
                SELECT r.id, r.nombre, r.descripcion, r.objetivo, r.fecha_creacion,
                       u.first_name, u.last_name, u.username
                FROM admin_gym_rutina r
                LEFT JOIN auth_user u ON r.creado_por_id = u.id
                LEFT JOIN admin_gym_rutinacliente rc ON r.id = rc.rutina_id
                LEFT JOIN admin_gym_cliente c ON rc.cliente_id = c.id
                WHERE r.id = %s AND (r.creado_por_id = %s OR c.user_id = %s)
                LIMIT 1
            """, [rutina_id, request.user.id, request.user.id])
            
            rutina_row = cursor.fetchone()
            if not rutina_row:
                return JsonResponse({'success': False, 'message': 'Rutina no encontrada o sin permisos'})
            
            # Obtener ejercicios de la rutina con todos los detalles
            cursor.execute("""
                SELECT e.nombre, er.series, er.repeticiones, er.peso_sugerido, 
                       er.tiempo_descanso, er.notas, er.orden, e.descripcion,
                       e.tipo, e.grupo_muscular
                FROM admin_gym_ejerciciorutina er
                JOIN admin_gym_ejercicio e ON er.ejercicio_id = e.id
                WHERE er.rutina_id = %s
                ORDER BY er.orden
            """, [rutina_id])
            
            ejercicios_data = cursor.fetchall()
        
        # Formatear datos de la rutina
        entrenador_nombre = f"{rutina_row[5]} {rutina_row[6]}".strip() if rutina_row[5] else rutina_row[7]
        
        ejercicios = []
        for ej in ejercicios_data:
            ejercicios.append({
                'nombre': ej[0],
                'series': ej[1] or 3,
                'repeticiones': ej[2] or 10,
                'peso': f"{ej[3]}kg" if ej[3] and ej[3] > 0 else 'Sin peso',
                'descanso': f"{ej[4]}s" if ej[4] else '60s',
                'notas': ej[5] or 'Sin notas adicionales',
                'orden': ej[6] or 1,
                'descripcion': ej[7] or '',
                'tipo': ej[8] or 'fuerza',
                'grupo_muscular': ej[9] or 'general'
            })
        
        rutina_data = {
            'id': rutina_row[0],
            'nombre': rutina_row[1],
            'descripcion': rutina_row[2] or 'Sin descripción',
            'objetivo': rutina_row[3],
            'fecha_creacion': 'Reciente',
            'entrenador': entrenador_nombre or 'Sistema',
            'ejercicios': ejercicios
        }
        
        return JsonResponse({
            'success': True,
            'rutina': rutina_data
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo detalle de rutina: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def rutina_detail_api(request, rutina_id):
    """RESTful minimal endpoint for a RutinaAlumno resource. Supports DELETE to soft-delete and PATCH to partially update.
    DELETE -> soft-delete (activa=False) if owner and tipo='personal'
    PATCH -> partial update (delegates to editar logic)
    """
    try:
        from alumno.models import PerfilAlumno, RutinaAlumno
        import json

        try:
            perfil = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Perfil no encontrado'}, status=404)

        try:
            rutina = RutinaAlumno.objects.get(id=rutina_id, alumno=perfil)
        except RutinaAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Rutina no encontrada o sin permisos'}, status=404)

        if request.method == 'DELETE':
            if rutina.tipo != 'personal':
                return JsonResponse({'success': False, 'message': 'No permitido eliminar rutinas asignadas por entrenador'}, status=403)
            # Soft-delete
            rutina.activa = False
            rutina.save()
            # Return 204 No Content to align with REST clients
            from django.http import HttpResponse
            return HttpResponse(status=204)

        if request.method in ('PATCH', 'POST'):
            # allow partial updates similar to editar_rutina_personal_alumno
            data = json.loads(request.body or '{}')
            changed = False
            if 'nombre' in data:
                nombre = str(data.get('nombre') or '').strip()
                if nombre == '':
                    return JsonResponse({'success': False, 'message': 'El nombre no puede estar vacío'}, status=400)
                rutina.nombre = nombre; changed = True
            if 'descripcion' in data:
                rutina.descripcion = data.get('descripcion') or '' ; changed = True
            if 'dia_asignado' in data:
                allowed_days = [c[0] for c in RutinaAlumno.DIAS_CHOICES]
                dia = data.get('dia_asignado') or ''
                if dia and dia not in allowed_days:
                    return JsonResponse({'success': False, 'message': 'Día inválido'}, status=400)
                rutina.dia_asignado = dia or None; changed = True
            if 'objetivo' in data:
                allowed_obj = [c[0] for c in RutinaAlumno.OBJETIVO_CHOICES]
                obj = data.get('objetivo')
                if obj and obj not in allowed_obj:
                    return JsonResponse({'success': False, 'message': 'Objetivo inválido'}, status=400)
                rutina.objetivo = obj; changed = True
            if 'activa' in data:
                rutina.activa = bool(data.get('activa')) ; changed = True

            if changed:
                rutina.save()

            return JsonResponse({'success': True, 'message': 'Rutina actualizada'})

        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    except Exception as e:
        logger.error(f"Error in rutina_detail_api: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def editar_rutina_personal_alumno(request, rutina_id):
    """Editar campos de una RutinaAlumno (solo si pertenece al alumno y es tipo 'personal').
    Acepta POST con JSON: {"nombre":..., "descripcion":..., "dia_asignado":..., "objetivo":..., "activa": true/false}
    """
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

        from alumno.models import PerfilAlumno, RutinaAlumno
        import json

        # Obtener perfil y rutina
        try:
            perfil = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Perfil de alumno no encontrado'}, status=404)

        try:
            rutina = RutinaAlumno.objects.get(id=rutina_id, alumno=perfil)
        except RutinaAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Rutina no encontrada o sin permisos'}, status=404)

        # Solo permitir editar rutinas personales
        if rutina.tipo != 'personal':
            return JsonResponse({'success': False, 'message': 'No permitido editar rutinas asignadas por entrenador'}, status=403)

        data = json.loads(request.body or '{}')

        # Validaciones mínimas
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        dia = data.get('dia_asignado')
        objetivo = data.get('objetivo')
        activa = data.get('activa')

        changed = False
        if nombre is not None:
            nombre = str(nombre).strip()
            if nombre == '':
                return JsonResponse({'success': False, 'message': 'El nombre no puede estar vacío'}, status=400)
            rutina.nombre = nombre
            changed = True

        if descripcion is not None:
            rutina.descripcion = str(descripcion)
            changed = True

        if dia is not None:
            # Validate allowed days
            allowed_days = [c[0] for c in RutinaAlumno.DIAS_CHOICES]
            if dia not in allowed_days and dia != '':
                return JsonResponse({'success': False, 'message': 'Día inválido'}, status=400)
            rutina.dia_asignado = dia or None
            changed = True

        if objetivo is not None:
            allowed_obj = [c[0] for c in RutinaAlumno.OBJETIVO_CHOICES]
            if objetivo not in allowed_obj:
                return JsonResponse({'success': False, 'message': 'Objetivo inválido'}, status=400)
            rutina.objetivo = objetivo
            changed = True

        if activa is not None:
            rutina.activa = bool(activa)
            changed = True

        if changed:
            rutina.save()

        return JsonResponse({'success': True, 'message': 'Rutina actualizada', 'rutina_id': rutina.id})

    except Exception as e:
        logger.error(f"Error editando rutina personal: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def eliminar_rutina_personal_alumno(request, rutina_id):
    """Eliminar (soft-delete) una RutinaAlumno personal del alumno.
    Método: POST
    """
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

        from alumno.models import PerfilAlumno, RutinaAlumno
        import json

        try:
            perfil = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Perfil de alumno no encontrado'}, status=404)

        try:
            rutina = RutinaAlumno.objects.get(id=rutina_id, alumno=perfil)
        except RutinaAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Rutina no encontrada o sin permisos'}, status=404)

        if rutina.tipo != 'personal':
            return JsonResponse({'success': False, 'message': 'No permitido eliminar rutinas asignadas por entrenador'}, status=403)

        # Soft delete: marcar como inactiva
        rutina.activa = False
        rutina.save()

        return JsonResponse({'success': True, 'message': 'Rutina eliminada (inactiva)'} )

    except Exception as e:
        logger.error(f"Error eliminando rutina personal: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def marcar_rutina_completada(request, rutina_id):
    """
    API para marcar una rutina como completada por el día actual.
    Genera un mensaje motivacional heurístico basado en la consistencia del alumno.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    try:
        from alumno.models import PerfilAlumno, RutinaAlumno, MensajeMotivacional, SesionEntrenamiento
        
        # Obtener perfil del alumno
        try:
            perfil = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Perfil de alumno no encontrado'}, status=404)
        
        # Verificar que la rutina existe y pertenece al alumno
        try:
            # Buscar tanto en RutinaAlumno como en admin_gym_rutinacliente
            rutina = None
            try:
                rutina = RutinaAlumno.objects.get(id=rutina_id, alumno=perfil)
            except RutinaAlumno.DoesNotExist:
                # Si no existe en RutinaAlumno, buscar en admin_gym
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT r.id, r.nombre
                        FROM admin_gym_rutina r
                        JOIN admin_gym_rutinacliente rc ON r.id = rc.rutina_id
                        JOIN admin_gym_cliente c ON rc.cliente_id = c.id
                        WHERE r.id = %s AND c.user_id = %s AND rc.activa = 1
                        LIMIT 1
                    """, [rutina_id, request.user.id])
                    
                    rutina_row = cursor.fetchone()
                    if not rutina_row:
                        return JsonResponse({'success': False, 'message': 'Rutina no encontrada'}, status=404)
                    
                    # Usar datos de admin_gym
                    rutina_nombre = rutina_row[1]
        except Exception as e:
            logger.error(f"Error buscando rutina: {e}")
            return JsonResponse({'success': False, 'message': 'Rutina no encontrada'}, status=404)
        
        # Obtener nombre de la rutina
        nombre_rutina = rutina.nombre if rutina else rutina_nombre
        
        # Registrar la sesión completada
        hoy = date.today()
        sesion_creada = False
        try:
            sesion, created = SesionEntrenamiento.objects.get_or_create(
                alumno=perfil,
                rutina=rutina if rutina else None,
                fecha=hoy,
                defaults={
                    'rutina_nombre': nombre_rutina
                }
            )
            sesion_creada = created
            
            if not created:
                # Ya existía una sesión hoy para esta rutina
                sesion.fecha_hora = timezone.now()
                sesion.save()
        except Exception as e:
            logger.error(f"Error registrando sesión: {e}")
        
        # Calcular días consecutivos y generar heurística motivacional
        hoy = date.today()
        
        # Contar sesiones completadas en los últimos 7 días usando SesionEntrenamiento
        hace_7_dias = hoy - timedelta(days=7)
        sesiones_recientes = SesionEntrenamiento.objects.filter(
            alumno=perfil,
            fecha__gte=hace_7_dias
        ).values('fecha').distinct().count()  # Contar días únicos
        
        # Verificar si ya completó hoy (basado en sesiones registradas)
        ya_completo_hoy = not sesion_creada  # Si no se creó sesión nueva, ya había completado hoy
        
        # Generar mensaje motivacional basado en heurística
        if ya_completo_hoy:
            mensajes = [
                "¡Ya completaste tu rutina hoy! Descansa y recupérate para mañana 💪",
                "¡Increíble dedicación! Ya registraste tu rutina hoy. El descanso también es clave 🌟",
                "¡Wow! Ya marcaste tu rutina hoy. Recuerda que el descanso es parte del éxito 🎯"
            ]
            mensaje = random.choice(mensajes)
        elif sesiones_recientes >= 5:
            # Muy consistente (5+ sesiones en 7 días)
            mensajes = [
                "¡Vas excelente! 🔥 Tu consistencia es impresionante. ¡Sigue así!",
                "¡Increíble racha! 💪 Tu disciplina está dando frutos. ¡No pares!",
                "¡Eres imparable! 🌟 Esta rutina es evidencia de tu compromiso. ¡Sigue así!",
                "¡Brutal! 🚀 Tu constancia es de campéon. ¡A por más!",
                "¡Espectacular! ⭐ Estás en fuego esta semana. ¡Sigue adelante!"
            ]
            mensaje = random.choice(mensajes)
        elif sesiones_recientes >= 3:
            # Consistencia moderada (3-4 sesiones en 7 días)
            mensajes = [
                "¡Vas muy bien! 💪 Mantén este ritmo y alcanzarás tus metas",
                "¡Excelente trabajo! 🌟 Tu constancia te llevará lejos",
                "¡Sigue así! 🔥 Cada entrenamiento cuenta. ¡Vas genial!",
                "¡Bien hecho! 🎯 Estás construyendo un gran hábito",
                "¡Fantástico! ⚡ Tu esfuerzo está marcando la diferencia"
            ]
            mensaje = random.choice(mensajes)
        elif sesiones_recientes >= 1:
            # Empezando a crear hábito (1-2 sesiones en 7 días)
            mensajes = [
                "¡Buen inicio! 💪 Cada entrenamiento te acerca a tu objetivo",
                "¡Vas bien! 🌟 La consistencia es clave. ¡Sigue adelante!",
                "¡Excelente! 🔥 Estás formando un gran hábito",
                "¡Bien hecho! 🎯 Paso a paso se llega lejos",
                "¡Genial! ⚡ Cada sesión cuenta. ¡Continúa así!"
            ]
            mensaje = random.choice(mensajes)
        else:
            # Primera sesión o retomando después de inactividad
            mensajes = [
                "¡Excelente decisión! 🌟 Hoy diste el primer paso. ¡Sigue así!",
                "¡Bienvenido de vuelta! 💪 Lo importante es empezar. ¡Vas bien!",
                "¡Gran trabajo! 🔥 Hoy comenzaste algo grande. ¡Adelante!",
                "¡Felicitaciones! 🎯 El primer paso es el más importante",
                "¡Perfecto! ⚡ Comenzar es la mitad del camino. ¡Sigue adelante!"
            ]
            mensaje = random.choice(mensajes)
        
        # Registrar la sesión completada como mensaje motivacional
        try:
            MensajeMotivacional.objects.create(
                alumno=perfil,
                tipo='entrenamiento_completado',
                titulo=f'Rutina "{nombre_rutina}" completada',
                contenido=mensaje,
                nivel='success',
                prioridad=3,
                origen='sistema_rutinas',
                fecha_envio=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error creando mensaje motivacional: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina marcada como completada',
            'mensaje_motivacional': mensaje,
            'sesiones_esta_semana': sesiones_recientes + 1
        })
        
    except Exception as e:
        logger.error(f"Error marcando rutina completada: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)