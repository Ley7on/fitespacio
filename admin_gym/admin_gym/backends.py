from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import Cliente, Profesor

class RUTAuthenticationBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Buscar por RUT en Cliente
        try:
            cliente = Cliente.objects.get(rut=username, activo=True)
            if cliente.user and cliente.user.is_active and cliente.user.check_password(password):
                return cliente.user
        except Cliente.DoesNotExist:
            pass
        
        # Buscar por RUT en Profesor
        try:
            profesor = Profesor.objects.get(rut=username)
            if profesor.user and profesor.user.is_active and profesor.user.check_password(password):
                return profesor.user
        except Profesor.DoesNotExist:
            pass
        
        # Fallback: autenticación normal por username (solo superusers)
        try:
            user = User.objects.get(username=username, is_active=True)
            if user.is_superuser and user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None