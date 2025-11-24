# entrenador/views.py - Vistas consolidadas

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.utils.html import escape
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods, require_POST
from datetime import date, datetime, timedelta
import calendar
import logging
import json
import csv
import re
from entrenador_app.auth_views import require_role
from entrenador_app.shift_system import ShiftSystem
from .models import (
    AsistenciaEntrenador, ContadorSeries, PlantillaExcel, EventoCalendario,
    SesionEntrenamiento, RegistroEjercicio, Ejercicio
)
from alumno.models import PerfilAlumno
from alumno.views import crear_mensaje_si_no_duplicado
from entrenador_app.admin_gym_models import (
    AdminGymRutina, AdminGymEjercicioRutina, AdminGymCliente, AdminGymRecomendacionSistema,
    AdminGymRutinaCliente
)

logger = logging.getLogger(__name__)

# ============ UTILIDADES ============

def safe_date_diff(fecha_actual, fecha_comparacion):
    """Calcula diferencia de días entre fechas manejando tipos datetime y date"""
    if not fecha_comparacion:
        return None
    
    # Convertir fecha_actual a date si es datetime
    if hasattr(fecha_actual, 'date'):
        fecha_actual = fecha_actual.date()
    
    # Convertir fecha_comparacion a date si es datetime
    if hasattr(fecha_comparacion, 'date'):
        fecha_comparacion = fecha_comparacion.date()
    
    return (fecha_actual - fecha_comparacion).days

# ============ VISTAS PRINCIPALES ============

@require_role('entrenador')
def dashboard(request):
    try:
        from django.db import connection
        hoy = timezone.now().date()
        
        # Chat removed: skip creation of chat/alert tables (chat feature deprecated)
        
        # DATOS REALES SINCRONIZADOS CON LA BASE DE DATOS
        with connection.cursor() as cursor:
            # 1. Alumnos activos reales con incremento semanal
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_cliente WHERE activo = 1
            """)
            alumnos_activos = cursor.fetchone()[0]
            
            # Calcular nuevos alumnos esta semana
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_cliente 
                WHERE activo = 1 AND DATE(fecha_registro) >= %s
            """, [inicio_semana])
            nuevos_esta_semana = cursor.fetchone()[0]
            
            # 2. Rutinas creadas por este entrenador
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_rutina WHERE creado_por_id = %s
            """, [request.user.id])
            rutinas_creadas = cursor.fetchone()[0]
            
            # 3. Rutinas activas asignadas por este entrenador
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_rutinacliente 
                WHERE asignado_por_id = %s AND activa = 1
            """, [request.user.id])
            rutinas_activas = cursor.fetchone()[0]
            
            # 4. Rutinas completadas por este entrenador
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_rutinacliente 
                WHERE asignado_por_id = %s AND activa = 0
            """, [request.user.id])
            rutinas_completadas = cursor.fetchone()[0]
            
            # 5. Alumnos con rutinas personalizadas (asignadas por este entrenador)
            cursor.execute("""
                SELECT COUNT(DISTINCT cliente_id) FROM admin_gym_rutinacliente 
                WHERE asignado_por_id = %s AND activa = 1
            """, [request.user.id])
            alumnos_personalizados = cursor.fetchone()[0]
            
            # 6. Asistencias del mes actual (datos reales)
            primer_dia_mes = hoy.replace(day=1)
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_asistencia 
                WHERE fecha >= %s AND fecha <= %s
            """, [primer_dia_mes, hoy])
            asistencias_mes = cursor.fetchone()[0]
            
            # 7. Gráfico de asistencia de TODOS LOS ALUMNOS (últimas 4 semanas)
            asistencia_semanas = []
            for i in range(4):
                dias_atras = (i * 7) + hoy.weekday()
                inicio_semana = hoy - timedelta(days=dias_atras)
                fin_semana = inicio_semana + timedelta(days=6)
                
                if fin_semana > hoy:
                    fin_semana = hoy
                
                # Contar asistencias de TODOS los alumnos, no solo del entrenador
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_asistencia 
                    WHERE fecha >= %s AND fecha <= %s
                """, [inicio_semana, fin_semana])
                
                asistencias_semana = cursor.fetchone()[0]
                asistencia_semanas.insert(0, asistencias_semana)
            
            # 8. Alertas pendientes: usar recomendaciones del sistema admin
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_recomendacionsistema 
                    WHERE respondido_por_id = %s AND estado = 'pendiente'
                """, [request.user.id])
                alertas_pendientes = cursor.fetchone()[0]
            except Exception:
                alertas_pendientes = 0
            
            # 9. Mensajes no leídos: chat eliminado, devolver 0
            mensajes_no_leidos = 0
            
            # 10. FUENTE DIRECTA: Tabla entrenador_asistenciaentrenador
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entrenador_asistenciaentrenador (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    entrenador_id INT NOT NULL,
                    fecha DATE NOT NULL,
                    hora_entrada TIME NOT NULL,
                    hora_salida TIME NULL,
                    UNIQUE KEY unique_entrenador_fecha (entrenador_id, fecha)
                )
            """)
            
            cursor.execute("""
                SELECT COUNT(*) FROM entrenador_asistenciaentrenador 
                WHERE entrenador_id = %s AND fecha >= %s AND fecha <= %s
            """, [request.user.id, primer_dia_mes, hoy])
            
            mis_asistencias = cursor.fetchone()[0]
        
        # Obtener rutinas activas como sesiones próximas
        proximas_sesiones = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.nombre, rc.fecha_inicio
                    FROM admin_gym_rutinacliente rc
                    JOIN admin_gym_cliente c ON rc.cliente_id = c.id
                    WHERE rc.asignado_por_id = %s AND rc.activa = 1
                    ORDER BY rc.fecha_asignacion DESC
                    LIMIT 5
                """, [request.user.id])
                
                rutinas_activas_data = cursor.fetchall()
                for rutina in rutinas_activas_data:
                    proximas_sesiones.append({
                        'alumno': rutina[0],
                        'tipo': 'Rutina Activa',
                        'hora': 'Pendiente',
                        'tag': 'Activa'
                    })
        except Exception as e:
            logger.warning(f"No se pudieron cargar rutinas activas: {e}")
            proximas_sesiones = []

        # Cargar alumnos directamente desde la base de datos
        alumnos_lista = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, c.nombre, c.email, c.telefono, c.membresia,
                           COUNT(DISTINCT rc.id) as rutinas_asignadas,
                           MAX(a.fecha) as ultima_asistencia
                    FROM admin_gym_cliente c
                    LEFT JOIN admin_gym_rutinacliente rc ON c.id = rc.cliente_id AND rc.activa = 1
                    LEFT JOIN admin_gym_asistencia a ON c.id = a.cliente_id
                    WHERE c.activo = 1
                    GROUP BY c.id, c.nombre, c.email, c.telefono, c.membresia
                    ORDER BY c.nombre
                    LIMIT 50
                """)
                
                alumnos_data = cursor.fetchall()
                
                for alumno in alumnos_data:
                    alumnos_lista.append({
                        'id': alumno[0],
                        'nombre': alumno[1] or 'Sin nombre',
                        'email': alumno[2] or 'Sin email',
                        'telefono': alumno[3] or 'No registrado',
                        'membresia': alumno[4] or 'Básica',
                        'rutinas_asignadas': alumno[5] or 0,
                        'ultima_asistencia': alumno[6].strftime('%Y-%m-%d') if alumno[6] else None
                    })
        except Exception as e:
            logger.error(f"Error cargando alumnos: {e}")
            # Datos de fallback
            alumnos_lista = [
                {
                    'id': 1,
                    'nombre': 'Juan Pérez',
                    'email': 'juan@email.com',
                    'telefono': '+56912345678',
                    'membresia': 'Premium',
                    'rutinas_asignadas': 2,
                    'ultima_asistencia': '2024-01-15'
                },
                {
                    'id': 2,
                    'nombre': 'María González',
                    'email': 'maria@email.com',
                    'telefono': '+56987654321',
                    'membresia': 'Básica',
                    'rutinas_asignadas': 1,
                    'ultima_asistencia': '2024-01-14'
                }
            ]

        context = {
            'nombre_entrenador': request.user.get_full_name() or request.user.username,
            'alumnos_activos': alumnos_activos,
            'nuevos_esta_semana': nuevos_esta_semana,
            'rutinas_asignadas': rutinas_creadas,
            'rutinas_activas': rutinas_activas,
            'rutinas_completadas': rutinas_completadas,
            'alumnos_personalizados': alumnos_personalizados,
            'proximas_sesiones': proximas_sesiones,
            'asistencia_semanas': asistencia_semanas,
            'asistencias_mes': asistencias_mes,
            'alertas_pendientes': alertas_pendientes,
            'mensajes_no_leidos': mensajes_no_leidos,
            'mis_asistencias': mis_asistencias,
            'alumnos_lista': json.dumps(alumnos_lista),
        }

    except Exception as e:
        logger.error(f"Error en dashboard: {e}")
        # En caso de error, mostrar datos mínimos pero reales
        try:
            alumnos_activos = AdminGymCliente.objects.using('default').filter(activo=True).count()
            rutinas_creadas = AdminGymRutina.objects.using('default').filter(creado_por=request.user).count()
        except Exception:
            alumnos_activos = 0
            rutinas_creadas = 0
            
        context = {
            'nombre_entrenador': request.user.get_full_name() or request.user.username,
            'alumnos_activos': alumnos_activos,
            'rutinas_asignadas': rutinas_creadas,
            'rutinas_activas': 0,
            'rutinas_completadas': 0,
            'alumnos_personalizados': 0,
            'proximas_sesiones': [],
            'asistencia_semanas': [0, 0, 0, 0],
            'asistencias_mes': 0,
            'alertas_pendientes': 0,
            'mensajes_no_leidos': 0,
            'mis_asistencias': 0,
            'error_message': f'Error conectando con la base de datos: {str(e)}'
        }

    return render(request, 'entrenador/dashboard_simple.html', context)

@require_role('entrenador')
def rutinas_plantillas(request):
    """Vista para gestionar rutinas y plantillas del entrenador"""
    try:
        from entrenador.models import Rutina, DetalleEjercicio
        import json
        
        # Obtener rutinas del entrenador (modelo antiguo)
        rutinas_qs = Rutina.objects.filter(
            entrenador=request.user
        ).exclude(tipo='auto_generada').order_by('-fecha_actualizacion')
        
        logger.info(f"[rutinas_plantillas] Usuario: {request.user.username} (ID: {request.user.id})")
        logger.info(f"[rutinas_plantillas] Query encontró: {rutinas_qs.count()} rutinas")
        
        # Serializar manualmente las rutinas
        todas_rutinas = []
        for rutina in rutinas_qs:
            try:
                # Contar ejercicios
                ejercicios_count = DetalleEjercicio.objects.filter(rutina=rutina).count()
                
                rutina_dict = {
                    'id': rutina.id,
                    'nombre': rutina.nombre or 'Sin nombre',
                    'objetivo': rutina.objetivo or 'general',
                    'descripcion': rutina.descripcion or '',
                    'tipo': rutina.tipo,
                    'status': rutina.status,
                    'dificultad': rutina.dificultad or 'intermedio',
                    'duracion_estimada': rutina.duracion_estimada or 60,
                    'frecuencia_semanal': rutina.frecuencia_semanal or 3,
                    'semanas_duracion': getattr(rutina, 'semanas_duracion', 4) or 4,
                    'tags': '',
                    'notas_entrenador': '',
                    'fecha_creacion': rutina.fecha_creacion.isoformat() if rutina.fecha_creacion else '',
                    'fecha_actualizacion': rutina.fecha_actualizacion.isoformat() if rutina.fecha_actualizacion else '',
                    'ejercicios_count': ejercicios_count,
                    'es_plantilla': rutina.tipo == 'plantilla',
                }
                todas_rutinas.append(rutina_dict)
            except Exception as e:
                logger.error(f"Error procesando rutina {rutina.id}: {e}")
                continue
        
        # Calcular estadísticas
        rutinas_activas = Rutina.objects.filter(
            entrenador=request.user,
            status__in=['activa', 'pausada']
        ).exclude(tipo='auto_generada').count()
        
        plantillas_count = Rutina.objects.filter(
            entrenador=request.user,
            tipo='plantilla'
        ).count()
        
        # Contar alumnos con rutinas asignadas
        from django.db.models import Count
        alumnos_con_rutinas = Rutina.objects.filter(
            entrenador=request.user
        ).exclude(tipo='auto_generada').aggregate(
            total_alumnos=Count('alumnos', distinct=True)
        )['total_alumnos'] or 0
        
        recomendaciones_pendientes = 0
        
        logger.info(f"rutinas_plantillas: {len(todas_rutinas)} rutinas para {request.user.username}")
        logger.info(f"rutinas_plantillas: Primera rutina: {todas_rutinas[0] if todas_rutinas else 'NINGUNA'}")
        logger.info(f"rutinas_plantillas: Stats - Activas: {rutinas_activas}, Plantillas: {plantillas_count}")
        
        # Serializar a JSON de forma segura para JavaScript
        rutinas_json_str = json.dumps(todas_rutinas, ensure_ascii=False)
        
        context = {
            'rutinas': todas_rutinas,
            'rutinas_json': rutinas_json_str,
            'stats': {
                'rutinas_activas': rutinas_activas,
                'plantillas': plantillas_count,
                'alumnos_activos': alumnos_con_rutinas,
                'alertas_pendientes': recomendaciones_pendientes,
            }
        }
        
        logger.info(f"rutinas_plantillas: Context tiene {len(context['rutinas'])} rutinas")
        logger.info(f"rutinas_plantillas: JSON length: {len(rutinas_json_str)} caracteres")
        
    except Exception as e:
        logger.error(f"Error en rutinas_plantillas: {e}", exc_info=True)
        context = {
            'rutinas': [],
            'rutinas_json': '[]',
            'stats': {
                'rutinas_activas': 0,
                'plantillas': 0,
                'alumnos_activos': 0,
                'alertas_pendientes': 0,
            },
            'error_message': f'Error: {str(e)}'
        }
    
    return render(request, 'entrenador/rutinas_plantillas.html', context)

# ============ API RUTINAS ============

@login_required
def obtener_rutinas(request):
    """Endpoint para obtener rutinas del entrenador - tabla Rutina NUEVA"""
    try:
        from entrenador.models import Rutina
        
        # Obtener rutinas del usuario actual
        rutinas = Rutina.objects.filter(
            entrenador=request.user
        ).exclude(tipo='auto_generada').order_by('-fecha_actualizacion')
        
        data = []
        for rutina in rutinas:
            rutina_dict = {
                'id': rutina.id,
                'nombre': rutina.nombre or 'Sin nombre',
                'objetivo': rutina.objetivo or 'general',
                'descripcion': rutina.descripcion or '',
                'tipo': rutina.tipo,
                'status': rutina.status,
                'dificultad': rutina.dificultad,
                'duracion_estimada': rutina.duracion_estimada,
                'frecuencia_semanal': rutina.frecuencia_semanal,
                'ejercicios_count': rutina.ejercicios.count() if hasattr(rutina, 'ejercicios') else 0,
                'fecha_creacion': rutina.fecha_creacion.isoformat() if rutina.fecha_creacion else '',
                'fecha_actualizacion': rutina.fecha_actualizacion.isoformat() if rutina.fecha_actualizacion else '',
            }
            data.append(rutina_dict)
        
        response_data = {
            'success': True,
            'rutinas': data,
            'plantillas': [r for r in data if r['tipo'] == 'plantilla'],
            'total': len(data)
        }
        
        logger.info(f"obtener_rutinas: {len(data)} rutinas para {request.user.username}")
        
        response = JsonResponse(response_data)
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        logger.error(f"ERROR obtener_rutinas: {e}", exc_info=True)
        error_response = {
            'success': False,
            'error': str(e),
            'rutinas': [],
            'total': 0
        }
        response = JsonResponse(error_response, status=500)
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response

@csrf_exempt
def crear_rutina(request):
    # Delegar en views_rutinas centralizado que usa admin_gym
    from entrenador.views_rutinas import crear_rutina as crear_core
    return crear_core(request)

def obtener_alumnos(request):
    """API para obtener lista de alumnos/clientes del entrenador
    
    Retorna:
        JSON array de objetos alumno: [{id, nombre, email, telefono, membresia, rutinas_asignadas}, ...]
    """
    if not request.user.is_authenticated:
        logger.warning(f"obtener_alumnos: usuario no autenticado desde {request.META.get('REMOTE_ADDR')}")
        response = JsonResponse([], safe=False, status=200)
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
    
    try:
        logger.info(f"obtener_alumnos: llamada por usuario {request.user.username} desde {request.META.get('REMOTE_ADDR')}")
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.nombre, c.email, c.telefono, c.membresia
                FROM admin_gym_cliente c
                WHERE c.activo = 1
                ORDER BY c.nombre
                LIMIT 50
            """)
            
            clientes = cursor.fetchall()
            logger.info(f"obtener_alumnos: encontrados {len(clientes)} clientes activos en BD")
        
        alumnos = []
        for cliente in clientes:
            cliente_id, nombre, email, telefono, membresia = cliente
            
            # Validar y limpiar datos
            alumnos.append({
                'id': int(cliente_id) if cliente_id else 0,
                'nombre': str(nombre or 'Sin nombre').strip(),
                'email': str(email or 'Sin email').strip(),
                'telefono': str(telefono or 'No registrado').strip(),
                'membresia': str(membresia or 'Sin membresía').strip(),
                'rutinas_asignadas': 0  # TODO: contar rutinas asignadas al alumno
            })
        
        logger.info(f"obtener_alumnos: devolviendo {len(alumnos)} alumnos formateados correctamente")
        response = JsonResponse(alumnos, safe=False, status=200)
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        logger.error(f"obtener_alumnos ERROR: {type(e).__name__}: {str(e)}", exc_info=True)
        # En caso de error, devolver array vacío (cliente puede manejar con mensaje de error)
        response = JsonResponse([], safe=False, status=200)
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response

def obtener_recomendaciones(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse([], safe=False)
    try:
        # Clientes que tienen rutinas creadas por este entrenador
        cliente_ids = AdminGymRutinaCliente.objects.using('default').filter(
            rutina__creado_por=request.user
        ).values_list('cliente_id', flat=True).distinct()
        
        recomendaciones = AdminGymRecomendacionSistema.objects.using('default').filter(
            cliente_id__in=list(cliente_ids)
        ).order_by('-fecha_creacion')[:50]
        
        recomendaciones_data = []
        for rec in recomendaciones:
            recomendaciones_data.append({
                'id': rec.id,
                'tipo': rec.tipo,
                'descripcion': rec.descripcion,
                'recomendacion': rec.recomendacion,
                'estado': rec.estado,
                'fecha_creacion': rec.fecha_creacion.isoformat(),
                'cliente_nombre': rec.cliente.nombre if rec.cliente else 'N/A',
                'cliente_email': rec.cliente.email if rec.cliente else 'N/A',
            })
        return JsonResponse(recomendaciones_data, safe=False)
    except Exception as e:
        logger.error(f"Error obteniendo recomendaciones: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ============ VISTAS BÁSICAS ============

@require_role('entrenador')
def alumnos_list(request):
    try:
        from django.db import connection
        
        # Construir query base con datos reales
        base_query = """
            SELECT c.id, c.nombre, c.email, c.telefono, c.activo, c.fecha_registro, 
                   c.membresia, c.estado_membresia, c.rut, c.fecha_vencimiento, 
                   c.foto_perfil, c.suspendido, c.user_id,
                   COUNT(DISTINCT rc.id) as rutinas_asignadas,
                   MAX(a.fecha) as ultima_asistencia
            FROM admin_gym_cliente c
            LEFT JOIN admin_gym_rutinacliente rc ON c.id = rc.cliente_id AND rc.activa = 1
            LEFT JOIN admin_gym_asistencia a ON c.id = a.cliente_id
            WHERE c.activo = 1
        """
        
        params = []
        
        # Implementar filtros con datos reales
        query = request.GET.get('q', '').strip()
        if query:
            query = re.sub(r'[^\w\s@.-]', '', query)[:100]
            if query:
                base_query += " AND (c.nombre LIKE %s OR c.email LIKE %s OR c.telefono LIKE %s OR c.rut LIKE %s)"
                like_query = f"%{query}%"
                params.extend([like_query, like_query, like_query, like_query])

        estado = request.GET.get('estado', '').strip()
        if estado == 'inactivo':
            base_query = base_query.replace("WHERE c.activo = 1", "WHERE c.activo = 0")
        elif estado == 'suspendido':
            base_query += " AND c.suspendido = 1"

        plan = request.GET.get('plan', '').strip()
        if plan and plan in ['anual', '6m', '3m', 'mensual']:
            base_query += " AND c.membresia = %s"
            params.append(plan)
        
        base_query += " GROUP BY c.id ORDER BY c.nombre"
        
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)
            clientes_raw = cursor.fetchall()
        
        # Procesar datos reales
        alumnos_adaptados = []
        for cliente_data in clientes_raw:
            (
                cliente_id, nombre, email, telefono, activo, fecha_registro,
                membresia, estado_membresia, rut, fecha_vencimiento,
                foto_perfil, suspendido, user_id, rutinas_asignadas, ultima_asistencia
            ) = cliente_data
            
            # Crear objeto user mock con datos reales
            user_mock = type('User', (), {
                'id': user_id if user_id else cliente_id,
                'username': rut,
                'get_full_name': lambda n=nombre: n,
                'email': email
            })()
            
            alumno_data = {
                'id': cliente_id,
                'user': user_mock,
                'plan': membresia,
                'estado': 'activo' if activo else 'inactivo',
                'fecha_inscripcion': fecha_registro,
                'telefono': telefono,
                'foto_perfil': foto_perfil,
                'get_plan_display': membresia.title() if membresia else 'Sin plan',
                'get_estado_display': 'Activo' if activo else 'Inactivo',
                'nombre_completo': nombre,
                'email': email,
                'rut': rut,
                'fecha_vencimiento': fecha_vencimiento,
                'estado_membresia': estado_membresia,
                'suspendido': suspendido,
                'rutinas_asignadas': rutinas_asignadas or 0,
                'ultima_asistencia': ultima_asistencia,
                'dias_sin_asistir': safe_date_diff(timezone.now(), ultima_asistencia)
            }
            alumnos_adaptados.append(alumno_data)

        context = {
            'alumnos': alumnos_adaptados,
            'total_alumnos': len(alumnos_adaptados),
            'query': query or '',
            'estado_filtro': estado,
            'plan_filtro': plan,
        }

    except Exception as e:
        logger.error(f"Error obteniendo alumnos: {e}")
        context = {
            'alumnos': [],
            'total_alumnos': 0,
            'error_message': f'Error conectando con la base de datos: {str(e)}',
            'query': '',
        }

    return render(request, 'entrenador/alumnos_list.html', context)

@require_role('entrenador')
def calendario(request):
    try:
        # Obtener eventos del mes actual
        eventos_recientes = EventoCalendario.objects.filter(
            entrenador=request.user,
            fecha_inicio__gte=timezone.now().date()
        ).order_by('fecha_inicio')[:10]
        
        context = {
            'eventos_recientes': eventos_recientes,
            'total_eventos': EventoCalendario.objects.filter(entrenador=request.user).count(),
        }
        
    except Exception as e:
        logger.error(f"Error en calendario: {e}")
        context = {
            'eventos_recientes': [],
            'total_eventos': 0,
            'error_message': 'Error al cargar el calendario'
        }
    
    return render(request, 'entrenador/calendario.html', context)

@require_role('entrenador')
def perfil(request):
    try:
        # Obtener estadísticas básicas del entrenador
        total_alumnos = AdminGymCliente.objects.using('default').filter(activo=True).count()
        total_rutinas = AdminGymRutina.objects.using('default').filter(creado_por=request.user).count()
        asistencias_mes = AsistenciaEntrenador.objects.filter(entrenador=request.user).count()
        
        context = {
            'user': request.user,
            'estadisticas': {
                'total_alumnos': total_alumnos,
                'total_rutinas': total_rutinas,
                'asistencias_mes': asistencias_mes,
            }
        }
        
    except Exception as e:
        logger.error(f"Error en perfil: {e}")
        context = {
            'user': request.user,
            'estadisticas': {
                'total_alumnos': 0,
                'total_rutinas': 0,
                'asistencias_mes': 0,
            }
        }
    
    return render(request, 'entrenador/perfil.html', context)


@require_role('entrenador')
def actualizar_perfil(request):
    """Actualiza campos básicos del perfil del entrenador via POST (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    try:
        user = request.user
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()

        # Validaciones simples
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return JsonResponse({'success': False, 'message': 'Email inválido'})

        user.first_name = first_name
        user.last_name = last_name
        if email:
            user.email = email
        user.save()

        return JsonResponse({'success': True})
    except Exception as e:
        logger.exception('Error actualizando perfil: %s', e)
        return JsonResponse({'success': False, 'message': 'Error interno al actualizar perfil'})

# Función simplificada - usar la vista de lista con modal
@require_role('entrenador')
def alumno_detalle(request, alumno_id):
    """Vista detallada del alumno con opciones de ver y asignar rutinas"""
    try:
        from alumno.models import PerfilAlumno, RutinaAlumno
        from entrenador.models import Rutina
        
        # Obtener el usuario alumno
        alumno_user = get_object_or_404(User, id=alumno_id)
        
        # Intenta obtener el perfil, si no existe crea uno
        try:
            perfil_alumno = PerfilAlumno.objects.get(user=alumno_user)
        except PerfilAlumno.DoesNotExist:
            logger.warning(f"PerfilAlumno no existe para {alumno_user.username}, creando...")
            perfil_alumno = PerfilAlumno.objects.create(
                user=alumno_user,
                plan='basic',
                estado='activo'
            )
        
        # Obtener rutinas del alumno
        rutinas_alumno = RutinaAlumno.objects.filter(
            alumno=perfil_alumno
        ).prefetch_related('ejercicios').order_by('-fecha_creacion')
        
        # Obtener rutinas disponibles del entrenador (tanto plantillas como personalizadas)
        # Mostrar todas EXCEPTO archivadas y auto-generadas
        # IMPORTANTE: usar Q objects para excluir con lógica OR (exluye archivada O auto_generada)
        rutinas_disponibles = Rutina.objects.filter(
            entrenador=request.user
        ).exclude(
            Q(status='archivada') | Q(tipo='auto_generada')  # Excluir archivadas O auto-generadas
        ).order_by('nombre')
        
        logger.info(f"alumno_detalle: request.user={request.user}, entrenador_id={request.user.id}, rutinas_encontradas={rutinas_disponibles.count()}")
        for r in rutinas_disponibles:
            logger.info(f"  - Rutina: {r.nombre}, tipo={r.tipo}, status={r.status}")
        
        context = {
            'alumno': perfil_alumno,
            'alumno_user': alumno_user,
            'rutinas_alumno': rutinas_alumno,
            'rutinas_disponibles': rutinas_disponibles,
            'total_rutinas': rutinas_alumno.count(),
        }
        
        return render(request, 'entrenador/alumno_detalle.html', context)
        
    except Exception as e:
        logger.error(f"Error en alumno_detalle: {e}", exc_info=True)
        messages.error(request, f'Error: {str(e)}')
        return redirect('alumnos_list')

@require_role('entrenador')
def asistencia(request):
    try:
        # Obtener asistencias del entrenador
        asistencias = AsistenciaEntrenador.objects.filter(
            entrenador=request.user
        ).order_by('-fecha')[:30]
        
        context = {
            'asistencias': asistencias,
            'total_dias': asistencias.count(),
        }
        
    except Exception as e:
        logger.error(f"Error en asistencia: {e}")
        context = {
            'asistencias': [],
            'total_dias': 0,
            'error_message': 'Error al cargar las asistencias'
        }
    
    return render(request, 'entrenador/asistencia.html', context)

@csrf_exempt
@require_role('entrenador')
def marcar_asistencia(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from django.db import connection
        from datetime import datetime, time
        
        hoy = date.today()
        ahora = timezone.now()
        
        with connection.cursor() as cursor:
            # Crear tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entrenador_asistenciaentrenador (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    entrenador_id INT NOT NULL,
                    fecha DATE NOT NULL,
                    hora_entrada TIME NOT NULL,
                    hora_salida TIME NULL,
                    notas TEXT,
                    UNIQUE KEY unique_entrenador_fecha (entrenador_id, fecha),
                    FOREIGN KEY (entrenador_id) REFERENCES auth_user(id)
                )
            """)
            
            # Verificar si ya marcó asistencia hoy
            cursor.execute("""
                SELECT id, hora_entrada, hora_salida FROM entrenador_asistenciaentrenador
                WHERE entrenador_id = %s AND fecha = %s
            """, [request.user.id, hoy])
            
            asistencia_existente = cursor.fetchone()
            
            if asistencia_existente:
                asistencia_id, hora_entrada, hora_salida = asistencia_existente
                
                if not hora_salida:
                    # Marcar salida
                    cursor.execute("""
                        UPDATE entrenador_asistenciaentrenador 
                        SET hora_salida = %s 
                        WHERE id = %s
                    """, [ahora.time(), asistencia_id])
                    
                    return JsonResponse({
                        'success': True, 
                        'message': 'Salida marcada',
                        'hora': ahora.strftime('%H:%M')
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Ya marcaste entrada y salida hoy'
                    })
            else:
                # Marcar entrada DIRECTAMENTE en tabla entrenador
                cursor.execute("""
                    INSERT INTO entrenador_asistenciaentrenador 
                    (entrenador_id, fecha, hora_entrada) 
                    VALUES (%s, %s, %s)
                """, [request.user.id, hoy, ahora.time()])
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Entrada marcada',
                    'hora': ahora.strftime('%H:%M'),
                    'actualizar_metricas': True
                })
            
    except Exception as e:
        logger.error(f"Error marcando asistencia: {e}")
        return JsonResponse({
            'success': False, 
            'message': f'Error: {str(e)}'
        })

@require_role('entrenador')
def contador_series_alumno(request, alumno_id):
    try:
        cliente = AdminGymCliente.objects.using('default').get(id=alumno_id)
        
        # Obtener rutinas activas del alumno
        rutinas_activas = AdminGymRutinaCliente.objects.using('default').filter(
            cliente=cliente, activa=True
        ).select_related('rutina')
        
        context = {
            'alumno': cliente,
            'rutinas_activas': rutinas_activas,
        }
        
    except AdminGymCliente.DoesNotExist:
        messages.error(request, 'Alumno no encontrado')
        return redirect('alumnos_list')
    except Exception as e:
        logger.error(f"Error en contador_series_alumno: {e}")
        context = {
            'alumno': None,
            'rutinas_activas': [],
            'error_message': 'Error al cargar los datos'
        }
    
    return render(request, 'entrenador/contador_series.html', context)

@require_role('entrenador')
def alumnos_personalizados(request):
    try:
        # Obtener alumnos que tienen rutinas asignadas por este entrenador
        clientes_con_rutinas = AdminGymCliente.objects.using('default').filter(
            admingymrutinacliente__asignado_por=request.user,
            admingymrutinacliente__activa=True,
            activo=True
        ).distinct().order_by('nombre')
        
        alumnos_data = []
        for cliente in clientes_con_rutinas:
            rutinas_activas = AdminGymRutinaCliente.objects.using('default').filter(
                cliente=cliente,
                asignado_por=request.user,
                activa=True
            ).count()
            
            alumnos_data.append({
                'cliente': cliente,
                'rutinas_activas': rutinas_activas,
                'user_id': cliente.user_id if cliente.user_id else cliente.id,
            })
        
        context = {
            'alumnos_personalizados': alumnos_data,
            'total_alumnos': len(alumnos_data),
        }
        
    except Exception as e:
        logger.error(f"Error en alumnos_personalizados: {e}")
        context = {
            'alumnos_personalizados': [],
            'total_alumnos': 0,
            'error_message': 'Error al cargar los alumnos personalizados'
        }
    
    return render(request, 'entrenador/alumnos_personalizados.html', context)

def eventos_calendario(request):
    """API para obtener eventos del calendario"""
    try:
        # Obtener eventos del calendario del entrenador actual
        eventos_db = EventoCalendario.objects.filter(
            entrenador=request.user
        ).order_by('fecha_inicio')
        
        eventos = []
        for evento in eventos_db:
            eventos.append({
                'id': evento.id,
                'title': evento.titulo,
                'start': evento.fecha_inicio.isoformat(),
                'end': evento.fecha_fin.isoformat(),
                'type': evento.tipo,
                'description': evento.descripcion,
                'color': evento.color,
                'completado': evento.completado,
                'alumno': evento.alumno.get_full_name() if evento.alumno else None
            })
        
        # También incluir sesiones públicas si existen
        try:
            from .models import ClaseSesion
            sesiones = ClaseSesion.objects.filter(publico=True, cancelada=False)
            
            for s in sesiones:
                eventos.append({
                    'id': f'sesion_{s.id}',
                    'title': s.titulo,
                    'start': s.inicio.isoformat(),
                    'end': s.fin.isoformat(),
                    'type': 'sesion',
                    'description': s.descripcion,
                    'capacidad': s.capacidad,
                    'inscritos': s.inscritos_count,
                    'disponible': s.disponible,
                    'ubicacion': s.ubicacion,
                    'color': '#28a745'
                })
        except Exception:
            pass  # Si no existe el modelo ClaseSesion, continuar
        
        return JsonResponse(eventos, safe=False)
        
    except Exception as e:
        logger.error(f"Error obteniendo eventos calendario: {e}")
        return JsonResponse([], safe=False)

@csrf_exempt
def crear_evento(request):
    """API para crear eventos en el calendario"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Usuario no autenticado'})

    try:
        data = json.loads(request.body.decode('utf-8'))
        titulo = data.get('titulo')
        descripcion = data.get('descripcion', '')
        inicio = data.get('fecha_inicio')
        fin = data.get('fecha_fin')
        tipo = data.get('tipo', 'sesion')
        color = data.get('color', '#007bff')

        if not titulo or not inicio or not fin:
            return JsonResponse({'success': False, 'message': 'Faltan datos requeridos: título, fecha inicio y fecha fin'})

        # Parsear fechas
        try:
            if inicio.endswith('Z'):
                inicio = inicio[:-1]
            if fin.endswith('Z'):
                fin = fin[:-1]
                
            inicio_dt = timezone.datetime.fromisoformat(inicio)
            fin_dt = timezone.datetime.fromisoformat(fin)
            
            # Asegurar que las fechas tengan timezone
            if timezone.is_naive(inicio_dt):
                inicio_dt = timezone.make_aware(inicio_dt)
            if timezone.is_naive(fin_dt):
                fin_dt = timezone.make_aware(fin_dt)
                
        except ValueError as e:
            return JsonResponse({'success': False, 'message': f'Error en formato de fecha: {str(e)}'})

        # Crear evento en el calendario
        evento = EventoCalendario.objects.create(
            entrenador=request.user,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo,
            fecha_inicio=inicio_dt,
            fecha_fin=fin_dt,
            color=color
        )

        return JsonResponse({
            'success': True, 
            'id': evento.id,
            'message': 'Evento creado exitosamente'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Error en formato JSON'})
    except Exception as e:
        logger.error(f"Error creando evento: {e}")
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})

@csrf_exempt
def editar_evento(request, evento_id):
    """API para editar eventos del calendario"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Usuario no autenticado'})

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Buscar el evento del entrenador actual
        evento = EventoCalendario.objects.get(
            id=evento_id, 
            entrenador=request.user
        )

        # Actualizar campos
        evento.titulo = data.get('titulo', evento.titulo)
        evento.descripcion = data.get('descripcion', evento.descripcion)
        evento.tipo = data.get('tipo', evento.tipo)
        evento.color = data.get('color', evento.color)
        
        # Actualizar fechas si se proporcionan
        if data.get('fecha_inicio'):
            inicio = data.get('fecha_inicio')
            if inicio.endswith('Z'):
                inicio = inicio[:-1]
            inicio_dt = timezone.datetime.fromisoformat(inicio)
            if timezone.is_naive(inicio_dt):
                inicio_dt = timezone.make_aware(inicio_dt)
            evento.fecha_inicio = inicio_dt
            
        if data.get('fecha_fin'):
            fin = data.get('fecha_fin')
            if fin.endswith('Z'):
                fin = fin[:-1]
            fin_dt = timezone.datetime.fromisoformat(fin)
            if timezone.is_naive(fin_dt):
                fin_dt = timezone.make_aware(fin_dt)
            evento.fecha_fin = fin_dt
        
        evento.save()

        return JsonResponse({
            'success': True,
            'message': 'Evento actualizado exitosamente'
        })
        
    except EventoCalendario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Evento no encontrado'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Error en formato JSON'})
    except Exception as e:
        logger.error(f"Error editando evento: {e}")
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})

@csrf_exempt
def eliminar_evento(request, evento_id):
    """API para eliminar eventos del calendario"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Usuario no autenticado'})

    try:
        # Buscar el evento del entrenador actual
        evento = EventoCalendario.objects.get(
            id=evento_id, 
            entrenador=request.user
        )
        
        # Eliminar el evento
        evento.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Evento eliminado exitosamente'
        })
        
    except EventoCalendario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Evento no encontrado'})
    except Exception as e:
        logger.error(f"Error eliminando evento: {e}")
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})


@csrf_exempt
@login_required
def inscribir_sesion(request, sesion_id):
    """Inscribir al usuario autenticado en la sesión indicada."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})

    try:
        from .models import ClaseSesion, InscripcionSesion
        sesion = ClaseSesion.objects.get(id=sesion_id)

        # Si no disponible
        if not sesion.disponible:
            return JsonResponse({'success': False, 'message': 'Sesión no disponible o completa'})

        # Crear o actualizar inscripción
        obj, created = InscripcionSesion.objects.update_or_create(
            sesion=sesion,
            alumno=request.user,
            defaults={'status': 'inscrito'}
        )

        return JsonResponse({'success': True, 'inscrito': True, 'created': created})
    except ClaseSesion.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sesión no encontrada'})
    except Exception as e:
        logger.error(f"Error inscribiendo a sesión: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


@csrf_exempt
@login_required
def rechazar_sesion(request, sesion_id):
    """Marcar la sesión como rechazada por el alumno (si existe inscripción la actualiza)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})

    try:
        from .models import ClaseSesion, InscripcionSesion
        sesion = ClaseSesion.objects.get(id=sesion_id)

        obj, created = InscripcionSesion.objects.update_or_create(
            sesion=sesion,
            alumno=request.user,
            defaults={'status': 'rechazado'}
        )

        return JsonResponse({'success': True, 'rechazado': True, 'created': created})
    except ClaseSesion.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sesión no encontrada'})
    except Exception as e:
        logger.error(f"Error rechazando sesión: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
@login_required
@require_role('entrenador')
def asignar_rutina(request):
    """Endpoint para asignar rutina desde entrenador.models.Rutina"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from entrenador.models import Rutina, RutinaAlumnos
        from django.contrib.auth.models import User
        
        alumno_id = request.POST.get('alumno_id')
        rutina_id = request.POST.get('plantilla')  # Viene como 'plantilla' desde el form
        notas = request.POST.get('notas', '')
        
        if not alumno_id or not rutina_id:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan datos: seleccione alumno y rutina'
            })
        
        # Obtener el usuario alumno y la rutina del entrenador
        try:
            alumno = User.objects.get(id=alumno_id)
            rutina = Rutina.objects.get(
                id=rutina_id,
                entrenador=request.user  # Validar que la rutina sea del entrenador
            )
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Alumno no encontrado'
            })
        except Rutina.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Rutina no encontrada o no tienes permisos'
            })
        
        # Verificar si ya está asignada
        if RutinaAlumnos.objects.filter(rutina=rutina, user=alumno).exists():
            return JsonResponse({
                'success': False,
                'message': 'Esta rutina ya está asignada a este alumno'
            })
        
        # Crear la asignación usando el modelo intermedio
        asignacion = RutinaAlumnos.objects.create(
            rutina=rutina,
            user=alumno
        )
        
        # Actualizar notas del entrenador si se proporcionaron
        if notas:
            rutina.notas_entrenador = notas
            rutina.save(update_fields=['notas_entrenador'])
        
        logger.info(f"Rutina '{rutina.nombre}' asignada a {alumno.username} por {request.user.username}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Rutina "{rutina.nombre}" asignada exitosamente',
            'rutina': {
                'id': rutina.id,
                'nombre': rutina.nombre,
                'objetivo': rutina.objetivo,
                'tipo': rutina.tipo,
                'status': rutina.status,
                'fecha_asignacion': timezone.now().strftime('%d/%m/%Y'),
                'ejercicios_count': rutina.ejercicios.count() if hasattr(rutina, 'ejercicios') else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error asignando rutina: {e}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'message': f'Error interno: {str(e)}'
        })


@csrf_exempt
def editar_rutina(request, rutina_id):
    from entrenador.views_rutinas import editar_rutina as editar_core
    return editar_core(request, rutina_id)

@csrf_exempt
def eliminar_rutina(request, rutina_id):
    from entrenador.views_rutinas import eliminar_rutina as eliminar_core
    return eliminar_core(request, rutina_id)

def exportar_rutinas_csv(request):
    from entrenador.views_rutinas import exportar_rutinas_csv as export_core
    return export_core(request)

def custom_logout(request):
    return redirect('login')

@login_required
def obtener_rutinas_alumno(request, alumno_id):
    """Obtener rutinas asignadas a un alumno específico"""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT rc.id, r.nombre, r.objetivo, rc.fecha_asignacion, 
                       rc.fecha_inicio, rc.activa, rc.notas,
                       u.username as asignado_por
                FROM admin_gym_rutinacliente rc
                JOIN admin_gym_rutina r ON rc.rutina_id = r.id
                LEFT JOIN auth_user u ON rc.asignado_por_id = u.id
                WHERE rc.cliente_id = %s
                ORDER BY rc.fecha_asignacion DESC
            """, [alumno_id])
            
            rutinas_data = cursor.fetchall()
        
        rutinas = []
        for rutina in rutinas_data:
            rutinas.append({
                'id': rutina[0],
                'nombre': rutina[1],
                'objetivo': rutina[2],
                'fecha_asignacion': rutina[3].isoformat() if rutina[3] else '',
                'fecha_inicio': rutina[4].isoformat() if rutina[4] else '',
                'activa': bool(rutina[5]),
                'notas': rutina[6] or '',
                'asignado_por': rutina[7] or 'Sistema'
            })
        
        return JsonResponse({
            'success': True,
            'rutinas': rutinas,
            'total': len(rutinas)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo rutinas del alumno: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def obtener_metricas_dashboard(request):
    """Endpoint para obtener métricas actualizadas del dashboard"""
    try:
        from django.db import connection
        hoy = timezone.now().date()
        
        with connection.cursor() as cursor:
            # Alumnos activos
            cursor.execute("SELECT COUNT(*) FROM admin_gym_cliente WHERE activo = 1")
            alumnos_activos = cursor.fetchone()[0]
            
            # Rutinas del entrenador
            cursor.execute("SELECT COUNT(*) FROM admin_gym_rutina WHERE creado_por_id = %s", [request.user.id])
            rutinas_creadas = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_rutinacliente 
                WHERE asignado_por_id = %s AND activa = 1
            """, [request.user.id])
            rutinas_activas = cursor.fetchone()[0]
            
            # FUENTE DIRECTA: Tabla entrenador_asistenciaentrenador
            primer_dia_mes = hoy.replace(day=1)
            
            cursor.execute("""
                SELECT COUNT(*) FROM entrenador_asistenciaentrenador 
                WHERE entrenador_id = %s AND fecha >= %s AND fecha <= %s
            """, [request.user.id, primer_dia_mes, hoy])
            
            mis_asistencias = cursor.fetchone()[0]
            
            # Asistencias del mes (todos los clientes)
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_asistencia 
                WHERE fecha >= %s AND fecha <= %s
            """, [primer_dia_mes, hoy])
            asistencias_mes = cursor.fetchone()[0]
            
            # Nuevos alumnos esta semana
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_cliente 
                WHERE activo = 1 AND DATE(fecha_registro) >= %s
            """, [inicio_semana])
            nuevos_esta_semana = cursor.fetchone()[0]
            
            # DATOS DEL GRÁFICO: Misma fuente que el contador
            asistencia_semanas = []
            
            for i in range(4):
                dias_atras = (i * 7) + hoy.weekday()
                inicio_semana_grafico = hoy - timedelta(days=dias_atras)
                fin_semana_grafico = inicio_semana_grafico + timedelta(days=6)
                
                if fin_semana_grafico > hoy:
                    fin_semana_grafico = hoy
                
                cursor.execute("""
                    SELECT COUNT(*) FROM entrenador_asistenciaentrenador 
                    WHERE entrenador_id = %s AND fecha >= %s AND fecha <= %s
                """, [request.user.id, inicio_semana_grafico, fin_semana_grafico])
                
                asistencias_semana = cursor.fetchone()[0]
                asistencia_semanas.insert(0, asistencias_semana)
        
        return JsonResponse({
            'success': True,
            'metricas': {
                'alumnos_activos': alumnos_activos,
                'nuevos_esta_semana': nuevos_esta_semana,
                'rutinas_creadas': rutinas_creadas,
                'rutinas_activas': rutinas_activas,
                'mis_asistencias': mis_asistencias,
                'asistencias_mes': asistencias_mes,
                'asistencia_semanas': asistencia_semanas,
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def obtener_progreso_alumno(request, alumno_id):
    """API para obtener el progreso completo de un alumno con datos reales"""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Obtener datos del alumno con asistencias reales
            cursor.execute("""
                SELECT c.id, c.nombre, c.email, c.telefono, c.fecha_registro, c.membresia,
                       COUNT(DISTINCT rc.id) as rutinas_activas,
                       COUNT(DISTINCT a.id) as total_asistencias,
                       MAX(a.fecha) as ultima_asistencia,
                       DATEDIFF(CURDATE(), c.fecha_registro) as dias_como_cliente
                FROM admin_gym_cliente c
                LEFT JOIN admin_gym_rutinacliente rc ON c.id = rc.cliente_id AND rc.activa = 1
                LEFT JOIN admin_gym_asistencia a ON c.id = a.cliente_id
                WHERE c.id = %s
                GROUP BY c.id
            """, [alumno_id])
            
            alumno_data = cursor.fetchone()
            
            if not alumno_data:
                return JsonResponse({'success': False, 'error': 'Alumno no encontrado'})
            
            # Obtener rutinas del alumno
            cursor.execute("""
                SELECT rc.id, r.nombre, r.objetivo, rc.fecha_asignacion, 
                       rc.activa, u.username as asignado_por, 
                       COALESCE(rc.notas, '') as notas,
                       COUNT(DISTINCT er.id) as total_ejercicios
                FROM admin_gym_rutinacliente rc
                JOIN admin_gym_rutina r ON rc.rutina_id = r.id
                LEFT JOIN auth_user u ON rc.asignado_por_id = u.id
                LEFT JOIN admin_gym_ejerciciorutina er ON r.id = er.rutina_id
                WHERE rc.cliente_id = %s
                GROUP BY rc.id
                ORDER BY rc.fecha_asignacion DESC
            """, [alumno_id])
            
            rutinas_data = cursor.fetchall()
            
            # Obtener asistencias recientes (últimas 10)
            cursor.execute("""
                SELECT DATE(fecha) as fecha_asistencia, TIME(fecha) as hora_asistencia
                FROM admin_gym_asistencia
                WHERE cliente_id = %s
                ORDER BY fecha DESC
                LIMIT 10
            """, [alumno_id])
            
            asistencias_recientes = cursor.fetchall()
            
            # Obtener estadísticas de asistencia por mes (últimos 6 meses)
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(fecha, '%%Y-%%m') as mes,
                    COUNT(*) as total_asistencias
                FROM admin_gym_asistencia
                WHERE cliente_id = %s 
                    AND fecha >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(fecha, '%%Y-%%m')
                ORDER BY mes DESC
            """, [alumno_id])
            
            estadisticas_mensuales = cursor.fetchall()
        
        # Estructurar respuesta
        progreso = {
            'nombre': alumno_data[1],
            'email': alumno_data[2],
            'telefono': alumno_data[3],
            'fecha_registro': alumno_data[4].strftime('%d/%m/%Y') if alumno_data[4] else '',
            'membresia': alumno_data[5] or 'Sin membresía',
            'rutinas_activas': alumno_data[6],
            'total_asistencias': alumno_data[7],
            'ultima_asistencia': alumno_data[8].strftime('%d/%m/%Y') if alumno_data[8] else 'Nunca',
            'dias_como_cliente': alumno_data[9] or 0,
            'rutinas': [],
            'asistencias_recientes': [],
            'estadisticas_mensuales': []
        }
        
        # Procesar rutinas
        for rutina in rutinas_data:
            progreso['rutinas'].append({
                'id': rutina[0],
                'nombre': rutina[1],
                'objetivo': rutina[2],
                'fecha_asignacion': rutina[3].strftime('%d/%m/%Y') if rutina[3] else '',
                'activa': bool(rutina[4]),
                'asignado_por': rutina[5] or 'Sistema',
                'notas': rutina[6] or 'Sin notas',
                'total_ejercicios': rutina[7] or 0
            })
        
        # Procesar asistencias recientes
        for asistencia in asistencias_recientes:
            progreso['asistencias_recientes'].append({
                'fecha': asistencia[0].strftime('%d/%m/%Y') if asistencia[0] else '',
                'hora': str(asistencia[1]) if asistencia[1] else ''
            })
        
        # Procesar estadísticas mensuales
        for stat in estadisticas_mensuales:
            progreso['estadisticas_mensuales'].append({
                'mes': stat[0],
                'total': stat[1]
            })
        
        return JsonResponse({
            'success': True,
            'progreso': progreso
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo progreso del alumno: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def obtener_detalle_rutina(request, rutina_id):
    """Endpoint para obtener detalles completos de una rutina"""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Verificar si la columna notas existe
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'admin_gym_rutinacliente' AND column_name = 'notas'
            """)
            
            notas_exists = cursor.fetchone()[0] > 0
            
            # Obtener datos de la rutina con o sin notas
            if notas_exists:
                cursor.execute("""
                    SELECT r.id, r.nombre, r.descripcion, r.objetivo, r.fecha_creacion, r.activa,
                           rc.fecha_asignacion, rc.fecha_inicio, rc.notas
                    FROM admin_gym_rutina r
                    LEFT JOIN admin_gym_rutinacliente rc ON r.id = rc.rutina_id
                    WHERE r.id = %s
                    LIMIT 1
                """, [rutina_id])
            else:
                cursor.execute("""
                    SELECT r.id, r.nombre, r.descripcion, r.objetivo, r.fecha_creacion, r.activa,
                           rc.fecha_asignacion, rc.fecha_inicio, '' as notas
                    FROM admin_gym_rutina r
                    LEFT JOIN admin_gym_rutinacliente rc ON r.id = rc.rutina_id
                    WHERE r.id = %s
                    LIMIT 1
                """, [rutina_id])
            
            rutina_data = cursor.fetchone()
            
            if not rutina_data:
                return JsonResponse({'success': False, 'error': 'Rutina no encontrada'})
            
            # Obtener ejercicios de la rutina
            cursor.execute("""
                SELECT e.nombre, er.series, er.repeticiones, er.peso_sugerido, 
                       er.tiempo_descanso, er.notas, er.orden
                FROM admin_gym_ejerciciorutina er
                JOIN admin_gym_ejercicio e ON er.ejercicio_id = e.id
                WHERE er.rutina_id = %s
                ORDER BY er.orden
            """, [rutina_id])
            
            ejercicios_data = cursor.fetchall()
            
            # Estructurar respuesta
            rutina_info = {
                'id': rutina_data[0],
                'nombre': rutina_data[1],
                'descripcion': rutina_data[2] or 'Sin descripción',
                'objetivo': rutina_data[3],
                'fecha_creacion': rutina_data[4].strftime('%d/%m/%Y') if rutina_data[4] else '',
                'activa': bool(rutina_data[5]),
                'fecha_asignacion': rutina_data[6].strftime('%d/%m/%Y') if rutina_data[6] else '',
                'fecha_inicio': rutina_data[7].strftime('%d/%m/%Y') if rutina_data[7] else '',
                'notas': rutina_data[8] or 'Sin notas',
                'ejercicios': []
            }
            
            for ejercicio in ejercicios_data:
                rutina_info['ejercicios'].append({
                    'nombre': ejercicio[0],
                    'series': ejercicio[1],
                    'repeticiones': ejercicio[2],
                    'peso_sugerido': str(ejercicio[3]) if ejercicio[3] else 'Sin peso',
                    'descanso': ejercicio[4] or 60,
                    'notas': ejercicio[5] or '',
                    'orden': ejercicio[6]
                })
            
            return JsonResponse({
                'success': True,
                'rutina': rutina_info
            })
            
    except Exception as e:
        logger.error(f"Error obteniendo detalle de rutina: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def debug_rutinas(request):
    """Endpoint de debug para verificar rutinas en la base de datos"""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Verificar tabla existe
            cursor.execute("SHOW TABLES LIKE 'admin_gym_rutina'")
            tabla_existe = cursor.fetchone() is not None
            
            if not tabla_existe:
                return JsonResponse({
                    'error': 'Tabla admin_gym_rutina no existe',
                    'tabla_existe': False
                })
            
            # Contar rutinas
            cursor.execute("SELECT COUNT(*) FROM admin_gym_rutina")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM admin_gym_rutina WHERE activa = 1")
            activas = cursor.fetchone()[0]
            
            # Obtener algunas rutinas de ejemplo
            cursor.execute("""
                SELECT id, nombre, objetivo, activa, es_plantilla, fecha_creacion
                FROM admin_gym_rutina 
                ORDER BY id DESC 
                LIMIT 10
            """)
            
            ejemplos = []
            for row in cursor.fetchall():
                ejemplos.append({
                    'id': row[0],
                    'nombre': row[1],
                    'objetivo': row[2],
                    'activa': bool(row[3]),
                    'es_plantilla': bool(row[4]),
                    'fecha_creacion': row[5].isoformat() if row[5] else None
                })
            
            return JsonResponse({
                'tabla_existe': True,
                'total_rutinas': total,
                'rutinas_activas': activas,
                'ejemplos': ejemplos,
                'usuario_actual': request.user.username,
                'es_staff': request.user.is_staff
            })
            
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'tabla_existe': False
        })

def test_alumnos_page(request):
    """Página de prueba simple para debuggear la carga de alumnos"""
    return render(request, 'entrenador/test_alumnos.html')

@require_role('entrenador')
@require_POST
def api_eliminar_rutina_alumno(request, rutina_id):
    """API para eliminar una rutina de un alumno"""
    try:
        from alumno.models import RutinaAlumno
        
        rutina = get_object_or_404(RutinaAlumno, id=rutina_id)
        
        # Verificar que el entrenador que asignó es quien la elimina
        if rutina.asignada_por and rutina.asignada_por != request.user:
            # Permitir que el trainer lo haga igualmente si es admin
            if not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'message': 'No tienes permiso para eliminar esta rutina'
                })
        
        alumno_nombre = rutina.alumno.user.get_full_name()
        rutina_nombre = rutina.nombre
        rutina.delete()
        
        logger.info(f"Rutina '{rutina_nombre}' eliminada de {alumno_nombre} por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Rutina "{rutina_nombre}" eliminada correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error eliminando rutina: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@require_role('entrenador')
def editar_rutina_alumno(request, alumno_id, rutina_id):
    """Vista para editar una rutina asignada a un alumno"""
    try:
        from alumno.models import RutinaAlumno, EjercicioRutinaAlumno
        
        # Obtener la rutina del alumno
        rutina = get_object_or_404(RutinaAlumno, id=rutina_id, alumno__user_id=alumno_id)
        
        # Verificar permiso: solo el entrenador que la asignó o staff
        if rutina.asignada_por != request.user and not request.user.is_staff:
            messages.error(request, 'No tienes permiso para editar esta rutina')
            return redirect('alumno_detalle', alumno_id=alumno_id)
        
        if request.method == 'POST':
            # Actualizar datos de la rutina
            rutina.nombre = request.POST.get('nombre', rutina.nombre)
            rutina.objetivo = request.POST.get('objetivo', rutina.objetivo)
            rutina.descripcion = request.POST.get('descripcion', rutina.descripcion)
            rutina.dia_asignado = request.POST.get('dia_asignado', rutina.dia_asignado)
            rutina.save()
            
            messages.success(request, 'Rutina actualizada correctamente')
            return redirect('alumno_detalle', alumno_id=alumno_id)
        
        # GET request
        ejercicios = rutina.ejercicios.all().order_by('orden')
        
        context = {
            'rutina': rutina,
            'ejercicios': ejercicios,
            'alumno': rutina.alumno,
        }
        
        return render(request, 'entrenador/editar_rutina_alumno.html', context)
        
    except Exception as e:
        logger.error(f"Error editando rutina: {e}", exc_info=True)
        messages.error(request, f'Error: {str(e)}')
        return redirect('alumno_detalle', alumno_id=alumno_id)

@require_role('entrenador')
@require_POST
def api_asignar_rutina_alumno(request, alumno_id):
    """API para asignar una rutina a un alumno"""
    try:
        from alumno.models import PerfilAlumno, RutinaAlumno, EjercicioRutinaAlumno
        from entrenador.models import Rutina, DetalleEjercicio
        from django.contrib.auth.models import User
        
        alumno_user = get_object_or_404(User, id=alumno_id)
        perfil_alumno = get_object_or_404(PerfilAlumno, user=alumno_user)
        
        # Obtener datos del formulario
        plantilla_id = request.POST.get('plantilla')
        dia_asignado = request.POST.get('dia_asignado', '')
        notas = request.POST.get('notas', '')
        
        if not plantilla_id:
            return JsonResponse({'success': False, 'message': 'Plantilla requerida'})
        
        # Obtener la plantilla - primero sin filtrar por entrenador
        try:
            plantilla = Rutina.objects.get(id=plantilla_id)
        except Rutina.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Plantilla con ID {plantilla_id} no encontrada'})
        
        # Verificar que pertenece al entrenador actual
        if plantilla.entrenador != request.user:
            logger.warning(f"Intento de asignar rutina de otro entrenador: usuario={request.user.id}, rutina_entrenador={plantilla.entrenador.id}")
            return JsonResponse({'success': False, 'message': 'No tienes permiso para asignar esta plantilla'})
        
        # Crear la rutina del alumno
        rutina_alumno = RutinaAlumno.objects.create(
            alumno=perfil_alumno,
            nombre=plantilla.nombre,
            objetivo=plantilla.objetivo,
            tipo='asignada',
            dia_asignado=dia_asignado if dia_asignado else None,
            rutina_entrenador=plantilla,
            asignada_por=request.user,
            fecha_asignacion=timezone.now(),
            descripcion=notas,
            activa=True
        )
        
        # Copiar ejercicios de la plantilla
        detalles = DetalleEjercicio.objects.filter(rutina=plantilla).order_by('orden')
        logger.info(f"Copiando {detalles.count()} ejercicios de plantilla {plantilla.nombre}")
        
        for detalle in detalles:
            try:
                EjercicioRutinaAlumno.objects.create(
                    rutina=rutina_alumno,
                    nombre=detalle.ejercicio.nombre,
                    series=detalle.series,
                    repeticiones=str(detalle.repeticiones),
                    peso=detalle.peso if hasattr(detalle, 'peso') else '',
                    descanso=detalle.descanso if hasattr(detalle, 'descanso') else '60s',
                    notas=detalle.notas if hasattr(detalle, 'notas') else '',
                    orden=detalle.orden
                )
            except Exception as e:
                logger.error(f"Error al copiar ejercicio {detalle.ejercicio.nombre}: {e}")
                continue
        
        # Crear mensaje motivacional
        crear_mensaje_si_no_duplicado(
            alumno=perfil_alumno,
            tipo='motivacion',
            titulo='Nueva Rutina Asignada',
            contenido=f'Tu entrenador te ha asignado la rutina: {plantilla.nombre}. ¡Comienza hoy mismo!',
            prioridad=3
        )
        
        # SINCRONIZAR CON TABLA ANTIGUA (para compatibilidad con app antigua del alumno)
        try:
            from entrenador_app.admin_gym_models import (
                AdminGymRutinaCliente, AdminGymCliente, AdminGymRutina,
                AdminGymEjercicio, AdminGymEjercicioRutina
            )
            
            # Obtener o crear cliente en tabla antigua
            cliente_antiguo = AdminGymCliente.objects.filter(user=alumno_user).first()
            if cliente_antiguo:
                # Obtener o crear rutina en tabla antigua
                rutina_antigua, created = AdminGymRutina.objects.get_or_create(
                    nombre=plantilla.nombre,
                    defaults={
                        'descripcion': plantilla.descripcion or '',
                        'objetivo': plantilla.objetivo or 'hipertrofia',
                        'activa': True,
                        'creado_por': request.user,
                        'es_plantilla': False,
                        'fecha_creacion': timezone.now(),
                    }
                )
                
                if created:
                    logger.info(f"Creada rutina en admin_gym_rutina: ID {rutina_antigua.id}")
                
                # Copiar ejercicios a la tabla antigua
                # Primero eliminar ejercicios existentes para evitar duplicados
                AdminGymEjercicioRutina.objects.filter(rutina=rutina_antigua).delete()
                
                for detalle in detalles:
                    # Obtener o crear ejercicio en tabla antigua
                    ejercicio_antiguo, _ = AdminGymEjercicio.objects.get_or_create(
                        nombre=detalle.ejercicio.nombre,
                        defaults={
                            'descripcion': detalle.ejercicio.descripcion if hasattr(detalle.ejercicio, 'descripcion') else '',
                            'tipo': detalle.tipo if hasattr(detalle, 'tipo') else 'fuerza',
                            'grupo_muscular': detalle.ejercicio.grupo_muscular if hasattr(detalle.ejercicio, 'grupo_muscular') else 'general',
                            'instrucciones': '',
                            'activo': True,
                        }
                    )
                    
                    # Parsear descanso (ej: "60-90s" -> 60)
                    descanso_str = detalle.descanso if hasattr(detalle, 'descanso') else '60s'
                    try:
                        # Extraer primer número de strings como "60-90s" o "60s"
                        import re
                        match = re.search(r'(\d+)', descanso_str)
                        tiempo_descanso = int(match.group(1)) if match else 60
                    except:
                        tiempo_descanso = 60
                    
                    # Parsear peso (ej: "20kg" -> 20.0)
                    peso_str = detalle.peso_inicial if hasattr(detalle, 'peso_inicial') else ''
                    try:
                        import re
                        match = re.search(r'(\d+\.?\d*)', peso_str)
                        peso_sugerido = float(match.group(1)) if match else 0.0
                    except:
                        peso_sugerido = 0.0
                    
                    # Crear ejercicio en rutina
                    AdminGymEjercicioRutina.objects.create(
                        rutina=rutina_antigua,
                        ejercicio=ejercicio_antiguo,
                        series=detalle.series,
                        repeticiones=detalle.repeticiones,
                        peso_sugerido=peso_sugerido,
                        tiempo_descanso=tiempo_descanso,
                        notas=detalle.notas if hasattr(detalle, 'notas') else '',
                        orden=detalle.orden
                    )
                
                logger.info(f"Copiados {detalles.count()} ejercicios a admin_gym_ejerciciorutina")
                
                # Crear asignación en tabla antigua si no existe
                if not AdminGymRutinaCliente.objects.filter(rutina=rutina_antigua, cliente=cliente_antiguo).exists():
                    AdminGymRutinaCliente.objects.create(
                        rutina=rutina_antigua,
                        cliente=cliente_antiguo,
                        asignado_por=request.user,
                        activa=True,
                        fecha_asignacion=timezone.now(),
                        fecha_inicio=timezone.now().date(),
                    )
                    logger.info(f"Sincronizada rutina a tabla antigua para {alumno_user.username}")
        except Exception as e:
            logger.warning(f"No se pudo sincronizar a tabla antigua: {e}", exc_info=True)
        
        logger.info(f"Rutina '{plantilla.nombre}' asignada a {alumno_user.username} por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina asignada correctamente',
            'rutina_id': rutina_alumno.id
        })
        
    except Exception as e:
        logger.error(f"Error asignando rutina: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })