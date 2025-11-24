# views_asignar_rutinas_aws.py - Vista para asignar rutinas usando tablas AWS

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def asignar_rutina_alumno(request):
    """Asignar rutina usando las tablas AWS existentes"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        from entrenador_app.admin_gym_models import AdminGymRutina, AdminGymEjercicio, AdminGymEjercicioRutina, AdminGymCliente, AdminGymRutinaCliente
        
        data = json.loads(request.body)
        
        nombre = data.get('nombre', '').strip()
        objetivo = data.get('objetivo', '').strip()
        alumno_id = data.get('alumno_id')
        ejercicios = data.get('ejercicios', [])
        
        if not nombre or not objetivo or not alumno_id:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan datos obligatorios'
            })
        
        with transaction.atomic():
            # 1. Crear rutina en admin_gym_rutina
            rutina = AdminGymRutina.objects.create(
                nombre=nombre,
                descripcion=data.get('descripcion', ''),
                objetivo=objetivo,
                creado_por=request.user,
                activa=True
            )
            
            # 2. Crear ejercicios
            for i, ej_data in enumerate(ejercicios, 1):
                ejercicio, created = AdminGymEjercicio.objects.get_or_create(
                    nombre=ej_data['nombre'],
                    defaults={
                        'descripcion': '',
                        'tipo': 'fuerza',
                        'grupo_muscular': 'general',
                        'activo': True
                    }
                )
                
                AdminGymEjercicioRutina.objects.create(
                    rutina=rutina,
                    ejercicio=ejercicio,
                    series=ej_data.get('series', 3),
                    repeticiones=ej_data.get('repeticiones', '8-12'),
                    peso_sugerido=ej_data.get('peso', ''),
                    tiempo_descanso=ej_data.get('descanso', 60),
                    notas=ej_data.get('notas', ''),
                    orden=i
                )
            
            # 3. Asignar a cliente
            cliente = AdminGymCliente.objects.filter(user_id=alumno_id).first()
            if cliente:
                AdminGymRutinaCliente.objects.create(
                    rutina=rutina,
                    cliente=cliente,
                    asignado_por=request.user,
                    activa=True
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Rutina asignada exitosamente',
            'rutina_id': rutina.id
        })
        
    except Exception as e:
        logger.error(f"Error asignando rutina: {e}")
        return JsonResponse({'success': False, 'message': str(e)})