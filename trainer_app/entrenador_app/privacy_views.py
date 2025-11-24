from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.serializers import serialize
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def privacy_center(request):
    """Centro de privacidad con información sobre el manejo de datos"""
    context = {
        'user': request.user,
        'last_login': request.user.last_login,
        'date_joined': request.user.date_joined,
    }
    return render(request, 'privacy/privacy_center.html', context)

@login_required
def change_password(request):
    """Cambio de contraseña del usuario"""
    # Determinar a qué perfil redirigir según el rol
    def _profile_redirect(user):
        # Entrenadores usan la ruta 'perfil' en root; alumnos usan el namespace 'alumno:perfil'
        try:
            # Evitar import circular: chequear banderas del user
            if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
                return redirect('perfil')
            else:
                return redirect('alumno:perfil')
        except Exception:
            return redirect('perfil')

    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        # Validaciones
        if not request.user.check_password(old_password):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return _profile_redirect(request.user)

        if new_password1 != new_password2:
            messages.error(request, 'Las nuevas contraseñas no coinciden.')
            return _profile_redirect(request.user)

        if len(new_password1) < 8:
            messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
            return _profile_redirect(request.user)

        try:
            # Cambiar contraseña
            request.user.set_password(new_password1)
            request.user.save()

            # Mantener la sesión activa después del cambio
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Contraseña actualizada exitosamente.')
            logger.info(f"Usuario {request.user.username} cambió su contraseña")

        except Exception as e:
            logger.error(f"Error cambiando contraseña para {request.user.username}: {e}")
            messages.error(request, 'Error al cambiar la contraseña. Inténtalo de nuevo.')

    return _profile_redirect(request.user)

@login_required
def download_data(request):
    """Descarga de datos personales (ARCO) en formato JSON"""
    try:
        user_data = {
            'informacion_personal': {
                'username': request.user.username,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'date_joined': request.user.date_joined.isoformat(),
                'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
                'is_staff': request.user.is_staff,
            },
            'fecha_exportacion': timezone.now().isoformat(),
            'version': '1.0'
        }
        
        # Agregar datos específicos según el tipo de usuario
        if request.user.is_staff:
            # Datos del entrenador
            from entrenador.models import AsistenciaEntrenador, EventoCalendario
            
            asistencias = AsistenciaEntrenador.objects.filter(entrenador=request.user)
            eventos = EventoCalendario.objects.filter(entrenador=request.user)
            
            user_data['datos_entrenador'] = {
                'asistencias': [
                    {
                        'fecha': a.fecha.isoformat(),
                        'hora_entrada': a.hora_entrada.isoformat() if a.hora_entrada else None,
                        'hora_salida': a.hora_salida.isoformat() if a.hora_salida else None,
                    } for a in asistencias
                ],
                'eventos_calendario': [
                    {
                        'titulo': e.titulo,
                        'descripcion': e.descripcion,
                        'fecha_inicio': e.fecha_inicio.isoformat(),
                        'fecha_fin': e.fecha_fin.isoformat() if e.fecha_fin else None,
                        'tipo': e.tipo,
                    } for e in eventos
                ]
            }
        else:
            # Datos del alumno
            try:
                from alumno.models import (
                    PerfilAlumno, ProgresoFisico, AccesoGimnasio, 
                    RegistroEjercicio, RegistroHabitoBueno, RegistroHabitoMalo
                )
                
                perfil = PerfilAlumno.objects.get(user=request.user)
                progresos = ProgresoFisico.objects.filter(alumno=perfil)
                accesos = AccesoGimnasio.objects.filter(alumno=perfil)
                ejercicios = RegistroEjercicio.objects.filter(alumno=perfil)
                habitos_buenos = RegistroHabitoBueno.objects.filter(alumno=perfil)
                habitos_malos = RegistroHabitoMalo.objects.filter(alumno=perfil)
                
                user_data['datos_alumno'] = {
                    'perfil': {
                        'descripcion': perfil.descripcion,
                        'instagram': perfil.instagram,
                        'facebook': perfil.facebook,
                        'estado': perfil.estado,
                        'fecha_creacion': perfil.fecha_creacion.isoformat(),
                    },
                    'progreso_fisico': [
                        {
                            'fecha': p.fecha.isoformat(),
                            'peso': float(p.peso) if p.peso else None,
                            'altura': float(p.altura) if p.altura else None,
                            'grasa_corporal': float(p.grasa_corporal) if p.grasa_corporal else None,
                            'masa_muscular': float(p.masa_muscular) if p.masa_muscular else None,
                        } for p in progresos
                    ],
                    'accesos_gimnasio': [
                        {
                            'fecha_acceso': a.fecha_acceso.isoformat(),
                            'tipo_acceso': a.tipo_acceso,
                        } for a in accesos
                    ],
                    'ejercicios': [
                        {
                            'fecha_registro': e.fecha_registro.isoformat(),
                            'ejercicio': e.ejercicio.nombre if e.ejercicio else None,
                            'series': e.series,
                            'repeticiones': e.repeticiones,
                            'peso': float(e.peso) if e.peso else None,
                        } for e in ejercicios
                    ],
                    'habitos_buenos': [
                        {
                            'fecha_registro': h.fecha_registro.isoformat(),
                            'habito': h.habito.nombre if h.habito else None,
                            'completado': h.completado,
                        } for h in habitos_buenos
                    ],
                    'habitos_malos': [
                        {
                            'fecha_registro': h.fecha_registro.isoformat(),
                            'habito': h.habito.nombre if h.habito else None,
                            'ocurrencias': h.ocurrencias,
                        } for h in habitos_malos
                    ]
                }
            except Exception as e:
                logger.warning(f"No se pudieron obtener datos de alumno para {request.user.username}: {e}")
                user_data['datos_alumno'] = {'error': 'No se encontraron datos de alumno'}
        
        # Crear respuesta HTTP con el archivo JSON
        response = HttpResponse(
            json.dumps(user_data, indent=2, ensure_ascii=False),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="mis_datos_fitspace_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.json"'
        
        logger.info(f"Usuario {request.user.username} descargó sus datos ARCO")
        return response
        
    except Exception as e:
        logger.error(f"Error generando datos ARCO para {request.user.username}: {e}")
        messages.error(request, 'Error al generar el archivo de datos. Inténtalo de nuevo.')
        return redirect('perfil')

@login_required
@require_POST
def delete_account(request):
    """Solicitud de eliminación de cuenta"""
    try:
        username = request.user.username
        user_id = request.user.id
        
        # Registrar la solicitud de eliminación
        logger.warning(f"SOLICITUD DE ELIMINACIÓN DE CUENTA - Usuario: {username} (ID: {user_id})")
        
        # En un entorno real, aquí se marcaría la cuenta para eliminación
        # y se notificaría al administrador, pero no se eliminaría inmediatamente
        
        # Por ahora, solo desactivamos la cuenta
        request.user.is_active = False
        request.user.save()
        
        # Cerrar sesión
        from django.contrib.auth import logout
        logout(request)
        
        messages.success(request, 
            'Tu solicitud de eliminación de cuenta ha sido procesada. '
            'Tu cuenta ha sido desactivada y será eliminada permanentemente en 30 días. '
            'Si cambias de opinión, contacta al administrador antes de ese plazo.'
        )
        
        return redirect('login')
        
    except Exception as e:
        logger.error(f"Error procesando eliminación de cuenta para {request.user.username}: {e}")
        messages.error(request, 'Error al procesar la solicitud. Inténtalo de nuevo.')
        return redirect('perfil')