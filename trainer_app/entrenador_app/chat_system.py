from django.utils import timezone
from django.utils.html import escape
import json
import logging

logger = logging.getLogger(__name__)

class ChatMessage:
    def __init__(self, sender_id, sender_type, recipient_id, recipient_type, message, timestamp=None):
        self.sender_id = sender_id
        self.sender_type = sender_type  # 'entrenador' or 'alumno'
        self.recipient_id = recipient_id
        self.recipient_type = recipient_type
        self.message = escape(message)
        self.timestamp = timestamp or timezone.now()
        self.read = False
        self.id = f"{sender_id}_{recipient_id}_{int(self.timestamp.timestamp())}"

class ChatSystem:
    """Sistema de chat bidireccional entre entrenador y alumno"""
    
    # Simulamos una base de datos en memoria para demo
    _messages = []
    _conversations = {}
    
    @classmethod
    def send_message(cls, sender_id, sender_type, recipient_id, recipient_type, message):
        """Envía un mensaje entre entrenador y alumno"""
        chat_message = ChatMessage(
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            message=message
        )
        
        cls._messages.append(chat_message)
        
        # Crear/actualizar conversación
        conversation_key = cls._get_conversation_key(sender_id, sender_type, recipient_id, recipient_type)
        if conversation_key not in cls._conversations:
            cls._conversations[conversation_key] = {
                'participants': {
                    'entrenador': sender_id if sender_type == 'entrenador' else recipient_id,
                    'alumno': sender_id if sender_type == 'alumno' else recipient_id
                },
                'last_message': chat_message,
                'unread_count': {'entrenador': 0, 'alumno': 0}
            }
        else:
            cls._conversations[conversation_key]['last_message'] = chat_message
        
        # Incrementar contador de no leídos para el destinatario
        cls._conversations[conversation_key]['unread_count'][recipient_type] += 1
        
        logger.info(f"Message sent from {sender_type} {sender_id} to {recipient_type} {recipient_id}")
        
        return chat_message
    
    @classmethod
    def get_conversation(cls, user_id, user_type, other_id, other_type):
        """Obtiene una conversación específica"""
        conversation_key = cls._get_conversation_key(user_id, user_type, other_id, other_type)
        """
        Archivo archivado: el sistema de chat fue retirado del proyecto.

        Este fichero se mantiene para evitar errores de importación en módulos
        que referencien `entrenador_app.chat_system`. Las funciones y clases de
        chat han sido eliminadas. Si se necesita restaurar, recuperar desde VCS.
        """