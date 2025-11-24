from django.urls import path
from django.views.generic import RedirectView
from . import views, views_rutina, views_rutinas_aws as views_rutinas
from entrenador import views_rutinas_personalizadas

app_name = 'alumno'

urlpatterns = [
    path('', views.dashboard_alumno, name='dashboard'),
    path('informacion-inicial/', views.informacion_inicial, name='informacion_inicial'),
    path('qr/', views.generar_qr, name='generar_qr'),
    path('validar-qr/', views.validar_acceso_qr, name='validar_qr'),
    # Se eliminó la ruta singular 'rutina/' por migración a la nueva vista 'rutinas/'
    # path('rutina/', views.rutina_personalizada, name='rutina'),
    path('progreso/', views.registrar_progreso, name='progreso'),
    # API para un registro de progreso individual (ver/editar/eliminar)
    path('api/progreso/<int:progreso_id>/', views.api_progreso_detail, name='api_progreso_detail'),
    path('progreso/export/', views.export_progresos, name='export_progresos'),
    path('historial/', views.historial_asistencia, name='historial'),
    path('metricas/', views.metricas_personales, name='metricas'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    
    # Hábitos
    path('habitos-buenos/', views.habitos_buenos, name='habitos_buenos'),
    path('habitos-buenos/<int:habito_id>/registrar/', views.registrar_habito_bueno, name='registrar_habito_bueno'),
    path('habitos-buenos/<int:habito_id>/editar/', views.editar_habito_bueno, name='editar_habito_bueno'),
    path('habitos-buenos/<int:habito_id>/eliminar/', views.eliminar_habito_bueno, name='eliminar_habito_bueno'),
    path('habitos-malos/', views.habitos_malos, name='habitos_malos'),
    path('habitos-malos/<int:habito_id>/editar/', views.editar_habito_malo, name='editar_habito_malo'),
    path('habitos-malos/<int:habito_id>/eliminar/', views.eliminar_habito_malo, name='eliminar_habito_malo'),
    
    # Sistema de Rutinas Nuevo
    path('rutinas/', views_rutinas.rutinas_dashboard, name='rutinas'),
    path('rutinas/crear/', views.crear_rutina, name='rutina_crear'),
    path('api/rutinas-asignadas/', views_rutinas_personalizadas.obtener_rutinas_asignadas_alumno, name='api_rutinas_asignadas'),
    path('api/rutinas-personales/', views_rutinas_personalizadas.obtener_rutinas_personales_alumno, name='api_rutinas_personales'),
    path('api/rutina/<int:rutina_id>/editar/', views_rutinas_personalizadas.editar_rutina_personal_alumno, name='api_editar_rutina_personal'),
    path('api/rutina/<int:rutina_id>/eliminar/', views_rutinas_personalizadas.eliminar_rutina_personal_alumno, name='api_eliminar_rutina_personal'),
    path('api/crear-rutina-personal/', views_rutinas.crear_rutina_personal, name='api_crear_rutina_personal'),
    path('api/calendario-semanal/', views_rutinas_personalizadas.obtener_calendario_semanal_alumno, name='api_calendario_semanal'),
    path('api/rutina/<int:rutina_id>/detalle/', views_rutinas_personalizadas.obtener_detalle_rutina, name='api_detalle_rutina'),
    path('api/rutina/<int:rutina_id>/', views_rutinas_personalizadas.rutina_detail_api, name='api_rutina_detail'),
    path('api/rutina/<int:rutina_id>/completar/', views_rutinas_personalizadas.marcar_rutina_completada, name='api_completar_rutina'),
    
    # Redirigir ruta vieja /alumno/rutina/ a /alumno/rutinas/
    path('rutina/', RedirectView.as_view(pattern_name='alumno:rutinas', permanent=True), name='rutina_redirect'),
    # Compatibilidad: nombre antiguo 'mi_rutina' usado en plantillas
    path('mi-rutina/', RedirectView.as_view(pattern_name='alumno:rutinas', permanent=False), name='mi_rutina'),
    
    # Rutas de Rutinas Antiguas (mantener por compatibilidad)
    path('rutina/crear/', views.crear_rutina_view, name='crear_rutina'),
    path('rutina/<int:rutina_id>/editar/', views.editar_rutina_view, name='editar_rutina'),
    path('rutina/<int:rutina_id>/ejecutar/', views.ejecutar_rutina_view, name='ejecutar_rutina'),
    path('api/ejercicios/', views_rutina.obtener_ejercicios, name='api_ejercicios'),
    path('api/rutinas/crear/', views_rutina.crear_rutina, name='api_crear_rutina'),
    
    # Mensajes Motivacionales
    path('mensajes/', views.mensajes_motivacionales, name='mensajes_motivacionales'),
    path('mensajes/<int:mensaje_id>/leido/', views.marcar_mensaje_leido, name='marcar_mensaje_leido'),
    path('mensajes/notif/<int:notif_id>/leido/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('api/mensajes-no-leidos/', views.obtener_mensajes_no_leidos, name='mensajes_no_leidos'),
    path('api/mensajes/', views.api_mensajes, name='api_mensajes'),
    path('api/marcar-todos-leidos/', views.marcar_todos_mensajes_leidos, name='marcar_todos_leidos'),
    
    # Ejercicios
    path('ejercicios/', views.ejercicios_disponibles, name='ejercicios'),
    path('ejercicios/<int:ejercicio_id>/', views.detalle_ejercicio, name='detalle_ejercicio'),
    
    # Metas
    path('metas/', views.metas, name='metas'),
    path('metas/<int:meta_id>/', views.detalle_meta, name='detalle_meta'),
    path('acciones/<int:accion_id>/completar/', views.completar_accion, name='completar_accion'),
    path('metas/<int:meta_id>/completar/', views.completar_meta, name='completar_meta'),
    path('metas/<int:meta_id>/editar/', views.editar_meta, name='editar_meta'),
    path('metas/<int:meta_id>/eliminar/', views.eliminar_meta, name='eliminar_meta'),
    path('metas/export/csv/', views.export_metas_csv, name='export_metas_csv'),
    path('metas/export/pdf/', views.export_metas_pdf, name='export_metas_pdf'),
    
    # Eventos
    path('eventos/', views.eventos_disponibles, name='eventos'),
    
    # Perfil
    path('perfil/', views.perfil_alumno, name='perfil'),
    path('debug-admin/', views.debug_admin_data, name='debug_admin'),
    path('debug-visitas-hoy/', views.debug_visitas_hoy, name='debug_visitas_hoy'),
    path('sincronizar-admin/', views.sincronizar_usuario_admin, name='sincronizar_admin'),
    
]