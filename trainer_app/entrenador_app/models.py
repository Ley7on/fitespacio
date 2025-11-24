# entrenador_app/models.py - Modelos para chat y notificaciones

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ChatConversacion(models.Model):
    alumno = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_alumno')
    entrenador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_entrenador')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['alumno', 'entrenador']
        db_table = 'entrenador_app_chatconversacion'
    
    def __str__(self):
        # archivo archivado: devolver identificador mínimo para evitar errores
        return f"Chat #{self.pk or 'unknown'}"


"""
Archivo archivado: el subsystem de chat fue eliminado del proyecto.

Este fichero se deja vacío a propósito para evitar import errors en puntos
del código que importen el módulo como referencia histórica. Las clases de
chat fueron removidas del modelo y las consultas sobre `entrenador_chat*`
deben haber sido eliminadas.

Si necesitas restaurar el chat en el futuro, recupera este archivo desde
control de versiones.
"""