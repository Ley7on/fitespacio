from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from admin_gym.models import Profesor, PerfilUsuario
from admin_gym.utils import generar_password_temporal

class Command(BaseCommand):
    help = 'Resetea la contraseña de un usuario'

    def add_arguments(self, parser):
        parser.add_argument('rut', type=str, help='RUT del usuario')

    def handle(self, *args, **options):
        rut = options['rut']
        
        try:
            profesor = Profesor.objects.get(rut=rut)
            if profesor.user:
                nueva_password = generar_password_temporal()
                profesor.user.set_password(nueva_password)
                profesor.user.save()
                
                # Asegurar que debe cambiar password
                perfil, created = PerfilUsuario.objects.get_or_create(
                    user=profesor.user,
                    defaults={
                        'rol': 'entrenador',
                        'debe_cambiar_password': True,
                        'activo': True
                    }
                )
                perfil.debe_cambiar_password = True
                perfil.save()
                
                self.stdout.write(f"✅ Password reseteada para {profesor.nombre}")
                self.stdout.write(f"   RUT: {rut}")
                self.stdout.write(f"   Nueva contraseña: {nueva_password}")
                self.stdout.write(f"   Usuario debe cambiar contraseña: {perfil.debe_cambiar_password}")
            else:
                self.stdout.write(f"❌ Profesor {profesor.nombre} no tiene usuario asociado")
                
        except Profesor.DoesNotExist:
            self.stdout.write(f"❌ No se encontró profesor con RUT: {rut}")