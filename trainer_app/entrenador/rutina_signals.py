# entrenador/rutina_signals.py
# Signals para sincronizar automáticamente cambios de rutinas del entrenador con rutinas asignadas a alumnos

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender='entrenador.DetalleEjercicio')
def sincronizar_ejercicio_actualizado(sender, instance, created, **kwargs):
    """
    Cuando un DetalleEjercicio del entrenador se actualiza,
    sincronizar automáticamente todos los EjercicioRutinaAlumno que referencian a este
    """
    if created:
        return  # Solo sincronizar en actualizaciones, no en creaciones
    
    try:
        from alumno.models import EjercicioRutinaAlumno
        
        # Encontrar todos los ejercicios de alumnos que referencian este ejercicio
        ejercicios_alumnos = EjercicioRutinaAlumno.objects.filter(
            ejercicio_entrenador=instance
        )
        
        if not ejercicios_alumnos.exists():
            return
        
        # Actualizar cada ejercicio del alumno con los nuevos valores
        with transaction.atomic():
            count = 0
            for ej_alumno in ejercicios_alumnos:
                # Sincronizar campos desde el DetalleEjercicio del entrenador
                ej_alumno.nombre = instance.nombre_ejercicio
                ej_alumno.series = instance.series
                ej_alumno.repeticiones = instance.repeticiones
                
                # Solo actualizar peso si el alumno no lo ha personalizado (mantener su peso personalizado)
                if not ej_alumno.peso or ej_alumno.peso == str(instance.peso_inicial):
                    ej_alumno.peso = str(instance.peso_inicial) if instance.peso_inicial else ''
                
                ej_alumno.descanso = instance.descanso
                ej_alumno.notas = instance.notas
                ej_alumno.orden = instance.orden
                
                ej_alumno.save()
                count += 1
            
            logger.info(f"✅ Sincronizados {count} ejercicios de alumnos desde DetalleEjercicio {instance.id} ({instance.nombre_ejercicio})")
    
    except Exception as e:
        logger.error(f"❌ Error sincronizando ejercicio {instance.id}: {e}", exc_info=True)


@receiver(post_delete, sender='entrenador.DetalleEjercicio')
def eliminar_ejercicios_alumnos_huerfanos(sender, instance, **kwargs):
    """
    Cuando se elimina un DetalleEjercicio del entrenador,
    eliminar también los ejercicios de alumnos que lo referencian
    (o marcarlos como huérfanos para que el alumno decida)
    """
    try:
        from alumno.models import EjercicioRutinaAlumno
        
        # Opción 1: Eliminar ejercicios huérfanos
        ejercicios_alumnos = EjercicioRutinaAlumno.objects.filter(
            ejercicio_entrenador=instance
        )
        
        count = ejercicios_alumnos.count()
        if count > 0:
            ejercicios_alumnos.delete()
            logger.info(f"🗑️ Eliminados {count} ejercicios de alumnos huérfanos (DetalleEjercicio {instance.id} eliminado)")
        
        # Opción 2 alternativa: Solo quitar la referencia (descomentar si prefieres mantener el ejercicio)
        # ejercicios_alumnos.update(ejercicio_entrenador=None)
        # logger.info(f"🔗 Desvinculados {count} ejercicios de alumnos (DetalleEjercicio {instance.id} eliminado)")
    
    except Exception as e:
        logger.error(f"❌ Error eliminando ejercicios huérfanos: {e}", exc_info=True)


@receiver(post_save, sender='entrenador.Rutina')
def sincronizar_rutina_actualizada(sender, instance, created, **kwargs):
    """
    Cuando una Rutina del entrenador se actualiza,
    sincronizar campos básicos en todas las RutinaAlumno que la referencian
    """
    if created:
        return  # Solo sincronizar en actualizaciones
    
    try:
        from alumno.models import RutinaAlumno
        
        # Encontrar todas las rutinas de alumnos que referencian esta rutina
        rutinas_alumnos = RutinaAlumno.objects.filter(
            rutina_entrenador=instance
        )
        
        if not rutinas_alumnos.exists():
            return
        
        # Actualizar campos básicos
        with transaction.atomic():
            count = rutinas_alumnos.update(
                nombre=instance.nombre,
                objetivo=instance.objetivo,
                descripcion=instance.descripcion
            )
            
            logger.info(f"✅ Sincronizadas {count} rutinas de alumnos desde Rutina {instance.id} ({instance.nombre})")
    
    except Exception as e:
        logger.error(f"❌ Error sincronizando rutina {instance.id}: {e}", exc_info=True)


@receiver(post_save, sender='entrenador.Rutina')
def sincronizar_nuevos_ejercicios(sender, instance, created, **kwargs):
    """
    Cuando se añaden nuevos ejercicios a una Rutina del entrenador,
    añadirlos automáticamente a todas las rutinas de alumnos que la tienen asignada
    """
    if created:
        return  # Solo para actualizaciones
    
    try:
        from alumno.models import RutinaAlumno, EjercicioRutinaAlumno
        from entrenador.models import DetalleEjercicio
        
        # Encontrar rutinas de alumnos que referencian esta rutina
        rutinas_alumnos = RutinaAlumno.objects.filter(rutina_entrenador=instance)
        
        if not rutinas_alumnos.exists():
            return
        
        # Obtener ejercicios actuales de la rutina del entrenador
        ejercicios_entrenador = DetalleEjercicio.objects.filter(rutina=instance).order_by('orden')
        
        with transaction.atomic():
            for rutina_alumno in rutinas_alumnos:
                # Obtener IDs de ejercicios que ya tiene el alumno
                ejercicios_existentes_ids = set(
                    rutina_alumno.ejercicios.filter(ejercicio_entrenador__isnull=False)
                    .values_list('ejercicio_entrenador_id', flat=True)
                )
                
                # Añadir nuevos ejercicios que el alumno no tiene
                nuevos = 0
                for detalle_ej in ejercicios_entrenador:
                    if detalle_ej.id not in ejercicios_existentes_ids:
                        EjercicioRutinaAlumno.objects.create(
                            rutina=rutina_alumno,
                            nombre=detalle_ej.nombre_ejercicio,
                            series=detalle_ej.series,
                            repeticiones=detalle_ej.repeticiones,
                            peso=str(detalle_ej.peso_inicial) if detalle_ej.peso_inicial else '',
                            descanso=detalle_ej.descanso,
                            notas=detalle_ej.notas,
                            orden=detalle_ej.orden,
                            ejercicio_entrenador=detalle_ej
                        )
                        nuevos += 1
                
                if nuevos > 0:
                    logger.info(f"➕ Añadidos {nuevos} nuevos ejercicios a rutina del alumno {rutina_alumno.id}")
    
    except Exception as e:
        logger.error(f"❌ Error añadiendo nuevos ejercicios: {e}", exc_info=True)
