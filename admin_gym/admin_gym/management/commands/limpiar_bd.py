from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from admin_gym.models import Cliente, Profesor

class Command(BaseCommand):
    help = 'Elimina todos los clientes y profesores de la base de datos'

    def handle(self, *args, **options):
        # Eliminar todos los clientes
        clientes_count = Cliente.objects.count()
        for cliente in Cliente.objects.all():
            if cliente.user:
                cliente.user.delete()
            cliente.delete()
        
        # Eliminar todos los profesores
        profesores_count = Profesor.objects.count()
        for profesor in Profesor.objects.all():
            if profesor.user:
                profesor.user.delete()
            profesor.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Eliminados {clientes_count} clientes y {profesores_count} profesores de la base de datos'
            )
        )