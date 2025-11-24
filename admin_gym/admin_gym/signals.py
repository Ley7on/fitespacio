from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cliente
import uuid
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Cliente)
def crear_cliente_entrenador_app(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un cliente en admin_app.
    Crea automáticamente un registro correspondiente en entrenador_app.
    """
    if created and instance.user:  # Solo si es un nuevo cliente y tiene usuario
        try:
            # Intentar importar el modelo del entrenador_app
            # Si falla, simplemente registrar el error y continuar
            try:
                import sys
                import os
                
                # Agregar el path de entrenador_app al sys.path si no está
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                entrenador_path = os.path.join(base_dir, 'entrenador_app')
                if entrenador_path not in sys.path:
                    sys.path.append(entrenador_path)
                
                from entrenador_app.admin_gym_models import AdminGymCliente
                
                # Verificar si ya existe un cliente en entrenador_app para este usuario
                if not AdminGymCliente.objects.filter(user=instance.user).exists():
                    # Generar QR único
                    qr_code = str(uuid.uuid4())[:20]
                    qr_secret = str(uuid.uuid4())[:32]

                    # Crear el cliente en entrenador_app
                    AdminGymCliente.objects.create(
                        nombre=instance.nombre,
                        email=instance.email,
                        telefono=instance.telefono or '',
                        activo=instance.activo,
                        fecha_registro=instance.fecha_registro,
                        membresia=instance.membresia,
                        estado_membresia=instance.estado_membresia,
                        suspendido=instance.suspendido,
                        qr_code=qr_code,
                        qr_image='',
                        rut=instance.rut,
                        user=instance.user,
                        facebook='',
                        instagram='',
                        twitter='',
                        qr_secret=qr_secret,
                        fecha_vencimiento=instance.fecha_vencimiento,
                        profesor_asignado_id=instance.profesor_asignado_id if hasattr(instance, 'profesor_asignado_id') else None,
                        foto_perfil=''
                    )
                    print(f"[SIGNAL] Cliente {instance.nombre} creado automáticamente en entrenador_app")
                else:
                    print(f"[SIGNAL] Cliente {instance.nombre} ya existe en entrenador_app")
                    
            except ImportError as ie:
                print(f"[SIGNAL WARNING] No se pudo importar entrenador_app models: {ie}")
                print(f"[SIGNAL INFO] Cliente {instance.nombre} creado solo en admin_app")
            except Exception as inner_e:
                print(f"[SIGNAL ERROR] Error interno creando cliente en entrenador_app: {inner_e}")
                
        except Exception as e:
            print(f"[SIGNAL ERROR] Error general en signal: {e}")
