from django.urls import path
from django.shortcuts import render
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('usuarios/', views.usuarios, name='usuarios'),
    path('sesiones/', views.sesiones, name='sesiones'),
    path('pagos/', views.pagos, name='pagos'),
    path('reportes/', views.reportes, name='reportes'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('usuario/<int:usuario_id>/', views.usuario_detalle, name='usuario_detalle'),
    path('usuario/<int:usuario_id>/marcar-asistencia/', views.marcar_asistencia, name='marcar_asistencia'),
    path('usuario/<int:usuario_id>/modificar/', views.modificar_usuario, name='modificar_usuario'),
    path('usuario/<int:usuario_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    path('profesores/', views.profesores, name='profesores'),
    path('profesor/<int:profesor_id>/editar/', views.editar_profesor, name='editar_profesor'),
    path('profesor/<int:profesor_id>/eliminar/', views.eliminar_profesor, name='eliminar_profesor'),
    path('cambiar_password/', views.cambiar_password, name='cambiar_password'),
    path('avisar-pago/<int:pago_id>/', views.avisar_pago, name='avisar_pago'),
    path('marcar-pagado/<int:pago_id>/', views.marcar_pagado, name='marcar_pagado'),
    path('marcar-vencido/<int:pago_id>/', views.marcar_vencido, name='marcar_vencido'),
    path('scanner-qr/', views.scanner_qr, name='scanner_qr'),
    path('api/validar-qr/', views.validar_qr_api, name='validar_qr_api'),
    path('api/asistencias-hoy/', views.asistencias_hoy_api, name='asistencias_hoy_api'),
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('reportes/exportar/pdf/', views.exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reportes/exportar/excel/', views.exportar_reporte_excel, name='exportar_reporte_excel'),
    path('test-tailwind/', lambda request: render(request, 'admin_gym/test_tailwind.html'), name='test_tailwind'),
]