from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
import json
import logging
from entrenador_app.auth_views import require_role
from entrenador_app.shift_system import ShiftSystem

logger = logging.getLogger(__name__)

@csrf_protect
@require_http_methods(["POST"])
@require_role('entrenador')
def toggle_shift(request):
    """Inicia o termina el turno del entrenador"""
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'start' or 'end'
        
        entrenador_id = 'entrenador'  # Mock ID
        
        if action == 'start':
            success = ShiftSystem.start_shift(entrenador_id)
            if success:
                shift_info = ShiftSystem.get_shift_info(entrenador_id)
                return JsonResponse({
                    'success': True,
                    'status': 'active',
                    'message': 'Turno iniciado correctamente',
                    'shift_info': {
                        'start_time': shift_info['start_time'].isoformat(),
                        'duration_hours': shift_info['duration_hours']
                    }
                })
        
        elif action == 'end':
            success = ShiftSystem.end_shift(entrenador_id)
            if success:
                return JsonResponse({
                    'success': True,
                    'status': 'ended',
                    'message': 'Turno finalizado correctamente'
                })
        
        return JsonResponse({'error': 'Acción inválida'}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error toggling shift: {str(e)}")
        return JsonResponse({'error': 'Error interno'}, status=500)

@require_role('entrenador')
def get_shift_status(request):
    """Obtiene el estado actual del turno"""
    try:
        entrenador_id = 'entrenador'
        
        is_on_shift = ShiftSystem.is_on_shift(entrenador_id)
        shift_info = ShiftSystem.get_shift_info(entrenador_id) if is_on_shift else None
        should_be_on_shift = ShiftSystem.should_be_on_shift(entrenador_id)
        
        response_data = {
            'is_on_shift': is_on_shift,
            'should_be_on_shift': should_be_on_shift,
            'shift_info': None
        }
        
        if shift_info:
            response_data['shift_info'] = {
                'start_time': shift_info['start_time'].isoformat(),
                'duration_hours': round(shift_info['duration_hours'], 2),
                'status': shift_info['status']
            }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting shift status: {str(e)}")
        return JsonResponse({'error': 'Error interno'}, status=500)