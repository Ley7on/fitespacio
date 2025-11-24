from django.urls import path
from . import views_rutinas as views
from . import views_asignar_rutinas_aws
from . import views_rutinas_personalizadas

urlpatterns = [
    path('api/rutinas/', views.obtener_rutinas, name='obtener_rutinas_api'),
    path('api/rutinas/crear/', views.crear_rutina, name='crear_rutina'),
    path('api/rutinas/<int:rutina_id>/', views.obtener_rutina_detalle, name='obtener_detalle_rutina'),
    path('api/rutinas/<int:rutina_id>/actualizar/', views.actualizar_rutina, name='actualizar_rutina'),
    path('api/rutinas/<int:rutina_id>/editar/', views.editar_rutina, name='editar_rutina'),
    path('api/rutinas/<int:rutina_id>/duplicar/', views.duplicar_rutina, name='duplicar_rutina'),
    path('api/rutinas/<int:rutina_id>/eliminar/', views.eliminar_rutina, name='eliminar_rutina'),
    path('api/rutinas/<int:rutina_id>/ejercicios/<int:ejercicio_id>/', views.eliminar_ejercicio_rutina, name='eliminar_ejercicio_rutina'),
    path('api/rutinas/<int:rutina_id>/ejercicios/<int:ejercicio_id>/', views.eliminar_ejercicio_rutina, name='eliminar_ejercicio_rutina'),

    # Upload de video para ejercicios
    path('api/ejercicios/upload-video/', views.upload_ejercicio_video, name='upload_ejercicio_video'),

    # Alumno marca completado
    path('api/entrenamientos/completar/', views.completar_ejercicio, name='completar_ejercicio'),

    # Analytics: volumen por ejercicio
    path('api/analytics/volumen-ejercicio/', views.volumen_ejercicio, name='volumen_ejercicio'),

    # NUEVO: endpoints para asignación de rutinas a alumnos
    path('api/alumnos/', views.obtener_alumnos, name='obtener_alumnos'),
    path('api/rutinas/<int:rutina_id>/asignar/', views.asignar_rutina_a_alumnos, name='asignar_rutina_a_alumnos'),
    path('api/rutinas/<int:rutina_id>/alumnos/', views.obtener_alumnos_rutina, name='obtener_alumnos_rutina'),
    
    # Sistema nuevo de asignación de rutinas
    path('api/asignar-rutina-alumno/', views_asignar_rutinas_aws.asignar_rutina_alumno, name='asignar_rutina_alumno'),
    
    # Rutinas personalizadas
    path('api/rutinas/crear-personalizada/', views_rutinas_personalizadas.crear_rutina_personalizada, name='crear_rutina_personalizada'),

]
