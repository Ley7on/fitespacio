from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.http import JsonResponse, HttpResponse
from django.utils.html import escape
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.urls import reverse
import json
import logging
import csv
import io
from datetime import timedelta, datetime
from entrenador_app.auth_views import require_role
from entrenador_app.heuristics import process_heuristic_messages

from .models import InformacionAlumno, PerfilAlumno, AccesoGimnasio, ProgresoFisico, NotificacionMotivacional, HabitoBueno, RegistroHabitoBueno, HabitoMalo, RegistroHabitoMalo, MensajeMotivacional, Ejercicio, RegistroEjercicio, Meta, AccionMeta, ProgresoMeta, RutinaAlumno, EjercicioRutinaAlumno
from .heuristics import MotorRecomendaciones
from .validators import validate_payload

logger = logging.getLogger(__name__)


def crear_mensaje_si_no_duplicado(alumno, tipo, titulo, contenido, prioridad=2, ventana_horas=24):
    """Crea un MensajeMotivacional solo si no existe uno con el mismo título
    para el mismo alumno en la ventana de tiempo especificada (horas)."""
    try:
        from datetime import timedelta
        from .models import MensajeMotivacional

        cutoff = timezone.now() - timedelta(hours=ventana_horas)
        existe = MensajeMotivacional.objects.filter(
            alumno=alumno,
            titulo=titulo,
            fecha_envio__gte=cutoff
        ).exists()

        if not existe:
            return MensajeMotivacional.objects.create(
                alumno=alumno,
                tipo=tipo,
                titulo=titulo,
                contenido=contenido,
                prioridad=prioridad
            )
    except Exception:
        logger.exception('Error en crear_mensaje_si_no_duplicado')
    return None

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@require_role('alumno')
def informacion_inicial(request):
    """Formulario de información inicial para nuevos alumnos"""
    try:
        # Verificar si ya tiene información completa
        info_alumno = InformacionAlumno.objects.filter(user=request.user).first()
        if info_alumno and info_alumno.informacion_completa:
            messages.info(request, 'Ya tienes información registrada')
            return redirect('alumno:dashboard')
        
        if request.method == 'POST':
            # Crear o actualizar información del alumno
            if not info_alumno:
                info_alumno = InformacionAlumno(user=request.user)
            
            info_alumno.nombre_completo = request.POST.get('nombre_completo')
            info_alumno.fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
            info_alumno.genero = request.POST.get('genero')
            info_alumno.telefono = request.POST.get('telefono', '')
            info_alumno.direccion = request.POST.get('direccion', '')
            info_alumno.altura = request.POST.get('altura') or None
            info_alumno.peso_actual = request.POST.get('peso_actual') or None
            info_alumno.porcentaje_grasa = request.POST.get('porcentaje_grasa') or None
            info_alumno.informacion_completa = True
            
            info_alumno.save()
            
            messages.success(request, '¡Información guardada exitosamente! Bienvenido al sistema.')
            return redirect('alumno:dashboard')
        
        context = {
            'info_alumno': info_alumno,
            'generos': InformacionAlumno.GENERO_CHOICES,
        }
        
        return render(request, 'alumno/informacion_inicial.html', context)
        
    except Exception as e:
        logger.error(f"Error en información inicial: {e}")
        messages.error(request, 'Error procesando la información')
        return redirect('alumno:dashboard')

@require_role('alumno')
def dashboard_alumno(request):
    """Dashboard del alumno con datos reales de la base de datos AWS"""
    from django.db import connection
    
    try:
        # Verificar si necesita completar información inicial
        info_alumno = InformacionAlumno.objects.filter(user=request.user).first()
        if not info_alumno or not info_alumno.informacion_completa:
            return redirect('alumno:informacion_inicial')
        
        # Crear perfil si no existe
        perfil, created = PerfilAlumno.objects.get_or_create(
            user=request.user,
            defaults={'fecha_inscripcion': timezone.now()}
        )
        
        # Obtener datos directamente desde admin
        total_visitas = 0
        accesos_recientes = []
        
        with connection.cursor() as cursor:
            # Buscar cliente por user_id primero
            cursor.execute("SELECT id FROM admin_gym_cliente WHERE user_id = %s", [request.user.id])
            cliente_result = cursor.fetchone()
            
            if not cliente_result:
                # Buscar por email como fallback
                cursor.execute("SELECT id FROM admin_gym_cliente WHERE email = %s", [request.user.email])
                cliente_result = cursor.fetchone()
                
                if cliente_result:
                    # Actualizar con user_id para futuras consultas
                    cursor.execute("UPDATE admin_gym_cliente SET user_id = %s WHERE id = %s", [request.user.id, cliente_result[0]])
            
            if cliente_result:
                cliente_id = cliente_result[0]
                
                # Total de visitas
                cursor.execute("SELECT COUNT(*) FROM admin_gym_asistencia WHERE cliente_id = %s", [cliente_id])
                total_visitas = cursor.fetchone()[0] or 0
                
                # Accesos recientes
                cursor.execute("""
                    SELECT fecha FROM admin_gym_asistencia 
                    WHERE cliente_id = %s
                    ORDER BY fecha DESC LIMIT 5
                """, [cliente_id])
                
                accesos_data = cursor.fetchall()
                accesos_recientes = [{
                    'fecha_acceso': row[0],
                    'tipo_acceso': 'entrada'
                } for row in accesos_data]
        
        # Obtener progreso físico reciente
        progreso_reciente = ProgresoFisico.objects.filter(
            alumno=perfil
        ).order_by('-fecha').first()
        
        # Obtener mensajes motivacionales no leídos
        mensajes_no_leidos = MensajeMotivacional.objects.filter(
            alumno=perfil,
            leido=False
        ).count()
        
        # Ejecutar heurísticas ligeras para generar mensajes motivacionales
        try:
            from .heuristicas_motivacion import generar_mensajes_motivacionales
            generar_mensajes_motivacionales(perfil)
        except Exception:
            # fallback al motor antiguo si existe
            try:
                MotorRecomendaciones.procesar_mensajes_alumno(perfil.id)
            except Exception:
                pass

        # Obtener últimas 3 notificaciones para mostrar en el panel del dashboard
        try:
            ultimas_notificaciones = MensajeMotivacional.objects.filter(
                alumno=perfil
            ).order_by('-fecha_envio')[:3]
        except Exception:
            ultimas_notificaciones = []
        
        # Chat feature removed — mantener contador en 0
        unread_chat_count = 0
        
        # Obtener información del alumno
        info_alumno = InformacionAlumno.objects.filter(user=request.user).first()
        
        context = {
            'perfil': perfil,
            'info_alumno': info_alumno,
            'accesos_recientes': accesos_recientes,
            'progreso_reciente': progreso_reciente,
            'total_visitas': total_visitas,
            'user': request.user,
            'unread_chat_count': unread_chat_count,
            'mensajes_no_leidos': mensajes_no_leidos,
            'notificaciones': ultimas_notificaciones,
        }
        # Incluir datos de hábitos buenos para uso en el dashboard (agua/sueño)
        try:
            habitos_activos = HabitoBueno.objects.filter(alumno=perfil, activo=True)
            habito_agua = habitos_activos.filter(tipo='agua').first()
            habito_sueno = habitos_activos.filter(tipo='sueno').first()
            context['habito_agua_id'] = habito_agua.id if habito_agua else None
            context['habito_agua_meta'] = habito_agua.meta_diaria if habito_agua else None
            context['habito_sueno_id'] = habito_sueno.id if habito_sueno else None
            context['habito_sueno_meta'] = habito_sueno.meta_diaria if habito_sueno else None
        except Exception:
            context['habito_agua_id'] = None
            context['habito_agua_meta'] = None
            context['habito_sueno_id'] = None
            context['habito_sueno_meta'] = None
        
    except Exception as e:
        logger.error(f"Error en dashboard alumno: {e}")
        # Crear perfil si no existe
        perfil, created = PerfilAlumno.objects.get_or_create(
            user=request.user,
            defaults={'fecha_inscripcion': timezone.now()}
        )
        context = {
            'perfil': perfil,
            'info_alumno': InformacionAlumno.objects.filter(user=request.user).first(),
            'accesos_recientes': [],
            'progreso_reciente': None,
            'total_visitas': 0,
            'user': request.user,
            'unread_chat_count': 0,
            'mensajes_no_leidos': 0,
            'error_message': f'Error: {str(e)}'
        }
    
    return render(request, 'alumno/dashboard.html', context)

@require_role('alumno')
def generar_qr(request):
    """Generar QR para marcar asistencia en el admin"""
    try:
        import qrcode
        from io import BytesIO
        import base64
        import uuid
        
        # Generar token único para este QR
        token = str(uuid.uuid4())
        import time
        timestamp = time.time()
        
        # Datos del QR: user_id:token:timestamp
        qr_data = f"{request.user.id}:{token}:{timestamp}"
        
        # Crear QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Generar imagen
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Convertir a base64
        qr_image = base64.b64encode(buffer.getvalue()).decode()
        
        return JsonResponse({
            'qr_code': qr_image,
            'valido_hasta': timestamp + 300  # 5 minutos
        })
        
    except Exception as e:
        logger.error(f"Error generando QR: {e}")
        return JsonResponse({'error': 'Error generando QR'}, status=500)

@csrf_protect
@require_http_methods(["POST"])
def validar_acceso_qr(request):
    try:
        data = json.loads(request.body)
        qr_data = escape(data.get('qr_data', ''))
        
        if ':' not in qr_data:
            return JsonResponse({'error': 'QR inválido'}, status=400)
        
        user_id, token = qr_data.split(':', 1)
        
        # Mock validation para pruebas
        if user_id == '1' and len(token) > 5: # Simple validation
            logger.info(f"Acceso concedido (demo) para user_id: {user_id}")
            return JsonResponse({
                'success': True,
                'usuario': escape('Juan Pérez (Demo)'),
                'plan': escape('Pro')
            })
        else:
            logger.warning(f"Acceso denegado (demo) para user_id: {user_id}")
            return JsonResponse({'error': 'QR inválido (demo)'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error validando QR: {str(e)}")
        return JsonResponse({'error': 'Error interno'}, status=500)

@require_role('alumno')
def rutina_personalizada(request):
    """Rutina asignada por el entrenador"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        # Buscar rutina asignada por entrenador
        rutina_entrenador = RutinaAlumno.objects.filter(
            alumno=perfil,
            tipo='asignada',
            activa=True
        ).first()
        
        if rutina_entrenador:
            ejercicios_rutina = rutina_entrenador.ejercicios.all().order_by('orden')
            
            context = {
                'perfil': perfil,
                'rutina': rutina_entrenador,
                'ejercicios': ejercicios_rutina,
                'tiene_rutina': True
            }
        else:
            # Si no hay rutina asignada, mostrar mensaje
            context = {
                'perfil': perfil,
                'rutina': None,
                'ejercicios': [],
                'tiene_rutina': False,
                'mensaje': 'Aún no tienes una rutina asignada por tu entrenador'
            }
        
    except Exception as e:
        logger.error(f"Error en rutina personalizada: {e}")
        context = {
            'perfil': None,
            'rutina': None,
            'ejercicios': [],
            'tiene_rutina': False,
            'error_message': 'Error cargando rutina'
        }
    
    return render(request, 'alumno/rutina.html', context)

@require_role('alumno')
def registrar_progreso(request):
    """Registrar progreso físico real"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        if request.method == 'POST':
            peso = request.POST.get('peso')
            masa_muscular = request.POST.get('masa_muscular')
            porcentaje_grasa = request.POST.get('porcentaje_grasa')
            notas = request.POST.get('notas', '')
            
            try:
                # Crear registro de progreso
                ProgresoFisico.objects.create(
                    alumno=perfil,
                    peso=float(peso) if peso else None,
                    grasa_corporal=float(porcentaje_grasa) if porcentaje_grasa else None,
                    masa_muscular=float(masa_muscular) if masa_muscular else None,
                    notas=notas
                )
                
                # Crear mensaje motivacional al registrar progreso
                mensaje_generado = None
                try:
                    titulo = 'Progreso registrado ✅'
                    partes = []
                    if peso:
                        partes.append(f'Peso: {peso} kg')
                    if porcentaje_grasa:
                        partes.append(f'% Grasa: {porcentaje_grasa}')
                    if masa_muscular:
                        partes.append(f'Masa muscular: {masa_muscular}')
                    contenido = 'Registro de progreso: ' + ', '.join(partes) if partes else 'Has registrado tu progreso.'
                    mensaje_obj = crear_mensaje_si_no_duplicado(perfil, 'progreso', titulo, contenido, prioridad=1, ventana_horas=24)
                    if mensaje_obj:
                        mensaje_generado = {
                            'id': mensaje_obj.id,
                            'titulo': mensaje_obj.titulo,
                            'contenido': mensaje_obj.contenido,
                            'tipo': mensaje_obj.tipo,
                            'prioridad': mensaje_obj.prioridad,
                            'fecha_envio': mensaje_obj.fecha_envio.isoformat()
                        }
                except Exception:
                    mensaje_generado = None

                messages.success(request, 'Progreso registrado exitosamente')

                # Si la petición viene por AJAX (fetch desde frontend), devolver JSON con mensaje generado
                try:
                    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
                except Exception:
                    is_ajax = False

                if is_ajax:
                    resp = {'success': True}
                    if mensaje_generado:
                        resp['mensaje_generado'] = mensaje_generado
                    return JsonResponse(resp)

                return redirect('alumno:progreso')
            except Exception as e:
                logger.error(f"Error creando progreso: {e}")
                messages.error(request, 'Error registrando progreso. Intenta nuevamente.')
        
        # Obtener historial de progreso
        try:
            progresos = ProgresoFisico.objects.filter(
                alumno=perfil
            ).order_by('-fecha')[:20]
        except Exception as e:
            logger.error(f"Error obteniendo progresos: {e}")
            progresos = []
        
        context = {
            'perfil': perfil,
            'progresos': progresos,
        }
        
    except Exception as e:
        logger.error(f"Error en registrar progreso: {e}")
        # Crear perfil si no existe
        perfil, created = PerfilAlumno.objects.get_or_create(
            user=request.user,
            defaults={'fecha_inscripcion': timezone.now()}
        )
        context = {
            'perfil': perfil,
            'progresos': [],
            'error_message': 'Funcionalidad de progreso físico en desarrollo'
        }
    
    return render(request, 'alumno/progreso.html', context)


@require_role('alumno')
@csrf_protect
def api_progreso_detail(request, progreso_id):
    """API JSON para ver/editar/eliminar un registro de ProgresoFisico del alumno.
    Rutas aceptadas:
    - GET: devolver detalle JSON
    - PUT/PATCH/POST: actualizar campos (peso, grasa_corporal, masa_muscular, notas)
    - DELETE: eliminar registro
    """
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        progreso = get_object_or_404(ProgresoFisico, pk=progreso_id, alumno=perfil)

        if request.method == 'GET':
            return JsonResponse({
                'id': progreso.id,
                'fecha': progreso.fecha.isoformat(),
                'peso': progreso.peso,
                'grasa_corporal': progreso.grasa_corporal,
                'masa_muscular': progreso.masa_muscular,
                'notas': progreso.notas or ''
            })

        # Actualizar (aceptamos POST como compatibilidad con navegadores que no usan PUT)
        if request.method in ('PUT', 'PATCH', 'POST'):
            try:
                # Intentar parsear JSON si viene en body
                try:
                    data = json.loads(request.body.decode('utf-8')) if request.body else {}
                except Exception:
                    data = request.POST.dict()

                peso = data.get('peso')
                grasa = data.get('grasa_corporal') or data.get('grasa')
                musculo = data.get('masa_muscular') or data.get('musculo')
                notas = data.get('notas')

                if peso is not None and peso != '':
                    progreso.peso = float(peso)
                else:
                    progreso.peso = None

                if grasa is not None and grasa != '':
                    progreso.grasa_corporal = float(grasa)
                else:
                    progreso.grasa_corporal = None

                if musculo is not None and musculo != '':
                    progreso.masa_muscular = float(musculo)
                else:
                    progreso.masa_muscular = None

                if notas is not None:
                    progreso.notas = notas

                progreso.save()

                return JsonResponse({'success': True, 'id': progreso.id})
            except Exception as e:
                logger.exception('Error actualizando progreso')
                return JsonResponse({'error': 'Error actualizando registro'}, status=400)

        if request.method == 'DELETE':
            try:
                progreso.delete()
                return JsonResponse({'success': True})
            except Exception as e:
                logger.exception('Error eliminando progreso')
                return JsonResponse({'error': 'Error eliminando registro'}, status=400)

        return JsonResponse({'error': 'Método no permitido'}, status=405)

    except Exception as e:
        logger.exception(f'API progreso error: {e}')
        return JsonResponse({'error': 'Error interno'}, status=500)


@require_role('alumno')
def export_progresos(request):
    """Exportar los registros de progreso del alumno.
    Soporta formatos: csv (por defecto), pdf (si reportlab está instalado).
    """
    perfil = get_object_or_404(PerfilAlumno, user=request.user)
    formato = request.GET.get('format', 'csv').lower()

    progresos = ProgresoFisico.objects.filter(alumno=perfil).order_by('-fecha')

    if formato == 'csv' or formato == 'excel':
        # Generar CSV en memoria
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['id', 'fecha', 'peso', 'grasa_corporal', 'masa_muscular', 'notas'])
        for p in progresos:
            fecha = p.fecha.isoformat() if p.fecha else ''
            writer.writerow([p.id, fecha, p.peso if p.peso is not None else '', p.grasa_corporal if p.grasa_corporal is not None else '', p.masa_muscular if p.masa_muscular is not None else '', p.notas or ''])

        resp = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="progreso_export.csv"'
        return resp

    if formato == 'pdf':
        # Try to generate a simple PDF using reportlab if available
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch

            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            x = inch * 0.5
            y = height - inch * 0.75

            c.setFont('Helvetica-Bold', 14)
            c.drawString(x, y, 'Exportación de Progreso - Fitspace')
            c.setFont('Helvetica', 10)
            y -= 20

            # Table header
            c.drawString(x, y, 'Fecha')
            c.drawString(x + 120, y, 'Peso')
            c.drawString(x + 180, y, 'Grasa')
            c.drawString(x + 240, y, 'Masa')
            c.drawString(x + 300, y, 'Notas')
            y -= 12

            for p in progresos:
                if y < inch:  # new page
                    c.showPage()
                    y = height - inch * 0.75
                fecha = p.fecha.strftime('%Y-%m-%d %H:%M') if p.fecha else ''
                notas = (p.notas or '').replace('\n', ' ')[:80]
                c.drawString(x, y, fecha)
                c.drawString(x + 120, y, str(p.peso or ''))
                c.drawString(x + 180, y, str(p.grasa_corporal or ''))
                c.drawString(x + 240, y, str(p.masa_muscular or ''))
                c.drawString(x + 300, y, notas)
                y -= 14

            c.save()
            buffer.seek(0)
            resp = HttpResponse(buffer.read(), content_type='application/pdf')
            resp['Content-Disposition'] = 'attachment; filename="progreso_export.pdf"'
            return resp
        except ImportError:
            # reportlab no está instalado
            return HttpResponse('PDF export not available. Install reportlab (pip install reportlab) to enable PDF export.', status=501)

    return HttpResponse('Formato no soportado', status=400)

@require_role('alumno')
def historial_asistencia(request):
    """Historial real de asistencias desde la base de datos"""
    from django.db import connection
    from datetime import timedelta
    
    try:
        # Crear perfil si no existe
        perfil, created = PerfilAlumno.objects.get_or_create(
            user=request.user,
            defaults={'fecha_inscripcion': timezone.now()}
        )
        
        accesos = []
        total_visitas = 0
        visitas_ultimo_mes = 0
        promedio_semanal = 0
        
        with connection.cursor() as cursor:
            # Buscar cliente por user_id primero
            cursor.execute("SELECT id FROM admin_gym_cliente WHERE user_id = %s", [request.user.id])
            cliente_result = cursor.fetchone()
            
            if not cliente_result:
                # Buscar por email como fallback
                cursor.execute("SELECT id FROM admin_gym_cliente WHERE email = %s", [request.user.email])
                cliente_result = cursor.fetchone()
                
                if cliente_result:
                    # Actualizar con user_id para futuras consultas
                    cursor.execute("UPDATE admin_gym_cliente SET user_id = %s WHERE id = %s", [request.user.id, cliente_result[0]])
            
            if cliente_result:
                cliente_id = cliente_result[0]
                
                # Total de visitas
                cursor.execute("SELECT COUNT(*) FROM admin_gym_asistencia WHERE cliente_id = %s", [cliente_id])
                total_visitas = cursor.fetchone()[0] or 0
                
                # Obtener historial
                cursor.execute("""
                    SELECT fecha FROM admin_gym_asistencia 
                    WHERE cliente_id = %s
                    ORDER BY fecha DESC LIMIT 50
                """, [cliente_id])
                
                accesos_data = cursor.fetchall()
                accesos = [{
                    'fecha_acceso': row[0],
                    'tipo_acceso': 'entrada'
                } for row in accesos_data]
                
                # Visitas último mes
                hace_30_dias = timezone.now() - timedelta(days=30)
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_asistencia 
                    WHERE cliente_id = %s AND fecha >= %s
                """, [cliente_id, hace_30_dias])
                
                visitas_ultimo_mes = cursor.fetchone()[0] or 0
                promedio_semanal = round(visitas_ultimo_mes / 4.3, 1) if visitas_ultimo_mes > 0 else 0
        
        context = {
            'perfil': perfil,
            'accesos': accesos,
            'total_visitas': total_visitas,
            'promedio_semanal': promedio_semanal,
            'visitas_ultimo_mes': visitas_ultimo_mes,
        }
        
    except Exception as e:
        logger.error(f"Error en historial asistencia: {e}")
        # Crear perfil si no existe
        perfil, created = PerfilAlumno.objects.get_or_create(
            user=request.user,
            defaults={'fecha_inscripcion': timezone.now()}
        )
        context = {
            'perfil': perfil,
            'accesos': [],
            'total_visitas': 0,
            'promedio_semanal': 0,
            'visitas_ultimo_mes': 0,
            'error_message': f'Error: {str(e)}'
        }
    
    return render(request, 'alumno/historial.html', context)

@require_role('alumno')
def metricas_personales(request):
    """Métricas reales del alumno desde la base de datos"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        # Total de visitas directamente desde admin
        total_visitas = obtener_total_visitas_admin(request.user.id)
        
        # Última visita desde tabla del admin
        from django.db import connection
        ultima_visita = None
        
        try:
            with connection.cursor() as cursor:
                cliente_id = obtener_cliente_id_admin(cursor, request.user.id)
                if cliente_id:
                    # Última visita
                    cursor.execute("""
                        SELECT fecha FROM admin_gym_asistencia 
                        WHERE cliente_id = %s
                        ORDER BY fecha DESC LIMIT 1
                    """, [cliente_id])
                    
                    result = cursor.fetchone()
                    if result:
                        ultima_visita = {'fecha_acceso': result[0]}
                    
        except Exception as e:
            logger.error(f"Error obteniendo métricas del admin: {e}")
            # Fallback a tabla local
            try:
                total_visitas = AccesoGimnasio.objects.filter(
                    alumno=perfil,
                    tipo_acceso='entrada'
                ).count()
                
                ultima_visita = AccesoGimnasio.objects.filter(
                    alumno=perfil,
                    tipo_acceso='entrada'
                ).order_by('-fecha_acceso').first()
            except:
                pass
        
        # Días activo (desde la inscripción)
        dias_activo = (timezone.now().date() - perfil.fecha_inscripcion.date()).days
        
        # Progreso físico
        progresos = ProgresoFisico.objects.filter(
            alumno=perfil
        ).order_by('-fecha')[:10]
        
        # Ejercicios realizados
        total_ejercicios = RegistroEjercicio.objects.filter(
            alumno=perfil
        ).count()
        
        # Hábitos buenos completados
        habitos_completados = RegistroHabitoBueno.objects.filter(
            habito__alumno=perfil
        ).count()
        
        # Metas activas
        from .models import Meta as MetaAlumno
        metas_activas = MetaAlumno.objects.filter(
            alumno=perfil,
            estado='activa'
        ).count()
        
        # Frecuencia de visitas (visitas por semana) - usar datos reales del admin
        if dias_activo > 0 and total_visitas > 0:
            frecuencia_semanal = round((total_visitas * 7) / dias_activo, 1)
        else:
            frecuencia_semanal = 0
        
        # Racha actual (días consecutivos con actividad)
        racha_actual = calcular_racha_actual_admin(request.user.id)
        
        # Calcular estadísticas detalladas desde admin
        estadisticas_detalladas = calcular_estadisticas_detalladas_admin(request.user.id)
        
        # Comparación con otros usuarios
        comparacion_usuarios = calcular_comparacion_usuarios_admin(request.user.id, total_visitas)
        
        # Logros desbloqueados basados en datos reales
        logros = calcular_logros_reales(request.user.id, total_visitas, racha_actual)
        
        # Horarios preferidos desde admin
        horarios_preferidos = calcular_horarios_preferidos_admin(request.user.id)
        
        # Evolución mensual desde admin
        evolucion_data = calcular_evolucion_mensual_admin(request.user.id)
        evolucion_mensual = evolucion_data['datos']
        etiquetas_meses = evolucion_data['etiquetas']
        
        # Objetivos del mes
        objetivos_mes = calcular_objetivos_mes_admin(request.user.id, total_ejercicios, habitos_completados)
        
        import json
        
        context = {
            'perfil': perfil,
            'total_visitas': total_visitas,
            'dias_activo': dias_activo,
            'progresos': progresos,
            'total_ejercicios': total_ejercicios,
            'habitos_completados': habitos_completados,
            'metas_activas': metas_activas,
            'frecuencia_semanal': frecuencia_semanal,
            'ultima_visita': ultima_visita,
            'racha_actual': racha_actual,
            'estadisticas_detalladas': estadisticas_detalladas,
            'comparacion_usuarios': comparacion_usuarios,
            'logros': json.dumps(logros),
            'horarios_preferidos': json.dumps(horarios_preferidos),
            'evolucion_mensual': json.dumps(evolucion_mensual),
            'etiquetas_meses': json.dumps(etiquetas_meses),
            **objetivos_mes,
        }
        
    except Exception as e:
        logger.error(f"Error en métricas personales: {e}")
        context = {
            'perfil': None,
            'total_visitas': 0,
            'dias_activo': 0,
            'progresos': [],
            'error_message': 'Error cargando métricas'
        }
    
    return render(request, 'alumno/metricas.html', context)

def calcular_racha_actual_admin(user_id):
    """Calcula la racha actual usando la tabla del admin"""
    try:
        from datetime import timedelta
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Primero obtener el cliente_id
            cursor.execute("""
                SELECT id FROM admin_gym_cliente WHERE user_id = %s
            """, [user_id])
            
            cliente_result = cursor.fetchone()
            if not cliente_result:
                logger.warning(f"No se encontró cliente para calcular racha, user_id: {user_id}")
                return 0
            
            cliente_id = cliente_result[0]
            
            # Obtener fechas únicas de acceso
            cursor.execute("""
                SELECT DISTINCT DATE(fecha) as fecha
                FROM admin_gym_asistencia 
                WHERE cliente_id = %s
                ORDER BY fecha DESC
            """, [cliente_id])
            
            fechas_data = cursor.fetchall()
            if not fechas_data:
                return 0
            
            fechas_acceso = [row[0] for row in fechas_data]
            
        racha = 0
        fecha_actual = timezone.now().date()
        
        # Verificar si hay actividad hoy o ayer
        if fechas_acceso[0] == fecha_actual:
            racha = 1
            fecha_esperada = fecha_actual - timedelta(days=1)
        elif fechas_acceso[0] == fecha_actual - timedelta(days=1):
            racha = 1
            fecha_esperada = fechas_acceso[0] - timedelta(days=1)
        else:
            return 0
        
        # Contar días consecutivos hacia atrás
        for fecha in fechas_acceso[1:]:
            if fecha == fecha_esperada:
                racha += 1
                fecha_esperada -= timedelta(days=1)
            else:
                break
        
        return racha
        
    except Exception as e:
        logger.error(f"Error calculando racha desde admin: {e}")
        return 0

def calcular_estadisticas_detalladas_admin(user_id):
    """Calcula estadísticas detalladas desde la tabla del admin"""
    try:
        from django.db import connection
        from datetime import timedelta
        
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if not cliente_id:
                return {'tiempo_promedio': '0h', 'mejor_racha': 0, 'hora_favorita': '--', 'consistencia': 0}
            
            # Tiempo promedio estimado (sin datos de salida, usar promedio estándar)
            tiempo_promedio = 90  # 1.5 horas promedio
            tiempo_promedio_str = f"{tiempo_promedio//60}h {tiempo_promedio%60}m"
            
            # Hora favorita
            cursor.execute("""
                SELECT HOUR(fecha) as hora, COUNT(*) as cantidad
                FROM admin_gym_asistencia 
                WHERE cliente_id = %s
                GROUP BY HOUR(fecha)
                ORDER BY cantidad DESC
                LIMIT 1
            """, [cliente_id])
            
            resultado = cursor.fetchone()
            hora_favorita = f"{resultado[0]:02d}:00" if resultado else '--'
            
            # Consistencia (% de días con actividad en el último mes)
            hace_30_dias = timezone.now() - timedelta(days=30)
            cursor.execute("""
                SELECT COUNT(DISTINCT DATE(fecha)) as dias_activos
                FROM admin_gym_asistencia 
                WHERE cliente_id = %s AND fecha >= %s
            """, [cliente_id, hace_30_dias])
            
            resultado = cursor.fetchone()
            dias_activos = resultado[0] if resultado else 0
            consistencia = round((dias_activos / 30) * 100, 0)
            
            return {
                'tiempo_promedio': tiempo_promedio_str,
                'mejor_racha': calcular_mejor_racha_admin(user_id),
                'hora_favorita': hora_favorita,
                'consistencia': f"{consistencia}%"
            }
            
    except Exception as e:
        logger.error(f"Error calculando estadísticas detalladas: {e}")
        return {'tiempo_promedio': '0h', 'mejor_racha': 0, 'hora_favorita': '--', 'consistencia': '0%'}

def calcular_mejor_racha_admin(user_id):
    """Calcula la mejor racha histórica"""
    try:
        from django.db import connection
        from datetime import timedelta
        
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if not cliente_id:
                return 0
            
            cursor.execute("""
                SELECT DISTINCT DATE(fecha) as fecha
                FROM admin_gym_asistencia 
                WHERE cliente_id = %s
                ORDER BY fecha
            """, [cliente_id])
            
            fechas = [row[0] for row in cursor.fetchall()]
            if not fechas:
                return 0
            
            mejor_racha = 0
            racha_actual = 1
            
            for i in range(1, len(fechas)):
                if fechas[i] - fechas[i-1] == timedelta(days=1):
                    racha_actual += 1
                else:
                    mejor_racha = max(mejor_racha, racha_actual)
                    racha_actual = 1
            
            return max(mejor_racha, racha_actual)
            
    except Exception as e:
        logger.error(f"Error calculando mejor racha: {e}")
        return 0

def calcular_comparacion_usuarios_admin(user_id, total_visitas):
    """Calcula comparación con otros usuarios"""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Total de usuarios activos
            cursor.execute("""
                SELECT COUNT(DISTINCT cliente_id) FROM admin_gym_asistencia 
                WHERE fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            
            total_usuarios = cursor.fetchone()[0] or 1
            
            # Usuarios con menos visitas que el usuario actual
            cursor.execute("""
                SELECT COUNT(DISTINCT cliente_id) FROM (
                    SELECT cliente_id, COUNT(*) as visitas
                    FROM admin_gym_asistencia 
                    WHERE fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY cliente_id
                    HAVING visitas < %s
                ) as subquery
            """, [total_visitas])
            
            usuarios_debajo = cursor.fetchone()[0] or 0
            percentil = round((usuarios_debajo / total_usuarios) * 100, 0)
            
            # Sin datos de salida, usar promedio estándar
            promedio_duracion = 90  # 1.5 horas promedio
            
            return {
                'percentil': f"Top {100-percentil}%" if percentil > 50 else f"Bottom {percentil}%",
                'promedio_duracion': f"{promedio_duracion//60}h {promedio_duracion%60}m",
                'total_usuarios': total_usuarios
            }
            
    except Exception as e:
        logger.error(f"Error calculando comparación: {e}")
        return {'percentil': 'Top 50%', 'promedio_duracion': '1h 0m', 'total_usuarios': 100}

def calcular_logros_reales(user_id, total_visitas, racha_actual):
    """Calcula logros basados en datos reales"""
    try:
        from django.db import connection
        
        logros = []
        
        # Primera visita
        logros.append({
            'id': 'primera_visita',
            'nombre': 'Primera Visita',
            'descripcion': 'Completaste tu primera sesión',
            'icono': 'fa-star',
            'desbloqueado': total_visitas > 0
        })
        
        # Racha de 7 días
        logros.append({
            'id': 'racha_7',
            'nombre': '7 Días Seguidos',
            'descripcion': 'Mantuviste una racha de 7 días',
            'icono': 'fa-fire',
            'desbloqueado': racha_actual >= 7 or calcular_mejor_racha_admin(user_id) >= 7
        })
        
        # 50 visitas
        logros.append({
            'id': 'constante',
            'nombre': 'Constancia',
            'descripcion': '50 visitas completadas',
            'icono': 'fa-trophy',
            'desbloqueado': total_visitas >= 50
        })
        
        # Madrugador (antes de las 7 AM)
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if cliente_id:
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_asistencia 
                    WHERE cliente_id = %s AND HOUR(fecha) < 7
                """, [cliente_id])
                
                visitas_temprano = cursor.fetchone()[0] or 0
                
                logros.append({
                    'id': 'madrugador',
                    'nombre': 'Madrugador',
                    'descripcion': 'Entrenas antes de las 7 AM',
                    'icono': 'fa-sun',
                    'desbloqueado': visitas_temprano >= 5
                })
                
                # Nocturno (después de las 9 PM)
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_asistencia 
                    WHERE cliente_id = %s AND HOUR(fecha) >= 21
                """, [cliente_id])
                
                visitas_noche = cursor.fetchone()[0] or 0
                
                logros.append({
                    'id': 'nocturno',
                    'nombre': 'Búho Nocturno',
                    'descripcion': 'Entrenas después de las 9 PM',
                    'icono': 'fa-moon',
                    'desbloqueado': visitas_noche >= 5
                })
        
        return logros
        
    except Exception as e:
        logger.error(f"Error calculando logros: {e}")
        return []

def calcular_horarios_preferidos_admin(user_id):
    """Calcula horarios preferidos desde admin"""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if not cliente_id:
                return {}
            
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN HOUR(fecha) BETWEEN 6 AND 8 THEN '06:00-09:00'
                        WHEN HOUR(fecha) BETWEEN 9 AND 11 THEN '09:00-12:00'
                        WHEN HOUR(fecha) BETWEEN 12 AND 14 THEN '12:00-15:00'
                        WHEN HOUR(fecha) BETWEEN 15 AND 17 THEN '15:00-18:00'
                        WHEN HOUR(fecha) BETWEEN 18 AND 20 THEN '18:00-21:00'
                        ELSE '21:00-24:00'
                    END as franja,
                    COUNT(*) as cantidad
                FROM admin_gym_asistencia 
                WHERE cliente_id = %s
                GROUP BY franja
                ORDER BY cantidad DESC
            """, [cliente_id])
            
            resultados = cursor.fetchall()
            return {franja: cantidad for franja, cantidad in resultados}
            
    except Exception as e:
        logger.error(f"Error calculando horarios preferidos: {e}")
        return {}

def calcular_evolucion_mensual_admin(user_id):
    """Calcula evolución mensual desde admin - últimos 6 meses"""
    try:
        from django.db import connection
        from datetime import datetime, timedelta
        import calendar
        
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if not cliente_id:
                return {'datos': [0, 0, 0, 0, 0, 0], 'etiquetas': []}
            
            # Generar últimos 6 meses
            hoy = datetime.now()
            meses_datos = []
            etiquetas = []
            
            for i in range(5, -1, -1):  # 6 meses hacia atrás
                fecha = hoy - timedelta(days=30*i)
                mes_str = fecha.strftime('%Y-%m')
                etiqueta = fecha.strftime('%b')
                
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_asistencia 
                    WHERE cliente_id = %s
                        AND DATE_FORMAT(fecha, '%%Y-%%m') = %s
                """, [cliente_id, mes_str])
                
                resultado = cursor.fetchone()
                visitas = resultado[0] if resultado else 0
                
                meses_datos.append(visitas)
                etiquetas.append(etiqueta)
            
            return {'datos': meses_datos, 'etiquetas': etiquetas}
            
    except Exception as e:
        logger.error(f"Error calculando evolución mensual: {e}")
        return {'datos': [0, 0, 0, 0, 0, 0], 'etiquetas': ['Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov']}

def calcular_objetivos_mes_admin(user_id, total_ejercicios, habitos_completados):
    """Calcula objetivos del mes actual"""
    try:
        from django.db import connection
        from datetime import datetime
        
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if not cliente_id:
                return {
                    'visitas_mes_actual': 0,
                    'porcentaje_visitas_mes': 0,
                    'porcentaje_ejercicios': 0,
                    'porcentaje_habitos': 0
                }
            
            # Visitas del mes actual
            mes_actual = datetime.now().strftime('%Y-%m')
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_asistencia 
                WHERE cliente_id = %s
                    AND DATE_FORMAT(fecha, '%%Y-%%m') = %s
            """, [cliente_id, mes_actual])
            
            visitas_mes = cursor.fetchone()[0] or 0
            
            return {
                'visitas_mes_actual': visitas_mes,
                'porcentaje_visitas_mes': min(100, (visitas_mes / 20) * 100),
                'porcentaje_ejercicios': min(100, (total_ejercicios / 50) * 100),
                'porcentaje_habitos': min(100, (habitos_completados / 30) * 100)
            }
            
    except Exception as e:
        logger.error(f"Error calculando objetivos del mes: {e}")
        return {
            'visitas_mes_actual': 0,
            'porcentaje_visitas_mes': 0,
            'porcentaje_ejercicios': 0,
            'porcentaje_habitos': 0
        }

def obtener_total_visitas_admin(user_id):
    """Obtiene total de visitas directamente desde admin con sincronización"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cliente_id = obtener_cliente_id_admin(cursor, user_id)
            if not cliente_id:
                return 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_asistencia 
                WHERE cliente_id = %s
            """, [cliente_id])
            
            resultado = cursor.fetchone()
            return resultado[0] if resultado else 0
    except Exception as e:
        logger.error(f"Error obteniendo total visitas: {e}")
        return 0

def obtener_cliente_id_admin(cursor, user_id):
    """Obtiene el cliente_id desde la tabla del admin con sincronización automática"""
    cursor.execute("SELECT id FROM admin_gym_cliente WHERE user_id = %s", [user_id])
    resultado = cursor.fetchone()
    
    if not resultado:
        # Intentar sincronización automática
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
            # Buscar por email o nombre similar
            cursor.execute("""
                SELECT id FROM admin_gym_cliente 
                WHERE email = %s OR nombre LIKE %s
                LIMIT 1
            """, [user.email, f"%{user.get_full_name()}%"])
            
            match_result = cursor.fetchone()
            if match_result:
                # Actualizar con user_id
                cursor.execute("""
                    UPDATE admin_gym_cliente SET user_id = %s WHERE id = %s
                """, [user_id, match_result[0]])
                logger.info(f"Usuario {user_id} sincronizado automáticamente con cliente {match_result[0]}")
                return match_result[0]
        except Exception as e:
            logger.error(f"Error en sincronización automática: {e}")
    
    return resultado[0] if resultado else None

def calcular_racha_actual(perfil):
    """Calcula la racha actual de días consecutivos con actividad (fallback)"""
    try:
        from datetime import timedelta
        
        # Obtener fechas únicas de acceso (solo fechas, no horas)
        fechas_acceso = AccesoGimnasio.objects.filter(
            alumno=perfil,
            tipo_acceso='entrada'
        ).dates('fecha_acceso', 'day').order_by('-fecha_acceso')
        
        if not fechas_acceso:
            return 0
        
        racha = 0
        fecha_actual = timezone.now().date()
        
        # Verificar si hay actividad hoy o ayer
        if fechas_acceso[0] == fecha_actual:
            racha = 1
            fecha_esperada = fecha_actual - timedelta(days=1)
        elif fechas_acceso[0] == fecha_actual - timedelta(days=1):
            racha = 1
            fecha_esperada = fechas_acceso[0] - timedelta(days=1)
        else:
            return 0
        
        # Contar días consecutivos hacia atrás
        for fecha in fechas_acceso[1:]:
            if fecha == fecha_esperada:
                racha += 1
                fecha_esperada -= timedelta(days=1)
            else:
                break
        
        return racha
        
    except Exception as e:
        logger.error(f"Error calculando racha: {e}")
        return 0

@require_role('alumno')
def notificaciones(request):
    """Notificaciones reales con motor heurístico"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        # Ejecutar motor de recomendaciones antes de mostrar notificaciones
        try:
            MotorRecomendaciones.procesar_mensajes_alumno(perfil.id)
        except Exception as e:
            logger.error(f"Error en motor de recomendaciones: {e}")
        
        # Obtener mensajes motivacionales reales
        mensajes = MensajeMotivacional.objects.filter(
            alumno=perfil
        ).order_by('-prioridad', '-fecha_envio')[:20]
        
        # Marcar mensajes como leídos si se solicita
        if request.GET.get('marcar_leidos'):
            mensajes.update(leido=True)
            return JsonResponse({'success': True})
        
        # Contar no leídos
        no_leidos = mensajes.filter(leido=False).count()
        
        context = {
            'perfil': perfil,
            'mensajes': mensajes,
            'no_leidos': no_leidos,
        }
        
    except Exception as e:
        logger.error(f"Error en notificaciones: {e}")
        context = {
            'perfil': None,
            'mensajes': [],
            'no_leidos': 0,
            'error_message': 'Error cargando notificaciones'
        }
    
    return render(request, 'alumno/notificaciones.html', context)

@require_role('alumno')
def habitos_buenos(request):
    """Hábitos buenos reales del alumno"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        if request.method == 'POST':
            # Crear nuevo hábito bueno
            nombre = request.POST.get('nombre')
            tipo = request.POST.get('tipo')
            meta_diaria = int(request.POST.get('meta_diaria', 1))
            unidad = request.POST.get('unidad', 'veces')
            descripcion = request.POST.get('descripcion', '')
            
            HabitoBueno.objects.create(
                alumno=perfil,
                nombre=nombre,
                tipo=tipo,
                meta_diaria=meta_diaria,
                unidad=unidad,
                descripcion=descripcion
            )
            
            messages.success(request, f'Hábito "{nombre}" creado exitosamente')
            return redirect('alumno:habitos_buenos')
        
        # Obtener hábitos reales del alumno
        habitos = HabitoBueno.objects.filter(
            alumno=perfil,
            activo=True
        ).order_by('-fecha_creacion')
        
        # Obtener registros de hoy para cada hábito
        from datetime import timedelta
        hoy = timezone.now().date()
        hace_7_dias = hoy - timedelta(days=7)
        
        habitos_con_progreso = []
        
        for habito in habitos:
            registro_hoy = RegistroHabitoBueno.objects.filter(
                habito=habito,
                fecha=hoy
            ).first()
            
            progreso_hoy = registro_hoy.cantidad if registro_hoy else 0
            porcentaje = min(100, (progreso_hoy / habito.meta_diaria) * 100)
            
            # Calcular progreso semanal
            registros_semana = RegistroHabitoBueno.objects.filter(
                habito=habito,
                fecha__gte=hace_7_dias
            )
            
            dias_completados = registros_semana.filter(
                cantidad__gte=habito.meta_diaria
            ).count()
            
            total_cantidad_semana = sum(r.cantidad for r in registros_semana)
            promedio_diario = total_cantidad_semana / 7 if registros_semana.exists() else 0
            
            habitos_con_progreso.append({
                'habito': habito,
                'progreso_hoy': progreso_hoy,
                'porcentaje': porcentaje,
                'completado': progreso_hoy >= habito.meta_diaria,
                'dias_completados_semana': dias_completados,
                'promedio_diario_semana': round(promedio_diario, 1),
                'total_semana': total_cantidad_semana
            })
        
        # Calcular resumen semanal real (últimos 7 días)
        try:
            from datetime import timedelta
            hoy = timezone.now().date()
            inicio_semana = hoy - timedelta(days=6)  # 7 días incluyendo hoy

            # Obtener registros de la semana y de toda la historia para calcular rachas
            registros_semana = RegistroHabitoBueno.objects.filter(
                habito__alumno=perfil,
                fecha__range=(inicio_semana, hoy)
            ).select_related('habito')

            registros_todos = RegistroHabitoBueno.objects.filter(
                habito__alumno=perfil
            ).select_related('habito').order_by('fecha')

            # Por hábito -> días completados en la semana (cada día cuenta una vez)
            habitos = [h['habito'] for h in habitos_con_progreso]
            total_habitos = len(habitos)

            # Mapa habito.id -> set(fecha) donde la meta fue alcanzada
            completados_por_habito = {h.id: set() for h in habitos}
            fechas_completadas_global = set()

            for reg in registros_semana:
                try:
                    if reg.cantidad >= (reg.habito.meta_diaria or 0):
                        completados_por_habito[reg.habito.id].add(reg.fecha)
                        fechas_completadas_global.add(reg.fecha)
                except Exception:
                    # ignore malformed registros
                    pass

            # Total completados en la semana (suma de días cumplidos por hábito)
            total_completados_semana = sum(len(s) for s in completados_por_habito.values())
            total_posibles = total_habitos * 7 if total_habitos > 0 else 0
            cumplimiento_percent = round((total_completados_semana / total_posibles) * 100, 1) if total_posibles > 0 else 0

            # Días activos: número de días en la semana donde al menos un hábito fue completado
            dias_activos = 0
            for i in range(7):
                d = inicio_semana + timedelta(days=i)
                if any(d in s for s in completados_por_habito.values()):
                    dias_activos += 1

            # Construir set global de fechas completadas en toda la historia para rachas
            fechas_hist = set()
            for reg in registros_todos:
                try:
                    if reg.cantidad >= (reg.habito.meta_diaria or 0):
                        fechas_hist.add(reg.fecha)
                except Exception:
                    pass

            # Calcular racha actual (consecutive days up to today present in fechas_completadas_global)
            racha_actual = 0
            dia_check = hoy
            while dia_check in fechas_completadas_global:
                racha_actual += 1
                dia_check = dia_check - timedelta(days=1)

            # Calcular mejor racha histórica
            mejor_racha = 0
            if fechas_hist:
                fechas_list = sorted(fechas_hist)
                current = 1
                for idx in range(1, len(fechas_list)):
                    if (fechas_list[idx] - fechas_list[idx-1]).days == 1:
                        current += 1
                    else:
                        if current > mejor_racha:
                            mejor_racha = current
                        current = 1
                mejor_racha = max(mejor_racha, current)

        except Exception as e:
            logger.exception('Error calculando resumen semanal')
            cumplimiento_percent = 0
            dias_activos = 0
            racha_actual = 0
            mejor_racha = 0
            total_habitos = len(habitos_con_progreso)

        context = {
            'perfil': perfil,
            'habitos_con_progreso': habitos_con_progreso,
            'tipos_habito': HabitoBueno.TIPO_CHOICES,
            'resumen_semanal': {
                'total_habitos': total_habitos,
                'cumplimiento_percent': cumplimiento_percent,
                'dias_activos': dias_activos,
                'racha_actual': racha_actual,
                'mejor_racha': mejor_racha
            },
        }
        
    except Exception as e:
        logger.error(f"Error en hábitos buenos: {e}")
        context = {
            'perfil': None,
            'habitos_con_progreso': [],
            'tipos_habito': HabitoBueno.TIPO_CHOICES,
            'error_message': 'Error cargando hábitos'
        }
    
    return render(request, 'alumno/habitos_buenos.html', context)

@require_role('alumno')
def registrar_habito_bueno(request, habito_id):
    """Registrar progreso real de hábito bueno"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            habito = get_object_or_404(HabitoBueno, id=habito_id, alumno=perfil)
            
            cantidad = int(request.POST.get('cantidad', 1))
            notas = request.POST.get('notas', '')
            hoy = timezone.now().date()
            
            # Crear o actualizar registro de hoy
            registro, created = RegistroHabitoBueno.objects.get_or_create(
                habito=habito,
                fecha=hoy,
                defaults={'cantidad': cantidad, 'notas': notas}
            )
            
            if not created:
                # Para hábitos de sueño debemos reemplazar el valor (horas),
                # no sumar como con el contador de agua.
                if habito.tipo == 'sueno':
                    registro.cantidad = cantidad
                else:
                    registro.cantidad += cantidad

                if notas:
                    registro.notas = f"{registro.notas}\n{notas}" if registro.notas else notas
                registro.save()
            
            # Verificar si se completó la meta
            completado = registro.cantidad >= habito.meta_diaria
            mensaje = f'Hábito registrado: {registro.cantidad}/{habito.meta_diaria} {habito.unidad}'
            
            if completado:
                mensaje += ' ¡Meta completada! 🎉'

            # Crear mensaje motivacional en base al tipo de hábito y si se completó
            mensaje_generado = None
            try:
                if completado:
                    # Hacer el título único incluyendo la medición para que cada cambio genere una notificación distinta
                    try:
                        unidad = habito.unidad if habito.unidad else ''
                        if habito.tipo == 'agua':
                            titulo = f'¡Meta de agua alcanzada: {registro.cantidad} {unidad}!'
                            contenido = f'Has completado tu objetivo de {habito.meta_diaria} {unidad} hoy. ¡Excelente! Puedes seguir bebiendo si lo deseas.'
                        elif habito.tipo == 'sueno':
                            titulo = f'Buen descanso: {registro.cantidad} {unidad}'
                            contenido = f'Has registrado {registro.cantidad} {unidad} de sueño. Buen trabajo con tu descanso.'
                        else:
                            titulo = f'Has alcanzado tu objetivo: {habito.nombre}'
                            contenido = f'Has alcanzado tu meta: {habito.nombre}. ¡Sigue así!'

                        mensaje_obj = crear_mensaje_si_no_duplicado(perfil, 'habitos', titulo, contenido, prioridad=1, ventana_horas=24)
                    except Exception:
                        logger.exception('Error formando mensaje para hábito completado')
                        mensaje_obj = None

                    if mensaje_obj:
                        mensaje_generado = {
                            'id': mensaje_obj.id,
                            'titulo': mensaje_obj.titulo,
                            'contenido': mensaje_obj.contenido,
                            'tipo': mensaje_obj.tipo,
                            'prioridad': mensaje_obj.prioridad,
                            'fecha_envio': mensaje_obj.fecha_envio.isoformat()
                        }

                    # Ejecutar heurísticas adicionales (p.ej. para otros hábitos/metas relacionados)
                    try:
                        from .heuristicas_motivacion import generar_mensajes_motivacionales
                        generar_mensajes_motivacionales(perfil)
                    except Exception:
                        pass
                else:
                    # Mensaje de incentivo leve cuando no se completa (sólo para sueño y agua)
                    # Para no completado, incluir las horas en el título para que cada actualización cree un mensaje distinto
                    try:
                        if habito.tipo == 'sueno' and registro.cantidad < max(5, int(habito.meta_diaria)):
                            unidad = habito.unidad or 'h'
                            titulo_m = f'Atención al descanso: {registro.cantidad}{unidad}'
                            contenido_m = f'Veo que hoy dormiste {registro.cantidad} {unidad}. El descanso es clave para tu recuperación, intenta priorizarlo cuando puedas.'
                            mensaje_obj = crear_mensaje_si_no_duplicado(perfil, 'salud_mental', titulo_m, contenido_m, prioridad=2, ventana_horas=24)
                            if mensaje_obj:
                                mensaje_generado = {
                                    'id': mensaje_obj.id,
                                    'titulo': mensaje_obj.titulo,
                                    'contenido': mensaje_obj.contenido,
                                    'tipo': mensaje_obj.tipo,
                                    'prioridad': mensaje_obj.prioridad,
                                    'fecha_envio': mensaje_obj.fecha_envio.isoformat()
                                }
                    except Exception:
                        logger.exception('Error creando mensaje para hábito no completado')
            except Exception:
                # No bloquear el registro si falla la creación del mensaje
                logger.exception('Error creando mensaje motivacional para hábito')
            
            messages.success(request, mensaje)
            resp = {
                'success': True,
                'cantidad_actual': registro.cantidad,
                'meta': habito.meta_diaria,
                'completado': completado
            }
            if mensaje_generado:
                resp['mensaje_generado'] = mensaje_generado
            return JsonResponse(resp)
            
        except Exception as e:
            logger.error(f"Error registrando hábito: {e}")
            return JsonResponse({'error': 'Error registrando hábito'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@require_role('alumno')
def editar_habito_bueno(request, habito_id):
    """Editar un hábito bueno (solo propietario)"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        habito = get_object_or_404(HabitoBueno, id=habito_id, alumno=perfil)

        if request.method == 'POST':
            habito.nombre = request.POST.get('nombre', habito.nombre)
            habito.tipo = request.POST.get('tipo', habito.tipo)
            habito.meta_diaria = int(request.POST.get('meta_diaria', habito.meta_diaria))
            habito.unidad = request.POST.get('unidad', habito.unidad)
            habito.descripcion = request.POST.get('descripcion', habito.descripcion)
            habito.save()
            messages.success(request, 'Hábito actualizado correctamente')
            return redirect('alumno:habitos_buenos')

        context = {
            'perfil': perfil,
            'habito': habito,
            'tipos_habito': HabitoBueno.TIPO_CHOICES,
        }
        return render(request, 'alumno/editar_habito_bueno.html', context)

    except Exception as e:
        logger.error(f"Error editando hábito bueno: {e}")
        messages.error(request, 'Error actualizando hábito')
        return redirect('alumno:habitos_buenos')


@require_role('alumno')
def eliminar_habito_bueno(request, habito_id):
    """Soft-delete: marcar hábito como inactivo"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            habito = get_object_or_404(HabitoBueno, id=habito_id, alumno=perfil)
            habito.activo = False
            habito.save()
            messages.success(request, 'Hábito eliminado')
            return redirect('alumno:habitos_buenos')
        except Exception as e:
            logger.error(f"Error eliminando hábito bueno: {e}")
            messages.error(request, 'Error eliminando hábito')
            return redirect('alumno:habitos_buenos')

    return JsonResponse({'error': 'Método no permitido'}, status=405)

@require_role('alumno')
def habitos_malos(request):
    """Hábitos malos reales del alumno"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        if request.method == 'POST':
            # Crear nuevo hábito malo
            nombre = request.POST.get('nombre')
            tipo = request.POST.get('tipo')
            descripcion = request.POST.get('descripcion', '')
            
            HabitoMalo.objects.create(
                alumno=perfil,
                nombre=nombre,
                tipo=tipo,
                descripcion=descripcion
            )
            
            messages.success(request, f'Hábito "{nombre}" añadido para seguimiento')
            return redirect('alumno:habitos_malos')
        
        # Obtener hábitos malos reales
        habitos = HabitoMalo.objects.filter(
            alumno=perfil,
            activo=True
        ).order_by('-fecha_creacion')
        
        # Obtener registros recientes (7 días)
        from datetime import timedelta
        hace_7_dias = timezone.now().date() - timedelta(days=7)
        
        registros_recientes = RegistroHabitoMalo.objects.filter(
            habito__alumno=perfil,
            fecha__gte=hace_7_dias
        ).select_related('habito').order_by('-fecha_registro')[:10]
        
        # Estadísticas por hábito (frecuencia semanal)
        habitos_con_stats = []
        for habito in habitos:
            registros_semana = RegistroHabitoMalo.objects.filter(
                habito=habito,
                fecha__gte=hace_7_dias
            ).count()
            
            # Calcular tendencia (comparar con semana anterior)
            hace_14_dias = timezone.now().date() - timedelta(days=14)
            registros_semana_anterior = RegistroHabitoMalo.objects.filter(
                habito=habito,
                fecha__gte=hace_14_dias,
                fecha__lt=hace_7_dias
            ).count()
            
            tendencia = 'igual'
            if registros_semana > registros_semana_anterior:
                tendencia = 'subiendo'
            elif registros_semana < registros_semana_anterior:
                tendencia = 'bajando'
            
            habitos_con_stats.append({
                'habito': habito,
                'registros_semana': registros_semana,
                'registros_semana_anterior': registros_semana_anterior,
                'tendencia': tendencia
            })
        
        context = {
            'perfil': perfil,
            'habitos': habitos,
            'habitos_con_stats': habitos_con_stats,
            'registros_recientes': registros_recientes,
            'tipos_habito': HabitoMalo.TIPO_CHOICES,
            'intensidades': RegistroHabitoMalo.INTENSIDAD_CHOICES,
            'resumen_semanal': {
                'total_registros': sum(h['registros_semana'] for h in habitos_con_stats),
                'habitos_activos': len([h for h in habitos_con_stats if h['registros_semana'] > 0]),
                'tendencia_general': 'mejorando' if sum(h['registros_semana'] for h in habitos_con_stats) < sum(h['registros_semana_anterior'] for h in habitos_con_stats) else 'empeorando'
            },
        }
        
    except Exception as e:
        logger.error(f"Error en hábitos malos: {e}")
        context = {
            'perfil': None,
            'habitos': [],
            'habitos_con_stats': [],
            'registros_recientes': [],
            'tipos_habito': HabitoMalo.TIPO_CHOICES,
            'intensidades': RegistroHabitoMalo.INTENSIDAD_CHOICES,
            'error_message': 'Error cargando hábitos'
        }
    
    return render(request, 'alumno/habitos_malos.html', context)

@require_role('alumno')
def registrar_habito_malo(request, habito_id):
    """Registrar ocurrencia real de hábito malo"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            habito = get_object_or_404(HabitoMalo, id=habito_id, alumno=perfil)
            
            intensidad = int(request.POST.get('intensidad', 1))
            descripcion = request.POST.get('descripcion_situacion', '')
            reflexion = request.POST.get('reflexion', '')
            
            # Crear registro
            RegistroHabitoMalo.objects.create(
                habito=habito,
                intensidad=intensidad,
                descripcion_situacion=descripcion,
                reflexion=reflexion
            )
            
            # Mensaje según intensidad
            intensidad_texto = dict(RegistroHabitoMalo.INTENSIDAD_CHOICES)[intensidad]
            mensaje = f'Registro añadido: {habito.nombre} (Intensidad: {intensidad_texto})'
            
            if reflexion:
                mensaje += '. Excelente reflexión para mejorar.'
            else:
                mensaje += '. Reflexiona sobre cómo evitarlo la próxima vez.'
            
            messages.success(request, mensaje)
            # Crear un mensaje motivacional leve para reflexionar si la intensidad es moderada/alta
            try:
                if intensidad >= 2:
                    titulo_malo = f'Registro: {habito.nombre} (Intensidad: {intensidad_texto})'
                    contenido_malo = 'Gracias por registrar esto. Reflexionar sobre la situación te ayuda a mejorar. ¿Quieres hablar con tu entrenador para crear una estrategia?'
                    crear_mensaje_si_no_duplicado(perfil, 'salud_mental', titulo_malo, contenido_malo, prioridad=2, ventana_horas=12)
            except Exception:
                logger.exception('Error creando mensaje por hábito malo')

            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Error registrando hábito malo: {e}")
            return JsonResponse({'error': 'Error registrando hábito'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@require_role('alumno')
def editar_habito_malo(request, habito_id):
    """Editar un hábito malo (solo propietario)"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        habito = get_object_or_404(HabitoMalo, id=habito_id, alumno=perfil)

        if request.method == 'POST':
            habito.nombre = request.POST.get('nombre', habito.nombre)
            habito.tipo = request.POST.get('tipo', habito.tipo)
            habito.descripcion = request.POST.get('descripcion', habito.descripcion)
            habito.save()
            messages.success(request, 'Hábito actualizado correctamente')
            return redirect('alumno:habitos_malos')

        context = {
            'perfil': perfil,
            'habito': habito,
            'tipos_habito': HabitoMalo.TIPO_CHOICES,
        }
        return render(request, 'alumno/editar_habito_malo.html', context)

    except Exception as e:
        logger.error(f"Error editando hábito malo: {e}")
        messages.error(request, 'Error actualizando hábito')
        return redirect('alumno:habitos_malos')


@require_role('alumno')
def eliminar_habito_malo(request, habito_id):
    """Soft-delete: marcar hábito malo como inactivo"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            habito = get_object_or_404(HabitoMalo, id=habito_id, alumno=perfil)
            habito.activo = False
            habito.save()
            messages.success(request, 'Hábito eliminado')
            return redirect('alumno:habitos_malos')
        except Exception as e:
            logger.error(f"Error eliminando hábito malo: {e}")
            messages.error(request, 'Error eliminando hábito')
            return redirect('alumno:habitos_malos')

    return JsonResponse({'error': 'Método no permitido'}, status=405)

@require_role('alumno')
def mensajes_motivacionales(request):
    """Mensajes motivacionales reales con motor heurístico"""
    try:
        # Obtener perfil (tolerante a duplicados)
        perfil = PerfilAlumno.objects.filter(user=request.user).first()
        if not perfil:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)

        # Intentar generar mensajes persistidos vía motor (no es crítico si falla)
        try:
            MotorRecomendaciones.procesar_mensajes_alumno(perfil.id)
        except Exception as e:
            logger.debug(f"Motor recomendaciones falló al procesar alumno {getattr(perfil, 'id', None)}: {e}")

        # Traer mensajes persistidos (tanto nuevo modelo como legacy)
        from types import SimpleNamespace
        mensajes = []
        mensajes_qs = MensajeMotivacional.objects.filter(alumno__user=request.user).order_by('-prioridad', '-fecha_envio')[:200]
        # Legacy notifications table may be missing in some environments - skip it to avoid breaking the view
        notifs_qs = []

        for m in mensajes_qs:
            mensajes.append(SimpleNamespace(
                id=m.id,
                titulo=m.titulo,
                contenido=m.contenido,
                tipo=m.tipo,
                prioridad=m.prioridad,
                leido=m.leido,
                fecha_envio=m.fecha_envio,
                accion_sugerida=getattr(m, 'accion_sugerida', ''),
                get_tipo_display=m.get_tipo_display() if hasattr(m, 'get_tipo_display') else m.tipo,
                origen='mensaje'
            ))

        for n in notifs_qs:
            mensajes.append(SimpleNamespace(
                id=f"notif-{n.id}",
                titulo=n.titulo,
                contenido=n.mensaje,
                tipo='motivacion',
                prioridad=2,
                leido=n.leida,
                fecha_envio=n.fecha_envio,
                accion_sugerida='',
                get_tipo_display='Motivación',
                origen='legacy'
            ))

        # Si no hay mensajes persistidos, usar el analizador (no persistido) para mostrar sugerencias
        if not mensajes:
            try:
                sugerencias = MotorRecomendaciones.analizar_alumno(perfil)
                temp = []
                for idx, s in enumerate(sugerencias[:10]):
                    temp.append(SimpleNamespace(
                        id=f"temp-{idx}",
                        titulo=s.get('titulo'),
                        contenido=s.get('contenido'),
                        tipo=s.get('tipo'),
                        prioridad=s.get('prioridad', 2),
                        leido=False,
                        fecha_envio=timezone.now(),
                        accion_sugerida=s.get('accion_sugerida', ''),
                        get_tipo_display=s.get('tipo', '').capitalize(),
                        origen='sugerencia'
                    ))
                mensajes = temp
            except Exception as e:
                logger.debug(f"Error generando sugerencias temporales: {e}")

        # Ordenar mensajes por fecha_envio descendente
        mensajes.sort(key=lambda x: getattr(x, 'fecha_envio', timezone.now()), reverse=True)

        mensajes_no_leidos = [m for m in mensajes if not getattr(m, 'leido', False)]
        mensajes_leidos = [m for m in mensajes if getattr(m, 'leido', False)][:30]

        context = {
            'perfil': perfil,
            'mensajes_no_leidos': mensajes_no_leidos,
            'mensajes_leidos': mensajes_leidos,
            'mensajes': mensajes,
            'total_no_leidos': len(mensajes_no_leidos),
        }

    except Exception as e:
        logger.error(f"Error en mensajes motivacionales: {e}")
        context = {
            'perfil': None,
            'mensajes_no_leidos': [],
            'mensajes_leidos': [],
            'total_no_leidos': 0,
            'error_message': 'Error cargando mensajes'
        }

    return render(request, 'alumno/mensajes_motivacionales.html', context)

@require_role('alumno')
def marcar_mensaje_leido(request, mensaje_id):
    """Marcar mensaje real como leído"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            mensaje = get_object_or_404(MensajeMotivacional, id=mensaje_id, alumno=perfil)
            
            mensaje.leido = True
            mensaje.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Error marcando mensaje como leído: {e}")
            return JsonResponse({'error': 'Error procesando solicitud'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@require_role('alumno')
def obtener_mensajes_no_leidos(request):
    """Obtener contador real de mensajes no leídos"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        # Ejecutar motor de recomendaciones para generar nuevos mensajes
        try:
            MotorRecomendaciones.procesar_mensajes_alumno(perfil.id)
        except Exception as e:
            logger.error(f"Error en motor de recomendaciones: {e}")
        
        # Obtener mensajes no leídos tanto de MensajeMotivacional como de NotificacionMotivacional
        mensajes_qs = MensajeMotivacional.objects.filter(alumno=perfil, leido=False).order_by('-prioridad', '-fecha_envio')[:5]
        notifs_qs = []

        mensajes_data = []
        for mensaje in mensajes_qs:
            mensajes_data.append({
                'id': f'msg-{mensaje.id}',
                'titulo': mensaje.titulo,
                'contenido': mensaje.contenido[:100] + '...' if len(mensaje.contenido) > 100 else mensaje.contenido,
                'tipo': mensaje.tipo,
                'prioridad': mensaje.prioridad,
                'fecha': mensaje.fecha_envio.strftime('%H:%M')
            })
        for n in notifs_qs:
            mensajes_data.append({
                'id': f'notif-{n.id}',
                'titulo': n.titulo,
                'contenido': n.mensaje[:100] + '...' if len(n.mensaje) > 100 else n.mensaje,
                'tipo': 'motivacion',
                'prioridad': 2,
                'fecha': n.fecha_envio.strftime('%H:%M')
            })

        # Ordenar por hora (más reciente primero) usando la fecha real si está disponible
        mensajes_data.sort(key=lambda x: x.get('fecha', ''), reverse=True)

        return JsonResponse({
            'count': len(mensajes_data),
            'mensajes': mensajes_data
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo mensajes no leídos: {e}")
        return JsonResponse({
            'count': 0,
            'mensajes': [],
            'error': 'Error cargando mensajes'
        })


@require_role('alumno')
def api_mensajes(request):
    """API que devuelve la lista completa de mensajes (persistidos y legacy).
    Útil para el front-end cuando necesita refrescar o sincronizar la lista completa.
    """
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)

        # Intentar generar nuevos mensajes persistidos (no crítico)
        try:
            MotorRecomendaciones.procesar_mensajes_alumno(perfil.id)
        except Exception:
            pass

        mensajes_out = []

        mensajes_qs = MensajeMotivacional.objects.filter(alumno=perfil).order_by('-prioridad', '-fecha_envio')
        notifs_qs = []

        for m in mensajes_qs:
            mensajes_out.append({
                'id': f'msg-{m.id}',
                'orig_id': m.id,
                'origen': 'mensaje',
                'titulo': m.titulo,
                'contenido': m.contenido,
                'tipo': m.tipo,
                'prioridad': m.prioridad,
                'leido': bool(m.leido),
                'fecha_envio': m.fecha_envio.isoformat(),
                'accion_sugerida': getattr(m, 'accion_sugerida', '')
            })

        for n in notifs_qs:
            mensajes_out.append({
                'id': f'notif-{n.id}',
                'orig_id': n.id,
                'origen': 'legacy',
                'titulo': n.titulo,
                'contenido': n.mensaje,
                'tipo': 'motivacion',
                'prioridad': 2,
                'leido': bool(n.leida),
                'fecha_envio': n.fecha_envio.isoformat(),
                'accion_sugerida': ''
            })

        # ordenar por fecha_envio desc
        mensajes_out.sort(key=lambda x: x.get('fecha_envio') or '', reverse=True)

        return JsonResponse({'count': len(mensajes_out), 'mensajes': mensajes_out})

    except Exception as e:
        logger.error(f"Error en API mensajes: {e}")
        return JsonResponse({'count': 0, 'mensajes': [], 'error': 'Error cargando mensajes'})


@require_role('alumno')
def marcar_notificacion_leida(request, notif_id):
    """Marcar una NotificacionMotivacional legacy como leída (POST)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        notif = get_object_or_404(NotificacionMotivacional, id=notif_id, alumno=perfil)
        notif.leida = True
        notif.save()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error marcando notificación legacy como leída: {e}")
        return JsonResponse({'error': 'Error procesando solicitud'}, status=500)


@require_role('alumno')
@csrf_protect
@require_POST
def marcar_todos_mensajes_leidos(request):
    """Marca todos los MensajeMotivacional no leídos del alumno como leídos."""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        mensajes_no_leidos = MensajeMotivacional.objects.filter(alumno=perfil, leido=False)
        cantidad = mensajes_no_leidos.count()
        if cantidad > 0:
            mensajes_no_leidos.update(leido=True)
        return JsonResponse({'success': True, 'marcados': cantidad})
    except Exception as e:
        logger.exception('Error marcando todos los mensajes leídos')
        return JsonResponse({'error': 'Error marcando mensajes'}, status=500)

@require_role('alumno')
def ejercicios_disponibles(request):
    """Ejercicios reales disponibles en el gimnasio"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        # Obtener ejercicios reales de la base de datos
        ejercicios_db = Ejercicio.objects.all()
        
        # Organizar por categoría
        ejercicios = {}
        for ejercicio in ejercicios_db:
            categoria = ejercicio.categoria
            if categoria not in ejercicios:
                ejercicios[categoria] = []
            
            # Obtener estadísticas del alumno para este ejercicio
            registros = RegistroEjercicio.objects.filter(
                alumno=perfil,
                ejercicio=ejercicio
            )
            
            total_registros = registros.count()
            ultimo_registro = registros.order_by('-fecha_registro').first()
            
            ejercicios[categoria].append({
                'ejercicio': ejercicio,
                'total_registros': total_registros,
                'ultimo_registro': ultimo_registro,
                'realizado_recientemente': ultimo_registro and 
                    (timezone.now().date() - ultimo_registro.fecha).days <= 7
            })
        
        # Si no hay ejercicios en la BD, crear algunos por defecto
        if not ejercicios_db.exists():
            ejercicios = {
                'empuje': [],
                'traccion': [],
                'piernas': [],
                'core': []
            }
        
        context = {
            'perfil': perfil,
            'ejercicios': ejercicios,
            'categorias': Ejercicio.CATEGORIA_CHOICES,
        }
        
    except Exception as e:
        logger.error(f"Error en ejercicios disponibles: {e}")
        context = {
            'perfil': None,
            'ejercicios': {},
            'error_message': 'Error cargando ejercicios'
        }
    
    return render(request, 'alumno/ejercicios.html', context)

@require_role('alumno')
def detalle_ejercicio(request, ejercicio_id):
    """Detalle real del ejercicio con historial del alumno"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)
        
        if request.method == 'POST':
            series = int(request.POST.get('series', 1))
            repeticiones = int(request.POST.get('repeticiones', 1))
            peso_str = request.POST.get('peso', '')
            notas = request.POST.get('notas', '')
            
            # Convertir peso a decimal si se proporciona
            peso = None
            if peso_str:
                try:
                    peso = float(peso_str.replace('kg', '').replace(',', '.').strip())
                except ValueError:
                    peso = None
            
            # Crear registro
            RegistroEjercicio.objects.create(
                alumno=perfil,
                ejercicio=ejercicio,
                series=series,
                repeticiones=repeticiones,
                peso=peso,
                notas=notas
            )
            
            messages.success(request, f'Ejercicio registrado: {series} series x {repeticiones} reps' + 
                           (f' con {peso}kg' if peso else ''))
            return redirect('alumno:ejercicios')
        
        # Obtener historial del alumno para este ejercicio
        registros = RegistroEjercicio.objects.filter(
            alumno=perfil,
            ejercicio=ejercicio
        ).order_by('-fecha_registro')[:10]
        
        # Calcular estadísticas
        total_registros = registros.count()
        if registros:
            total_repeticiones = sum(r.series * r.repeticiones for r in registros)
            peso_maximo = max((r.peso for r in registros if r.peso), default=0)
            ultimo_registro = registros[0]
        else:
            total_repeticiones = 0
            peso_maximo = 0
            ultimo_registro = None
        
        # Repeticiones esta semana
        hace_7_dias = timezone.now().date() - timedelta(days=7)
        registros_semana = RegistroEjercicio.objects.filter(
            alumno=perfil,
            ejercicio=ejercicio,
            fecha__gte=hace_7_dias
        )
        repeticiones_semana = sum(r.series * r.repeticiones for r in registros_semana)
        
        context = {
            'ejercicio': ejercicio,
            'registros': registros,
            'total_registros': total_registros,
            'total_repeticiones': total_repeticiones,
            'peso_maximo': peso_maximo,
            'repeticiones_semana': repeticiones_semana,
            'ultimo_registro': ultimo_registro,
            'perfil': perfil,
        }
        
    except Exception as e:
        logger.error(f"Error en detalle ejercicio: {e}")
        context = {
            'ejercicio': None,
            'error_message': 'Error cargando ejercicio'
        }
    
    return render(request, 'alumno/detalle_ejercicio.html', context)

@require_role('alumno')
def metas(request):
    """Metas reales del alumno"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        
        if request.method == 'POST':
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            categoria = request.POST.get('categoria')
            fecha_objetivo = request.POST.get('fecha_objetivo')
            valor_objetivo = request.POST.get('valor_objetivo', '')
            
            from .models import Meta as MetaAlumno
            MetaAlumno.objects.create(
                alumno=perfil,
                titulo=titulo,
                descripcion=descripcion,
                categoria=categoria,
                fecha_objetivo=fecha_objetivo,
                valor_objetivo=valor_objetivo
            )
            
            messages.success(request, f'Meta "{titulo}" creada exitosamente')
            return redirect('alumno:metas')
        
        # Obtener metas reales
        from .models import Meta as MetaAlumno
        metas_activas = MetaAlumno.objects.filter(
            alumno=perfil,
            estado='activa'
        ).order_by('-fecha_creacion')
        
        # Calcular progreso para cada meta
        metas_con_progreso = []
        for meta in metas_activas:
            # Contar acciones
            total_acciones = meta.acciones.count()
            acciones_completadas = meta.acciones.filter(completada=True).count()
            
            # Calcular porcentaje de progreso
            if total_acciones > 0:
                progreso = (acciones_completadas / total_acciones) * 100
            else:
                progreso = 0
            
            # Días restantes
            dias_restantes = (meta.fecha_objetivo - timezone.now().date()).days
            
            metas_con_progreso.append({
                'meta': meta,
                'progreso': round(progreso, 1),
                'acciones_completadas': acciones_completadas,
                'total_acciones': total_acciones,
                'dias_restantes': dias_restantes
            })
        
        # Metas completadas recientes
        metas_completadas = MetaAlumno.objects.filter(
            alumno=perfil,
            estado='completada'
        ).order_by('-fecha_completada')[:5]
        
        context = {
            'perfil': perfil,
            'metas_con_progreso': metas_con_progreso,
            'metas_completadas': metas_completadas,
            'categorias': MetaAlumno.CATEGORIA_CHOICES,
        }
        
    except Exception as e:
        logger.error(f"Error en metas: {e}")
        from .models import Meta as MetaAlumno
        context = {
            'perfil': None,
            'metas_con_progreso': [],
            'metas_completadas': [],
            'categorias': MetaAlumno.CATEGORIA_CHOICES,
            'error_message': 'Error cargando metas'
        }
    
    return render(request, 'alumno/metas.html', context)

@require_role('alumno')
def detalle_meta(request, meta_id):
    """Detalle real de la meta con acciones y progreso"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        from .models import Meta as MetaAlumno
        meta = get_object_or_404(MetaAlumno, id=meta_id, alumno=perfil)
        
        if request.method == 'POST':
            if 'nueva_accion' in request.POST:
                descripcion = request.POST.get('descripcion_accion')
                AccionMeta.objects.create(
                    meta=meta,
                    descripcion=descripcion
                )
                messages.success(request, f'Acción "{descripcion}" añadida')
                
            elif 'registrar_progreso' in request.POST:
                valor = request.POST.get('valor_progreso')
                notas = request.POST.get('notas_progreso', '')
                
                ProgresoMeta.objects.create(
                    meta=meta,
                    valor_actual=valor,
                    notas=notas
                )
                messages.success(request, f'Progreso registrado: {valor}')
            
            return redirect('alumno:detalle_meta', meta_id=meta_id)
        
        # Obtener acciones de la meta
        acciones = meta.acciones.all().order_by('completada', '-fecha_creacion')
        
        # Obtener historial de progreso
        historial_progreso = meta.progresos.all().order_by('-fecha')[:10]
        
        # Calcular progreso
        total_acciones = acciones.count()
        acciones_completadas = acciones.filter(completada=True).count()
        
        if total_acciones > 0:
            porcentaje_progreso = (acciones_completadas / total_acciones) * 100
        else:
            porcentaje_progreso = 0
        
        # Días restantes
        dias_restantes = (meta.fecha_objetivo - timezone.now().date()).days
        
        # Último progreso registrado
        ultimo_progreso = historial_progreso.first() if historial_progreso else None
        
        context = {
            'meta': meta,
            'acciones': acciones,
            'historial_progreso': historial_progreso,
            'porcentaje_progreso': round(porcentaje_progreso, 1),
            'acciones_completadas': acciones_completadas,
            'total_acciones': total_acciones,
            'dias_restantes': dias_restantes,
            'ultimo_progreso': ultimo_progreso,
            'perfil': perfil,
        }
        
    except Exception as e:
        logger.error(f"Error en detalle meta: {e}")
        context = {
            'meta': None,
            'error_message': 'Error cargando meta'
        }
    
    return render(request, 'alumno/detalle_meta.html', context)

@require_role('alumno')
def completar_accion(request, accion_id):
    """Marcar acción real como completada"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            accion = get_object_or_404(AccionMeta, id=accion_id, meta__alumno=perfil)
            
            accion.completada = True
            accion.fecha_completada = timezone.now()
            accion.save()
            
            # Verificar si se completó la meta
            meta = accion.meta
            total_acciones = meta.acciones.count()
            acciones_completadas = meta.acciones.filter(completada=True).count()
            
            mensaje = 'Acción marcada como completada'
            
            if acciones_completadas == total_acciones and total_acciones > 0:
                meta.estado = 'completada'
                meta.fecha_completada = timezone.now()
                meta.save()
                mensaje += '. ¡Meta completada! 🎉'
            
            messages.success(request, mensaje)
            return JsonResponse({
                'success': True,
                'acciones_completadas': acciones_completadas,
                'total_acciones': total_acciones,
                'meta_completada': meta.estado == 'completada'
            })
            
        except Exception as e:
            logger.error(f"Error completando acción: {e}")
            return JsonResponse({'error': 'Error procesando solicitud'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@require_role('alumno')
def completar_meta(request, meta_id):
    """Marcar o desmarcar una meta como completada (toggle)"""
    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilAlumno, user=request.user)
            meta = get_object_or_404(Meta, id=meta_id, alumno=perfil)

            if meta.estado != 'completada':
                meta.estado = 'completada'
                meta.fecha_completada = timezone.now()
                meta.save()
                messages.success(request, 'Meta marcada como completada')
                # Crear mensaje motivacional al completar una meta
                try:
                    mensaje_obj = crear_mensaje_si_no_duplicado(
                        perfil,
                        'motivacion',
                        '🏆 ¡Meta completada!',
                        '¡Genial trabajo! Has completado una meta. Vas excelente, sigue así para mantener el progreso.',
                        prioridad=1,
                        ventana_horas=24
                    )
                    mensaje_generado = None
                    if mensaje_obj:
                        mensaje_generado = {
                            'id': mensaje_obj.id,
                            'titulo': mensaje_obj.titulo,
                            'contenido': mensaje_obj.contenido,
                            'tipo': mensaje_obj.tipo,
                            'prioridad': mensaje_obj.prioridad,
                            'fecha_envio': mensaje_obj.fecha_envio.isoformat()
                        }
                except Exception:
                    logger.exception('Error creando mensaje motivacional al completar meta')
                resp = {'success': True, 'meta_completada': True}
                if 'mensaje_generado' in locals() and mensaje_generado:
                    resp['mensaje_generado'] = mensaje_generado
                return JsonResponse(resp)
            else:
                meta.estado = 'activa'
                meta.fecha_completada = None
                meta.save()
                messages.success(request, 'Meta desmarcada como completada')
                return JsonResponse({'success': True, 'meta_completada': False})

        except Exception as e:
            logger.error(f"Error completando/desmarcando meta: {e}")
            return JsonResponse({'error': 'Error procesando solicitud'}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@require_role('alumno')
def editar_meta(request, meta_id):
    """Editar título/descripcion/categoria/fecha/valor de una meta"""
    perfil = get_object_or_404(PerfilAlumno, user=request.user)
    meta = get_object_or_404(Meta, id=meta_id, alumno=perfil)

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        categoria = request.POST.get('categoria')
        fecha_objetivo_raw = request.POST.get('fecha_objetivo')
        fecha_objetivo = None
        if fecha_objetivo_raw:
            try:
                fecha_objetivo = datetime.strptime(fecha_objetivo_raw, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido. Use YYYY-MM-DD')
                return redirect('alumno:editar_meta', meta_id=meta.id)
        valor_objetivo = request.POST.get('valor_objetivo', '')

        meta.titulo = titulo
        meta.descripcion = descripcion
        meta.categoria = categoria
        # Only update fecha_objetivo if a valid value was provided; otherwise keep existing
        if fecha_objetivo is not None:
            meta.fecha_objetivo = fecha_objetivo
        meta.valor_objetivo = valor_objetivo
        meta.save()

        messages.success(request, 'Meta actualizada correctamente')
        return redirect('alumno:detalle_meta', meta_id=meta.id)

    # GET -> render form
    context = {
        'meta': meta,
        'categorias': Meta.CATEGORIA_CHOICES,
        'perfil': perfil,
    }
    return render(request, 'alumno/editar_meta.html', context)


@require_role('alumno')
def eliminar_meta(request, meta_id):
    """Soft-delete: marcar meta como cancelada (no la borra, queda en historial)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    perfil = get_object_or_404(PerfilAlumno, user=request.user)
    meta = get_object_or_404(Meta, id=meta_id, alumno=perfil)

    try:
        # Soft delete by setting estado to 'cancelada'
        meta.estado = 'cancelada'
        meta.save()
        messages.success(request, 'Meta eliminada (cancelada) correctamente')
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error eliminando meta: {e}")
        return JsonResponse({'error': 'Error procesando solicitud'}, status=500)


@require_role('alumno')
def export_metas_csv(request):
    """Exportar todas las metas del alumno a CSV"""
    import csv
    perfil = get_object_or_404(PerfilAlumno, user=request.user)
    metas = Meta.objects.filter(alumno=perfil).order_by('-fecha_creacion')

    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mis_metas.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Titulo', 'Descripcion', 'Categoria', 'Fecha Objetivo', 'Valor Objetivo', 'Estado', 'Fecha Creacion', 'Fecha Completada', 'Acciones', 'Historial Progreso'])
    for m in metas:
        # Acciones: list as semicolon-separated items: desc|completada|fecha_completada
        acciones = []
        for a in m.acciones.all().order_by('fecha_creacion'):
            fecha_comp = a.fecha_completada.isoformat() if a.fecha_completada else ''
            acciones.append(f"{(a.descripcion or '').replace(';',',')}|{a.completada}|{fecha_comp}")

        # Historial de progreso: semicolon-separated fecha:value:notas
        progresos = []
        for p in m.progresos.all().order_by('-fecha')[:20]:
            notas = (p.notas or '').replace(';', ',')
            progresos.append(f"{p.fecha.isoformat()}|{(p.valor_actual or '').replace(';',',')}|{notas}")

        writer.writerow([
            m.id,
            m.titulo,
            (m.descripcion or '').replace('\n', ' '),
            m.get_categoria_display(),
            m.fecha_objetivo.isoformat() if m.fecha_objetivo else '',
            m.valor_objetivo,
            m.get_estado_display(),
            m.fecha_creacion.isoformat() if m.fecha_creacion else '',
            m.fecha_completada.isoformat() if m.fecha_completada else '',
            ';'.join(acciones),
            ';'.join(progresos)
        ])

    return response


@require_role('alumno')
def export_metas_pdf(request):
    """Intentar generar PDF con ReportLab; si no está, devolver error instructivo"""
    perfil = get_object_or_404(PerfilAlumno, user=request.user)
    metas = Meta.objects.filter(alumno=perfil).order_by('-fecha_creacion')

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        messages.error(request, 'Generación de PDF requiere instalar `reportlab`. Ejecuta: pip install reportlab')
        return redirect('alumno:metas')

    from django.http import HttpResponse
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="mis_metas.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 40
    p.setFont('Helvetica-Bold', 14)
    p.drawString(40, y, f'Mis Metas - {request.user.get_full_name()}')
    y -= 30
    p.setFont('Helvetica', 10)

    for m in metas:
        if y < 80:
            p.showPage()
            y = height - 40
            p.setFont('Helvetica', 10)
        p.drawString(40, y, f'[{m.id}] {m.titulo} ({m.get_categoria_display()}) - {m.get_estado_display()}')
        y -= 14
        fecha_obj = m.fecha_objetivo.isoformat() if m.fecha_objetivo else ''
        p.drawString(60, y, f'Objetivo: {m.valor_objetivo}  Fecha objetivo: {fecha_obj}')
        y -= 12
        desc = (m.descripcion or '').replace('\n', ' ')
        # wrap description roughly
        maxlen = 100
        for i in range(0, len(desc), maxlen):
            if y < 80:
                p.showPage()
                y = height - 40
                p.setFont('Helvetica', 10)
            p.drawString(60, y, desc[i:i+maxlen])
            y -= 12

        # Actions
        acciones = list(m.acciones.all().order_by('fecha_creacion'))
        if acciones:
            if y < 100:
                p.showPage(); y = height - 40; p.setFont('Helvetica', 10)
            p.setFont('Helvetica-Bold', 11)
            p.drawString(60, y, 'Acciones:')
            p.setFont('Helvetica', 10)
            y -= 14
            for a in acciones:
                linea = f"- {a.descripcion} [{'OK' if a.completada else 'pendiente'}]"
                if a.fecha_completada:
                    linea += f" (completada: {a.fecha_completada.date().isoformat()})"
                # wrap
                for i in range(0, len(linea), 80):
                    if y < 80:
                        p.showPage(); y = height - 40; p.setFont('Helvetica', 10)
                    p.drawString(70, y, linea[i:i+80])
                    y -= 12

        # Progresos (últimos 10)
        progresos = list(m.progresos.all().order_by('-fecha')[:10])
        if progresos:
            if y < 100:
                p.showPage(); y = height - 40; p.setFont('Helvetica', 10)
            p.setFont('Helvetica-Bold', 11)
            p.drawString(60, y, 'Historial de progreso:')
            p.setFont('Helvetica', 10)
            y -= 14
            for pr in progresos:
                linea = f"{pr.fecha.isoformat()} - {pr.valor_actual}"
                if pr.notas:
                    linea += f" — {pr.notas}"
                for i in range(0, len(linea), 100):
                    if y < 80:
                        p.showPage(); y = height - 40; p.setFont('Helvetica', 10)
                    p.drawString(70, y, linea[i:i+100])
                    y -= 12

        y -= 8

    p.showPage()
    p.save()
    return response

@require_role('alumno')
def sincronizar_usuario_admin(request):
    """Sincroniza el usuario actual con la tabla del admin"""
    from django.db import connection
    from django.http import HttpResponse
    
    try:
        with connection.cursor() as cursor:
            # Buscar si ya existe el usuario
            cursor.execute("""
                SELECT id FROM admin_gym_cliente WHERE user_id = %s
            """, [request.user.id])
            
            cliente_result = cursor.fetchone()
            
            if not cliente_result:
                # Buscar por nombre o email similar
                cursor.execute("""
                    SELECT id, nombre, email FROM admin_gym_cliente 
                    WHERE nombre LIKE %s OR email = %s
                """, [f"%{request.user.get_full_name()}%", request.user.email])
                
                posibles_matches = cursor.fetchall()
                
                if posibles_matches:
                    # Tomar el primer match y actualizar con user_id
                    cliente_id = posibles_matches[0][0]
                    cursor.execute("""
                        UPDATE admin_gym_cliente SET user_id = %s WHERE id = %s
                    """, [request.user.id, cliente_id])
                    
                    return HttpResponse(f"Usuario sincronizado exitosamente con cliente ID: {cliente_id}")
                else:
                    return HttpResponse("No se encontró un cliente matching en la tabla admin")
            else:
                return HttpResponse(f"Usuario ya está sincronizado con cliente ID: {cliente_result[0]}")
                
    except Exception as e:
        return HttpResponse(f"Error: {e}")

@require_role('alumno')
@login_required
def eventos_disponibles(request):
    """Vista para mostrar eventos disponibles a los alumnos"""
    return render(request, 'alumno/eventos.html')

def debug_visitas_hoy(request):
    """Debug específico para visitas de hoy"""
    from django.db import connection
    from django.http import HttpResponse
    from datetime import datetime
    
    debug_info = []
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    try:
        with connection.cursor() as cursor:
            debug_info.append(f"Usuario actual: {request.user.username} (ID: {request.user.id})")
            debug_info.append(f"Email: {request.user.email}")
            debug_info.append(f"Nombre completo: {request.user.get_full_name()}")
            debug_info.append(f"Fecha de hoy: {hoy}")
            debug_info.append("")
            
            # Buscar cliente por user_id
            cursor.execute("SELECT id, nombre, email FROM admin_gym_cliente WHERE user_id = %s", [request.user.id])
            cliente_result = cursor.fetchone()
            
            if cliente_result:
                cliente_id = cliente_result[0]
                debug_info.append(f"Cliente encontrado por user_id: ID={cliente_id}, Nombre={cliente_result[1]}, Email={cliente_result[2]}")
            else:
                debug_info.append("No se encontró cliente por user_id")
                
                # Buscar por email
                cursor.execute("SELECT id, nombre, email FROM admin_gym_cliente WHERE email = %s", [request.user.email])
                email_result = cursor.fetchone()
                if email_result:
                    debug_info.append(f"Cliente encontrado por email: ID={email_result[0]}, Nombre={email_result[1]}")
                    cliente_id = email_result[0]
                else:
                    # Buscar por nombre similar
                    cursor.execute("SELECT id, nombre, email FROM admin_gym_cliente WHERE nombre LIKE %s", [f"%{request.user.get_full_name()}%"])
                    nombre_result = cursor.fetchone()
                    if nombre_result:
                        debug_info.append(f"Cliente encontrado por nombre: ID={nombre_result[0]}, Nombre={nombre_result[1]}")
                        cliente_id = nombre_result[0]
                    else:
                        debug_info.append("No se encontró cliente por ningún método")
                        return HttpResponse("<br>".join(debug_info))
            
            debug_info.append("")
            debug_info.append(f"Usando cliente_id: {cliente_id}")
            
            # Verificar estructura de tabla primero
            cursor.execute("SHOW COLUMNS FROM admin_gym_asistencia")
            columnas = cursor.fetchall()
            debug_info.append("Columnas de admin_gym_asistencia:")
            for col in columnas:
                debug_info.append(f"  - {col[0]} ({col[1]})")
            debug_info.append("")
            
            # Buscar la columna correcta de fecha
            fecha_col = None
            tipo_col = None
            for col in columnas:
                if 'fecha' in col[0].lower():
                    fecha_col = col[0]
                if 'tipo' in col[0].lower():
                    tipo_col = col[0]
            
            debug_info.append(f"Columna de fecha detectada: {fecha_col}")
            debug_info.append(f"Columna de tipo detectada: {tipo_col}")
            debug_info.append("")
            
            if fecha_col:
                # Total de asistencias
                cursor.execute(f"SELECT COUNT(*) FROM admin_gym_asistencia WHERE cliente_id = %s", [cliente_id])
                total = cursor.fetchone()[0]
                debug_info.append(f"Total asistencias históricas: {total}")
                
                # Últimas 5 asistencias
                if tipo_col:
                    cursor.execute(f"""
                        SELECT {fecha_col}, {tipo_col} FROM admin_gym_asistencia 
                        WHERE cliente_id = %s ORDER BY {fecha_col} DESC LIMIT 5
                    """, [cliente_id])
                else:
                    cursor.execute(f"""
                        SELECT {fecha_col} FROM admin_gym_asistencia 
                        WHERE cliente_id = %s ORDER BY {fecha_col} DESC LIMIT 5
                    """, [cliente_id])
                
                ultimas = cursor.fetchall()
                debug_info.append("Últimas 5 asistencias:")
                for asistencia in ultimas:
                    if tipo_col:
                        debug_info.append(f"  - {asistencia[0]} ({asistencia[1]})")
                    else:
                        debug_info.append(f"  - {asistencia[0]}")
                
                # Verificar asistencias de hoy
                cursor.execute(f"""
                    SELECT COUNT(*) FROM admin_gym_asistencia 
                    WHERE cliente_id = %s AND DATE({fecha_col}) = %s
                """, [cliente_id, hoy])
                
                asistencias_hoy = cursor.fetchone()[0]
                debug_info.append(f"Asistencias de hoy ({hoy}): {asistencias_hoy}")
            else:
                debug_info.append("No se pudo detectar la columna de fecha")
                
    except Exception as e:
        debug_info.append(f"Error: {e}")
    
    return HttpResponse("<br>".join(debug_info))

@require_role('alumno')
def debug_admin_data(request):
    """Vista de debug para verificar datos del admin"""
    from django.db import connection
    from django.http import HttpResponse
    
    debug_info = []
    
    try:
        with connection.cursor() as cursor:
            # Verificar si existe el usuario en admin_gym_cliente
            cursor.execute("""
                SELECT id, nombre, email, rut FROM admin_gym_cliente WHERE user_id = %s
            """, [request.user.id])
            
            cliente_result = cursor.fetchone()
            if cliente_result:
                debug_info.append(f"Cliente encontrado: ID={cliente_result[0]}, Nombre={cliente_result[1]}, Email={cliente_result[2]}, RUT={cliente_result[3]}")
                
                cliente_id = cliente_result[0]
                
                # Verificar asistencias
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_gym_asistencia WHERE cliente_id = %s
                """, [cliente_id])
                
                count_result = cursor.fetchone()
                debug_info.append(f"Total asistencias: {count_result[0] if count_result else 0}")
                
                # Últimas 5 asistencias
                cursor.execute("""
                    SELECT fecha FROM admin_gym_asistencia 
                    WHERE cliente_id = %s ORDER BY fecha DESC LIMIT 5
                """, [cliente_id])
                
                asistencias = cursor.fetchall()
                debug_info.append(f"Últimas asistencias: {len(asistencias)}")
                for i, asistencia in enumerate(asistencias):
                    debug_info.append(f"  {i+1}. {asistencia[0]}")
                
                # Debug adicional - verificar estructura de tabla
                cursor.execute("SHOW COLUMNS FROM admin_gym_asistencia")
                columnas = cursor.fetchall()
                debug_info.append(f"Columnas de admin_gym_asistencia:")
                for col in columnas:
                    debug_info.append(f"  - {col[0]} ({col[1]})")
                    
            else:
                debug_info.append(f"No se encontró cliente para user_id: {request.user.id}")
                
                # Verificar todos los clientes
                cursor.execute("SELECT id, user_id, nombre, email FROM admin_gym_cliente LIMIT 10")
                clientes = cursor.fetchall()
                debug_info.append(f"Primeros 10 clientes en la tabla:")
                for cliente in clientes:
                    debug_info.append(f"  ID={cliente[0]}, user_id={cliente[1]}, nombre={cliente[2]}, email={cliente[3]}")
                
                # Verificar si hay registros de asistencia en general
                cursor.execute("SELECT COUNT(*) FROM admin_gym_asistencia")
                total_asistencias = cursor.fetchone()[0]
                debug_info.append(f"Total de asistencias en la tabla: {total_asistencias}")
                    
    except Exception as e:
        debug_info.append(f"Error: {e}")
    
    return HttpResponse("<br>".join(debug_info))

@require_role('alumno')
def perfil_alumno(request):
    """Perfil real del alumno desde la base de datos"""
    try:
        perfil = get_object_or_404(PerfilAlumno, user=request.user)
        info_alumno = InformacionAlumno.objects.filter(user=request.user).first()
        
        if request.method == 'POST':
            # Crear o actualizar información del alumno
            if not info_alumno:
                info_alumno = InformacionAlumno(user=request.user)
            
            info_alumno.nombre_completo = request.POST.get('nombre_completo')
            info_alumno.fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
            info_alumno.genero = request.POST.get('genero')
            info_alumno.telefono = request.POST.get('telefono', '')
            info_alumno.direccion = request.POST.get('direccion', '')
            info_alumno.altura = request.POST.get('altura') or None
            info_alumno.peso_actual = request.POST.get('peso_actual') or None
            info_alumno.porcentaje_grasa = request.POST.get('porcentaje_grasa') or None
            info_alumno.informacion_completa = True
            
            info_alumno.save()
            
            messages.success(request, 'Información actualizada exitosamente')
            return redirect('alumno:perfil')
        
        # Obtener total de visitas
        total_visitas = AccesoGimnasio.objects.filter(
            alumno=perfil,
            tipo_acceso='entrada'
        ).count() if perfil else 0
        
        context = {
            'perfil': perfil,
            'info_alumno': info_alumno,
            'user': request.user,
            'total_visitas': total_visitas,
        }
        
    except Exception as e:
        logger.error(f"Error en perfil alumno: {e}")
        context = {
            'perfil': None,
            'user': request.user,
            'error_message': 'Error conectando con la base de datos'
        }
    
    return render(request, 'alumno/perfil.html', context)

@login_required
def rutinas_nuevo(request):
    """Vista nueva para el sistema de rutinas del alumno"""
    return render(request, 'alumno/rutinas.html')

@login_required
def crear_rutina_view(request):
    """Vista para mostrar el formulario de creación de rutina"""
    ejercicios = Ejercicio.objects.all()
    return render(request, 'alumno/crear_rutina.html', {'ejercicios': ejercicios})

@login_required
def editar_rutina_view(request, rutina_id):
    """Vista para editar una rutina existente"""
    rutina = get_object_or_404(RutinaAlumno, id=rutina_id, alumno__user=request.user)
    ejercicios = Ejercicio.objects.all()
    return render(request, 'alumno/editar_rutina.html', {
        'rutina': rutina,
        'ejercicios': ejercicios
    })

@login_required
def ejecutar_rutina_view(request, rutina_id):
    """Vista para ejecutar/realizar una rutina"""
    rutina = get_object_or_404(RutinaAlumno, id=rutina_id, alumno__user=request.user)
    ejercicios_rutina = rutina.ejercicios.all().order_by('orden')
    return render(request, 'alumno/ejecutar_rutina.html', {
        'rutina': rutina,
        'ejercicios': ejercicios_rutina
    })


@login_required
@require_POST
def crear_rutina(request):
    """
    Endpoint POST JSON para crear una rutina personalizada.
    
    Body esperado:
    {
      "nombre": "Mi Rutina",
      "objetivo": "fuerza",
      "descripcion": "...",
      "dia": "lunes",
      "ejercicios": [
        {"nombre": "Flexiones", "series": 3, "reps": "10-12", "peso": 20, "descanso": 60}
      ]
    }
    
    Respuestas:
    - 201: {"ok": true, "id": <rutina_id>, "redirect": "/alumno/rutinas/"}
    - 400: {"ok": false, "errors": {campo: [msg, ...]}}
    """
    try:
        # Parsear JSON
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return JsonResponse(
                {"ok": False, "errors": {"_form": [f"JSON inválido: {str(e)}"]}},
                status=400
            )
        
        # Validar payload
        is_valid, result = validate_payload(data)
        if not is_valid:
            return JsonResponse(
                {"ok": False, "errors": result},
                status=400
            )
        
        # Obtener perfil del alumno
        try:
            perfil_alumno = PerfilAlumno.objects.get(user=request.user)
        except PerfilAlumno.DoesNotExist:
            return JsonResponse(
                {"ok": False, "errors": {"_form": ["Perfil de alumno no encontrado."]}},
                status=400
            )
        
        # Crear rutina y ejercicios en transacción atómica
        with transaction.atomic():
            rutina = RutinaAlumno.objects.create(
                alumno=perfil_alumno,
                nombre=result["nombre"],
                objetivo=result["objetivo"],
                descripcion=result["descripcion"],
                tipo="personal",
                dia_asignado=result["dia"] if result["dia"] else None,
                activa=True,
            )
            
            # Crear ejercicios
            ejercicios_objs = []
            for idx, ej_data in enumerate(result["ejercicios"], 1):
                ejercicios_objs.append(
                    EjercicioRutinaAlumno(
                        rutina=rutina,
                        nombre=ej_data["nombre"],
                        series=ej_data["series"],
                        repeticiones=ej_data["reps"],
                        peso=ej_data["peso"] if ej_data["peso"] else "",
                        descanso=ej_data["descanso"],
                        orden=idx,
                    )
                )
            
            EjercicioRutinaAlumno.objects.bulk_create(ejercicios_objs)
        
        # Retornar respuesta exitosa
        return JsonResponse(
            {
                "ok": True,
                "id": rutina.id,
                "redirect": reverse("alumno:rutinas"),
            },
            status=201
        )
    
    except Exception as e:
        logger.error(f"Error en crear_rutina: {e}", exc_info=True)
        return JsonResponse(
            {"ok": False, "errors": {"_form": ["Error interno del servidor."]}},
            status=500
        )
