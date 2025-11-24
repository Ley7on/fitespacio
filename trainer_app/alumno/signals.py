from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import AccesoGimnasio, ProgresoFisico, MensajeMotivacional, RegistroEjercicio


def _crear_mensaje_si_no_duplicado(alumno, tipo, titulo, contenido, prioridad=2, ventana_horas=24):
    try:
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
        pass
    return None


@receiver(post_save, sender=AccesoGimnasio)
def acceso_creado(sender, instance, created, **kwargs):
    """Cuando se crea un acceso de tipo 'entrada', generar una notificación de felicitación."""
    if not created:
        return
    try:
        if instance.tipo_acceso == 'entrada':
            alumno = instance.alumno
            # Calcular racha rápida: contar fechas únicas de acceso (últimos días)
            try:
                fechas = AccesoGimnasio.objects.filter(
                    alumno=alumno,
                    tipo_acceso='entrada'
                ).dates('fecha_acceso', 'day').order_by('-fecha_acceso')
                racha = 0
                from datetime import timedelta as _td
                hoy = timezone.now().date()
                fecha_esperada = hoy
                for f in fechas:
                    if f == fecha_esperada:
                        racha += 1
                        fecha_esperada -= _td(days=1)
                    else:
                        break
            except Exception:
                racha = 1

            titulo = '¡Buen trabajo!'
            if racha > 1:
                titulo = f'¡Racha de {racha} días! 🔥'
            contenido = 'Has registrado tu asistencia. ¡Sigue así!'
            if racha > 1:
                contenido = f'¡Increíble! Llevas {racha} días seguidos registrando tu asistencia. Mantén la constancia.'

            _crear_mensaje_si_no_duplicado(alumno, 'asistencia', titulo, contenido, prioridad=1, ventana_horas=24)
    except Exception:
        pass


@receiver(post_save, sender=ProgresoFisico)
def progreso_creado(sender, instance, created, **kwargs):
    """Cuando se crea un progreso físico, crear una notificación de logro si hay datos relevantes."""
    if not created:
        return
    try:
        alumno = instance.alumno
        parts = []
        if getattr(instance, 'peso', None):
            parts.append(f'Peso: {instance.peso} kg')
        if getattr(instance, 'grasa_corporal', None):
            parts.append(f'% Grasa: {instance.grasa_corporal}')
        if getattr(instance, 'masa_muscular', None):
            parts.append(f'Masa muscular: {instance.masa_muscular}')

        if parts:
            contenido = 'Registro de progreso: ' + ', '.join(parts)
            # Incluir un fragmento en el título para hacerlo único por registro
            resumen = parts[0] if parts else 'Progreso'
            titulo = f'Progreso: {resumen}'
            _crear_mensaje_si_no_duplicado(alumno, 'progreso', titulo, contenido, prioridad=1, ventana_horas=24)
    except Exception:
        pass


@receiver(post_save, sender=RegistroEjercicio)
def ejercicio_creado(sender, instance, created, **kwargs):
    """Cuando se registra un ejercicio, crear una notificación leve de logro."""
    if not created:
        return
    try:
        alumno = instance.alumno
        detalle = f'{instance.series}x{instance.repeticiones}'
        if getattr(instance, 'peso', None):
            detalle += f' - {instance.peso}kg'
        titulo = f'Registro: {instance.ejercicio.nombre} {detalle}'
        contenido = f'Has registrado {detalle} en {instance.ejercicio.nombre}. ¡Buen trabajo!'
        _crear_mensaje_si_no_duplicado(alumno, 'progreso', titulo, contenido, prioridad=2, ventana_horas=12)
    except Exception:
        pass
    
