from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from alumno.models import PerfilAlumno, Ejercicio
from entrenador.models import Ejercicio as EntrenadorEjercicio
from entrenador_app.models import SystemConfiguration
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup database with initial data for FitSpace application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all data (WARNING: This will delete existing data)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database setup...'))
        
        try:
            with transaction.atomic():
                if options['reset']:
                    self.reset_data()
                
                self.create_groups_and_permissions()
                self.create_default_users()
                self.create_exercises()
                self.create_system_configuration()
                
            self.stdout.write(self.style.SUCCESS('Database setup completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during setup: {str(e)}'))
            logger.error(f'Database setup error: {str(e)}')

    def reset_data(self):
        """Reset all data - use with caution"""
        self.stdout.write(self.style.WARNING('Resetting all data...'))
        
        # Delete users except superusers
        User.objects.filter(is_superuser=False).delete()
        
        # Delete exercises
        Ejercicio.objects.all().delete()
        if hasattr(EntrenadorEjercicio, 'objects'):
            EntrenadorEjercicio.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('Data reset completed'))

    def create_groups_and_permissions(self):
        """Create user groups and assign permissions"""
        self.stdout.write('Creating user groups and permissions...')
        
        # Create groups
        entrenadores_group, created = Group.objects.get_or_create(name='Entrenadores')
        alumnos_group, created = Group.objects.get_or_create(name='Alumnos')
        
        # Get content types
        user_ct = ContentType.objects.get_for_model(User)
        perfil_ct = ContentType.objects.get_for_model(PerfilAlumno)
        
        # Trainer permissions
        trainer_permissions = [
            'add_user', 'change_user', 'view_user',
            'add_perfilalumno', 'change_perfilalumno', 'view_perfilalumno',
        ]
        
        for perm_codename in trainer_permissions:
            try:
                permission = Permission.objects.get(codename=perm_codename)
                entrenadores_group.permissions.add(permission)
            except Permission.DoesNotExist:
                self.stdout.write(f'Permission {perm_codename} not found')
        
        # Student permissions (view only for their own data)
        student_permissions = [
            'view_perfilalumno',
        ]
        
        for perm_codename in student_permissions:
            try:
                permission = Permission.objects.get(codename=perm_codename)
                alumnos_group.permissions.add(permission)
            except Permission.DoesNotExist:
                self.stdout.write(f'Permission {perm_codename} not found')
        
        self.stdout.write(self.style.SUCCESS('Groups and permissions created'))

    def create_default_users(self):
        """Create default users for testing"""
        self.stdout.write('Creating default users...')
        
        # Create trainer user
        if not User.objects.filter(username='entrenador').exists():
            trainer = User.objects.create_user(
                username='entrenador',
                email='entrenador@fitspace.com',
                password='FitSpace2024!',
                first_name='Juan',
                last_name='Pérez',
                is_staff=True
            )
            trainer.groups.add(Group.objects.get(name='Entrenadores'))
            self.stdout.write('Trainer user created')
        
        # Create student user
        if not User.objects.filter(username='alumno').exists():
            student = User.objects.create_user(
                username='alumno',
                email='alumno@fitspace.com',
                password='FitSpace2024!',
                first_name='María',
                last_name='García'
            )
            student.groups.add(Group.objects.get(name='Alumnos'))
            
            # Create student profile
            PerfilAlumno.objects.create(
                user=student,
                telefono='+1234567890',
                fecha_nacimiento='1995-01-01',
                plan='basic',
                estado='activo'
            )
            self.stdout.write('Student user and profile created')

    def create_exercises(self):
        """Create default exercises"""
        self.stdout.write('Creating default exercises...')
        
        exercises_data = [
            # Tren Superior - Empuje
            {
                'nombre': 'Press de Banca',
                'categoria': 'empuje',
                'descripcion': 'Ejercicio básico para pecho, hombros y tríceps',
                'maquina_requerida': 'Banco con barra',
                'imagen': 'press_banca.jpg',
                'musculos_principales': 'Pectorales, Deltoides anterior, Tríceps'
            },
            {
                'nombre': 'Press Militar',
                'categoria': 'empuje',
                'descripcion': 'Ejercicio para desarrollo de hombros',
                'maquina_requerida': 'Barra o mancuernas',
                'imagen': 'press_militar.jpg',
                'musculos_principales': 'Deltoides, Tríceps, Core'
            },
            {
                'nombre': 'Flexiones',
                'categoria': 'empuje',
                'descripcion': 'Ejercicio corporal para pecho y brazos',
                'maquina_requerida': 'Ninguna',
                'imagen': 'flexiones.jpg',
                'musculos_principales': 'Pectorales, Tríceps, Core'
            },
            
            # Tren Superior - Tracción
            {
                'nombre': 'Dominadas',
                'categoria': 'traccion',
                'descripcion': 'Ejercicio para espalda y bíceps',
                'maquina_requerida': 'Barra de dominadas',
                'imagen': 'dominadas.jpg',
                'musculos_principales': 'Dorsales, Bíceps, Romboides'
            },
            {
                'nombre': 'Remo con Barra',
                'categoria': 'traccion',
                'descripcion': 'Ejercicio para desarrollo de espalda',
                'maquina_requerida': 'Barra',
                'imagen': 'remo_barra.jpg',
                'musculos_principales': 'Dorsales, Romboides, Bíceps'
            },
            {
                'nombre': 'Jalones al Pecho',
                'categoria': 'traccion',
                'descripcion': 'Ejercicio en máquina para espalda',
                'maquina_requerida': 'Máquina de jalones',
                'imagen': 'jalones.jpg',
                'musculos_principales': 'Dorsales, Bíceps'
            },
            
            # Tren Inferior
            {
                'nombre': 'Sentadillas',
                'categoria': 'piernas',
                'descripcion': 'Ejercicio fundamental para piernas',
                'maquina_requerida': 'Barra o peso corporal',
                'imagen': 'sentadillas.jpg',
                'musculos_principales': 'Cuádriceps, Glúteos, Isquiotibiales'
            },
            {
                'nombre': 'Peso Muerto',
                'categoria': 'piernas',
                'descripcion': 'Ejercicio completo para tren inferior y espalda',
                'maquina_requerida': 'Barra',
                'imagen': 'peso_muerto.jpg',
                'musculos_principales': 'Isquiotibiales, Glúteos, Espalda baja'
            },
            {
                'nombre': 'Zancadas',
                'categoria': 'piernas',
                'descripcion': 'Ejercicio unilateral para piernas',
                'maquina_requerida': 'Mancuernas o peso corporal',
                'imagen': 'zancadas.jpg',
                'musculos_principales': 'Cuádriceps, Glúteos'
            },
            
            # Core
            {
                'nombre': 'Plancha',
                'categoria': 'core',
                'descripcion': 'Ejercicio isométrico para core',
                'maquina_requerida': 'Ninguna',
                'imagen': 'plancha.jpg',
                'musculos_principales': 'Abdominales, Core'
            },
            {
                'nombre': 'Abdominales',
                'categoria': 'core',
                'descripcion': 'Ejercicio básico para abdomen',
                'maquina_requerida': 'Ninguna',
                'imagen': 'abdominales.jpg',
                'musculos_principales': 'Recto abdominal'
            },
        ]
        
        for exercise_data in exercises_data:
            exercise, created = Ejercicio.objects.get_or_create(
                nombre=exercise_data['nombre'],
                defaults=exercise_data
            )
            if created:
                self.stdout.write(f'Created exercise: {exercise.nombre}')

    def create_system_configuration(self):
        """Create system configuration entries"""
        self.stdout.write('Creating system configuration...')
        
        configs = [
            {
                'key': 'app_version',
                'value': '1.0.0',
                'description': 'Current application version',
                'category': 'system'
            },
            {
                'key': 'maintenance_mode',
                'value': 'false',
                'description': 'Enable/disable maintenance mode',
                'category': 'system'
            },
            {
                'key': 'max_login_attempts',
                'value': '5',
                'description': 'Maximum login attempts before lockout',
                'category': 'security'
            },
            {
                'key': 'session_timeout',
                'value': '3600',
                'description': 'Session timeout in seconds',
                'category': 'security'
            },
            {
                'key': 'backup_frequency',
                'value': 'daily',
                'description': 'Database backup frequency',
                'category': 'backup'
            },
            {
                'key': 'quality_target_satisfaction',
                'value': '95.0',
                'description': 'Target user satisfaction percentage',
                'category': 'quality'
            },
        ]
        
        for config_data in configs:
            config, created = SystemConfiguration.objects.get_or_create(
                key=config_data['key'],
                defaults=config_data
            )
            if created:
                self.stdout.write(f'Created config: {config.key}')
        
        self.stdout.write(self.style.SUCCESS('System configuration created'))

    def create_superuser_if_needed(self):
        """Create superuser if none exists"""
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write('Creating superuser...')
            User.objects.create_superuser(
                username='admin',
                email='admin@fitspace.com',
                password='FitSpaceAdmin2024!'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created'))