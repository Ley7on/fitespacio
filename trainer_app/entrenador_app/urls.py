from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.conf import settings
from pathlib import Path
from entrenador.views import (
    dashboard, 
    alumnos_list, 
    alumno_detalle, 
    calendario, 
    rutinas_plantillas, 
    perfil, actualizar_perfil,
    eventos_calendario,
    crear_evento,
    editar_evento,
    eliminar_evento,
    inscribir_sesion,
    rechazar_sesion,
    obtener_alumnos,
    asignar_rutina,
    obtener_progreso_alumno,
    obtener_rutinas,
    test_alumnos_page,
    api_asignar_rutina_alumno,
    api_eliminar_rutina_alumno,
    editar_rutina_alumno
)
from entrenador.views_rutinas import crear_rutina, editar_rutina, eliminar_rutina, exportar_rutinas_csv, obtener_alumnos as obtener_alumnos_rutinas
from entrenador.test_views import test_alumnos
from entrenador.views_rutinas_personalizadas import (
    crear_rutina_personalizada, 
    obtener_rutinas_asignadas_alumno,
    obtener_rutinas_personales_alumno,
    obtener_calendario_semanal_alumno
)
from entrenador_app.simple_user_creation import crear_usuario_simple, reenviar_credenciales_simple, listar_usuarios


# Sirve el Service Worker en la raíz con scope "/"
def service_worker(request):
    sw_path = Path(settings.PWA_SERVICE_WORKER_PATH)
    content = sw_path.read_text(encoding='utf-8')
    resp = HttpResponse(content, content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    return resp

from .auth_views import login_view, logout_view, profile_view, debug_rut_view, public_root, root_redirect, catchall_redirect
from .privacy_views import privacy_center, change_password, download_data, delete_account
from entrenador.shift_views import toggle_shift, get_shift_status

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Importar rutas de entrenador PRIMERO (todas las rutas /api/rutinas/*)
    path('', include('entrenador.urls')),
    
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('debug-rut/', debug_rut_view, name='debug_rut'),
    
    # Privacy routes
    path('privacy/', privacy_center, name='privacy_center'),
    path('change-password/', change_password, name='change_password'),
    path('download-data/', download_data, name='download_data'),
    path('delete-account/', delete_account, name='delete_account'),
    
    # Entrenador routes
    path('dashboard/', dashboard, name='dashboard'),
    path('alumnos/', alumnos_list, name='alumnos_list'),
    path('alumnos/<int:alumno_id>/', alumno_detalle, name='alumno_detalle'),
    path('calendario/', calendario, name='calendario'),
    path('rutinas-plantillas/', rutinas_plantillas, name='rutinas_plantillas'),
    path('perfil/', perfil, name='perfil'),
    path('actualizar-perfil/', actualizar_perfil, name='actualizar_perfil'),
    
    # Calendario CRUD
    path('api/eventos/', eventos_calendario, name='eventos_calendario'),
    path('api/eventos/crear/', crear_evento, name='crear_evento'),
    path('api/eventos/<int:evento_id>/editar/', editar_evento, name='editar_evento'),
    path('api/eventos/<int:evento_id>/eliminar/', eliminar_evento, name='eliminar_evento'),
    # Inscripción de alumnos a sesiones
    path('api/sesiones/<int:sesion_id>/inscribir/', inscribir_sesion, name='inscribir_sesion'),
    path('api/sesiones/<int:sesion_id>/rechazar/', rechazar_sesion, name='rechazar_sesion'),
    
    path('asignar-rutina/', asignar_rutina, name='asignar_rutina'),
    
    # Alumno app
    path('alumno/', include('alumno.urls')),



    # APIs necesarias
    path('api/alumnos/', obtener_alumnos_rutinas, name='obtener_alumnos'),
    path('api/alumnos/<int:alumno_id>/progreso/', obtener_progreso_alumno, name='obtener_progreso_alumno'),
    
    # Endpoint de prueba
    path('api/test-alumnos/', test_alumnos, name='test_alumnos'),
    path('test-alumnos-page/', test_alumnos_page, name='test_alumnos_page'),
    
    # APIs de rutinas personalizadas
    path('api/rutinas/crear-personalizada/', crear_rutina_personalizada, name='crear_rutina_personalizada'),
    path('alumno/api/rutinas-asignadas/', obtener_rutinas_asignadas_alumno, name='rutinas_asignadas_alumno'),
    path('alumno/api/rutinas-personales/', obtener_rutinas_personales_alumno, name='rutinas_personales_alumno'),
    path('alumno/api/calendario-semanal/', obtener_calendario_semanal_alumno, name='calendario_semanal_alumno'),
    
    # API para asignar rutina desde detalle del alumno
    path('api/alumno/<int:alumno_id>/asignar-rutina/', api_asignar_rutina_alumno, name='api_asignar_rutina_alumno'),
    path('api/rutina/<int:rutina_id>/eliminar/', api_eliminar_rutina_alumno, name='api_eliminar_rutina_alumno'),
    
    # Editar rutina del alumno (bajo entrenador para acceso desde panel entrenador)
    path('alumnos/<int:alumno_id>/rutina/<int:rutina_id>/editar/', editar_rutina_alumno, name='editar_rutina_alumno'),

    # Service Worker
    path('service-worker.js', service_worker, name='service_worker'),
    
    # Catchall: cualquier ruta no reconocida redirige a login (EXCEPTO /login/)
    re_path(r'^(?!login/).*$', catchall_redirect, name='catchall'),
]

import importlib
# Try both possible module paths. The project has a nested layout so depending on
# which manage.py is used the import root may differ. First try the short
# 'notifications.urls' (when running from project root), then the
# 'entrenador_app.notifications.urls' (when running from outer package).
notifs_module = None
for modname in ('notifications.urls', 'entrenador_app.notifications.urls'):
    try:
        importlib.import_module(modname)
        notifs_module = modname
        break
    except Exception:
        continue

if notifs_module is None:
    print('Warning: notifications.urls not importable under either path; skipping notifications routes')
else:
    from django.urls import path as _path, include as _include
    urlpatterns += [
        _path('notifications/', _include(notifs_module)),
    ]

# Servir media en DEBUG
from django.conf import settings as _settings
from django.conf.urls.static import static as _static
if getattr(_settings, 'DEBUG', False):
    urlpatterns += _static(_settings.MEDIA_URL, document_root=_settings.MEDIA_ROOT)
