from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class FitnessHeuristics:
    """Sistema de reglas heurísticas para seguimiento personalizado"""
    
    @staticmethod
    def check_attendance_patterns(alumno_id, last_visits):
        """Analiza patrones de asistencia y genera mensajes personalizados"""
        messages = []
        now = timezone.now()
        
        if not last_visits:
            # Sin visitas registradas
            messages.append({
                'type': 'welcome',
                'title': '¡Bienvenido a FitTracker! 🎯',
                'message': 'Estamos emocionados de tenerte en nuestro equipo. ¿Listo para comenzar tu transformación?',
                'priority': 'high'
            })
            return messages
        
        last_visit = last_visits[0] if last_visits else None
        days_since_last = (now.date() - last_visit).days if last_visit else 999
        
        # Regla: 2 días sin entrenar
        if days_since_last >= 2:
            messages.append({
                'type': 'check_in',
                'title': '¿Cómo estás? 💪',
                'message': f'Han pasado {days_since_last} días desde tu último entrenamiento. ¿Todo bien? Recuerda que la constancia es clave para alcanzar tus objetivos.',
                'priority': 'medium'
            })
        
        # Regla: 5 días sin entrenar
        if days_since_last >= 5:
            messages.append({
                'type': 'motivation',
                'title': '¡Te extrañamos en el gym! 🏋️‍♂️',
                'message': 'Sabemos que la vida puede ser intensa, pero no olvides que cada día es una nueva oportunidad para cuidar tu salud. ¿Necesitas ajustar tu rutina?',
                'priority': 'high'
            })
        
        # Regla: Racha positiva
        if len(last_visits) >= 3 and all((last_visits[i] - last_visits[i+1]).days <= 2 for i in range(len(last_visits)-1)):
            messages.append({
                'type': 'congratulations',
                'title': '¡Increíble constancia! 🔥',
                'message': 'Tu dedicación es admirable. Mantener esta rutina te llevará directo a tus objetivos. ¡Sigue así!',
                'priority': 'low'
            })
        
        return messages
    
    @staticmethod
    def check_progress_patterns(progress_data):
        """Analiza progreso físico y genera recomendaciones"""
        messages = []
        
        if not progress_data:
            messages.append({
                'type': 'progress_reminder',
                'title': 'Registra tu progreso 📊',
                'message': 'Llevar un registro de tu peso y medidas te ayudará a ver tu evolución. ¡Cada pequeño cambio cuenta!',
                'priority': 'medium'
            })
            return messages
        
        # Analizar tendencias de peso
        if len(progress_data) >= 2:
            latest = progress_data[0]
            previous = progress_data[1]
            
            if latest.peso and previous.peso:
                weight_change = latest.peso - previous.peso
                
                if weight_change > 2:  # Aumento significativo
                    messages.append({
                        'type': 'weight_concern',
                        'title': 'Revisemos tu progreso 🤔',
                        'message': f'He notado un cambio en tu peso (+{weight_change:.1f}kg). ¿Cómo te sientes? Podemos ajustar tu plan si es necesario.',
                        'priority': 'medium'
                    })
                elif weight_change < -2:  # Pérdida significativa
                    messages.append({
                        'type': 'weight_progress',
                        'title': '¡Excelente progreso! 🎉',
                        'message': f'Has perdido {abs(weight_change):.1f}kg. Tu esfuerzo está dando resultados. ¡Mantén el rumbo!',
                        'priority': 'low'
                    })
        
        return messages
    
    @staticmethod
    def check_workout_completion(workout_data):
        """Analiza completitud de entrenamientos"""
        messages = []
        
        if not workout_data:
            return messages
        
        completion_rate = sum(1 for w in workout_data if w.get('completed', False)) / len(workout_data)
        
        if completion_rate < 0.5:  # Menos del 50% completado
            messages.append({
                'type': 'workout_support',
                'title': 'Ajustemos tu rutina 💡',
                'message': 'He notado que algunas rutinas quedan incompletas. ¿Son muy intensas? Podemos modificarlas para que se adapten mejor a ti.',
                'priority': 'high'
            })
        elif completion_rate > 0.8:  # Más del 80% completado
            messages.append({
                'type': 'workout_praise',
                'title': '¡Eres imparable! ⚡',
                'message': 'Tu dedicación para completar las rutinas es ejemplar. ¿Te sientes listo para un nuevo desafío?',
                'priority': 'low'
            })
        
        return messages
    
    @staticmethod
    def generate_personalized_tips(alumno_profile):
        """Genera consejos personalizados basados en el perfil"""
        tips = []
        
        # Tips basados en el plan
        if alumno_profile.get('plan') == 'basic':
            tips.append("💡 Tip: Mantén una rutina simple pero constante. La consistencia es más importante que la intensidad.")
        elif alumno_profile.get('plan') == 'pro':
            tips.append("💡 Tip: Aprovecha al máximo tu plan Pro. Considera variar tus entrenamientos cada 4-6 semanas.")
        elif alumno_profile.get('plan') == 'vip':
            tips.append("💡 Tip: Con tu plan VIP tienes acceso completo. ¿Has probado las clases grupales?")
        
        # Tips generales motivacionales
        motivational_tips = [
            "🌟 Recuerda: Cada día que entrenas es una inversión en tu futuro yo.",
            "💪 El progreso no siempre es visible, pero siempre está ahí. ¡Confía en el proceso!",
            "🎯 Pequeños pasos consistentes llevan a grandes transformaciones.",
            "🔥 Tu única competencia eres tú mismo de ayer.",
            "⭐ El mejor entrenamiento es el que haces, no el perfecto que planeas."
        ]
        
        import random
        tips.append(random.choice(motivational_tips))
        
        return tips

def process_heuristic_messages(alumno_id, alumno_data):
    """Procesa todas las reglas heurísticas y genera mensajes"""
    all_messages = []
    
    # Verificar patrones de asistencia
    attendance_messages = FitnessHeuristics.check_attendance_patterns(
        alumno_id, 
        alumno_data.get('last_visits', [])
    )
    all_messages.extend(attendance_messages)
    
    # Verificar patrones de progreso
    progress_messages = FitnessHeuristics.check_progress_patterns(
        alumno_data.get('progress_data', [])
    )
    all_messages.extend(progress_messages)
    
    # Verificar completitud de entrenamientos
    workout_messages = FitnessHeuristics.check_workout_completion(
        alumno_data.get('workout_data', [])
    )
    all_messages.extend(workout_messages)
    
    # Generar tips personalizados
    tips = FitnessHeuristics.generate_personalized_tips(
        alumno_data.get('profile', {})
    )
    
    # Convertir tips a mensajes
    for tip in tips:
        all_messages.append({
            'type': 'tip',
            'title': 'Consejo personalizado',
            'message': tip,
            'priority': 'low'
        })
    
    # Ordenar por prioridad
    priority_order = {'high': 3, 'medium': 2, 'low': 1}
    all_messages.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
    
    logger.info(f"Generated {len(all_messages)} heuristic messages for alumno {alumno_id}")
    
    return all_messages[:3]  # Limitar a 3 mensajes más importantes