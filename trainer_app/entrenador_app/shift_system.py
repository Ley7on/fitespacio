from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class ShiftSystem:
    """Sistema de turnos para entrenadores"""
    
    # Simulamos turnos en memoria para demo
    _active_shifts = {}
    _shift_schedules = {
        'entrenador': {
            'monday': [{'start': '08:00', 'end': '16:00'}],
            'tuesday': [{'start': '08:00', 'end': '16:00'}],
            'wednesday': [{'start': '08:00', 'end': '16:00'}],
            'thursday': [{'start': '08:00', 'end': '16:00'}],
            'friday': [{'start': '08:00', 'end': '16:00'}],
            'saturday': [{'start': '09:00', 'end': '13:00'}],
            'sunday': []
        }
    }
    
    @classmethod
    def start_shift(cls, entrenador_id):
        """Inicia turno del entrenador"""
        now = timezone.now()
        cls._active_shifts[entrenador_id] = {
            'start_time': now,
            'status': 'active',
            'last_activity': now
        }
        logger.info(f"Shift started for entrenador {entrenador_id}")
        return True
    
    @classmethod
    def end_shift(cls, entrenador_id):
        """Termina turno del entrenador"""
        if entrenador_id in cls._active_shifts:
            cls._active_shifts[entrenador_id]['status'] = 'ended'
            cls._active_shifts[entrenador_id]['end_time'] = timezone.now()
            logger.info(f"Shift ended for entrenador {entrenador_id}")
            return True
        return False
    
    @classmethod
    def is_on_shift(cls, entrenador_id):
        """Verifica si el entrenador está en turno"""
        if entrenador_id not in cls._active_shifts:
            return False
        
        shift = cls._active_shifts[entrenador_id]
        return shift.get('status') == 'active'
    
    @classmethod
    def get_shift_info(cls, entrenador_id):
        """Obtiene información del turno actual"""
        if entrenador_id not in cls._active_shifts:
            return None
        
        shift = cls._active_shifts[entrenador_id]
        if shift.get('status') != 'active':
            return None
        
        now = timezone.now()
        duration = now - shift['start_time']
        
        return {
            'start_time': shift['start_time'],
            'duration': duration,
            'status': shift['status'],
            'duration_hours': duration.total_seconds() / 3600
        }
    
    @classmethod
    def get_available_entrenadores(cls):
        """Obtiene lista de entrenadores disponibles"""
        available = []
        for entrenador_id, shift in cls._active_shifts.items():
            if shift.get('status') == 'active':
                available.append({
                    'id': entrenador_id,
                    'name': cls._get_entrenador_name(entrenador_id),
                    'shift_start': shift['start_time'],
                    'duration': timezone.now() - shift['start_time']
                })
        return available
    
    @classmethod
    def update_activity(cls, entrenador_id):
        """Actualiza última actividad del entrenador"""
        if entrenador_id in cls._active_shifts:
            cls._active_shifts[entrenador_id]['last_activity'] = timezone.now()
    
    @classmethod
    def get_scheduled_hours(cls, entrenador_id, day_name=None):
        """Obtiene horarios programados del entrenador"""
        if day_name is None:
            day_name = timezone.now().strftime('%A').lower()
        
        schedule = cls._shift_schedules.get(entrenador_id, {})
        return schedule.get(day_name, [])
    
    @classmethod
    def should_be_on_shift(cls, entrenador_id):
        """Verifica si el entrenador debería estar en turno según horario"""
        now = timezone.now()
        current_time = now.strftime('%H:%M')
        day_name = now.strftime('%A').lower()
        
        scheduled_hours = cls.get_scheduled_hours(entrenador_id, day_name)
        
        for shift in scheduled_hours:
            if shift['start'] <= current_time <= shift['end']:
                return True
        
        return False
    
    @classmethod
    def _get_entrenador_name(cls, entrenador_id):
        """Mock function para obtener nombre del entrenador"""
        names = {
            'entrenador': 'Carlos Díaz',
            '1': 'María González',
            '2': 'Juan Rodríguez'
        }
        return names.get(str(entrenador_id), f'Entrenador {entrenador_id}')

# Inicializar turno de demo
ShiftSystem.start_shift('entrenador')