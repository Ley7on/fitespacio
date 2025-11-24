from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from admin_gym.models import Cliente, Profesor

class Command(BaseCommand):
    help = 'Elimina usuarios huérfanos que no tienen cliente o profesor asociado'

    def handle(self, *args, **options):
        usuarios_eliminados = 0
        
        for user in User.objects.all():
            # No eliminar superusuarios
            if user.is_superuser:
                continue
                
            # Verificar si tiene cliente o profesor asociado
            tiene_cliente = Cliente.objects.filter(user=user).exists()
            tiene_profesor = Profesor.objects.filter(user=user).exists()
            
            # Si no tiene ninguno, eliminarlo
            if not tiene_cliente and not tiene_profesor:
                self.stdout.write(f'Eliminando usuario huérfano: {user.username} ({user.email})')
                user.delete()
                usuarios_eliminados += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Eliminados {usuarios_eliminados} usuarios huérfanos')
        )