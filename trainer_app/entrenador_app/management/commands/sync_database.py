# entrenador_app/management/commands/sync_database.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sincroniza y valida la base de datos del sistema entrenador'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corregir problemas encontrados automáticamente',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando sincronización de base de datos...'))
        
        # 1. Verificar tablas principales
        self.verificar_tablas_principales()
        
        # 2. Crear tablas faltantes
        if options['fix']:
            self.crear_tablas_faltantes()
        
        # 3. Validar datos
        self.validar_datos()
        
        # 4. Sincronizar usuarios
        if options['fix']:
            self.sincronizar_usuarios()
        
        self.stdout.write(self.style.SUCCESS('Sincronización completada.'))

    def verificar_tablas_principales(self):
        """Verifica que existan las tablas principales del sistema"""
        tablas_requeridas = [
            'admin_gym_cliente',
            'admin_gym_profesor',
            'admin_gym_rutina',
            'admin_gym_ejercicio',
            'admin_gym_ejerciciorutina',
            'admin_gym_rutinacliente',
            'admin_gym_asistencia',
            'entrenador_asistenciaentrenador',
        ]
        
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tablas_existentes = [tabla[0] for tabla in cursor.fetchall()]
            
            for tabla in tablas_requeridas:
                if tabla in tablas_existentes:
                    self.stdout.write(f"[OK] Tabla {tabla} existe")
                else:
                    self.stdout.write(self.style.ERROR(f"[ERROR] Tabla {tabla} NO existe"))

    def crear_tablas_faltantes(self):
        """Crea las tablas que faltan en el sistema"""
        with connection.cursor() as cursor:
            # Tabla de asistencia de entrenadores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entrenador_asistenciaentrenador (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    entrenador_id INT NOT NULL,
                    fecha DATE NOT NULL,
                    hora_entrada TIME NOT NULL,
                    hora_salida TIME NULL,
                    notas TEXT,
                    UNIQUE KEY unique_entrenador_fecha (entrenador_id, fecha),
                    FOREIGN KEY (entrenador_id) REFERENCES auth_user(id)
                )
            """)
            
            self.stdout.write(self.style.SUCCESS("Tablas creadas/verificadas correctamente"))

    def validar_datos(self):
        """Valida la integridad de los datos"""
        with connection.cursor() as cursor:
            # Verificar clientes activos
            cursor.execute("SELECT COUNT(*) FROM admin_gym_cliente WHERE activo = 1")
            clientes_activos = cursor.fetchone()[0]
            self.stdout.write(f"Clientes activos: {clientes_activos}")
            
            # Verificar rutinas
            cursor.execute("SELECT COUNT(*) FROM admin_gym_rutina")
            total_rutinas = cursor.fetchone()[0]
            self.stdout.write(f"Total rutinas: {total_rutinas}")
            
            # Verificar asistencias
            cursor.execute("SELECT COUNT(*) FROM admin_gym_asistencia WHERE fecha >= CURDATE() - INTERVAL 30 DAY")
            asistencias_mes = cursor.fetchone()[0]
            self.stdout.write(f"Asistencias último mes: {asistencias_mes}")
            
            # Verificar usuarios sin vincular
            cursor.execute("""
                SELECT COUNT(*) FROM admin_gym_cliente 
                WHERE user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user)
            """)
            clientes_sin_usuario = cursor.fetchone()[0]
            if clientes_sin_usuario > 0:
                self.stdout.write(self.style.WARNING(f"Clientes sin usuario vinculado: {clientes_sin_usuario}"))

    def sincronizar_usuarios(self):
        """Sincroniza usuarios entre las tablas"""
        with connection.cursor() as cursor:
            # Buscar clientes sin usuario vinculado
            cursor.execute("""
                SELECT id, nombre, email, rut FROM admin_gym_cliente 
                WHERE user_id IS NULL AND email != ''
            """)
            
            clientes_sin_usuario = cursor.fetchall()
            
            for cliente_id, nombre, email, rut in clientes_sin_usuario:
                # Buscar usuario existente por email
                try:
                    user = User.objects.get(email=email)
                    cursor.execute("""
                        UPDATE admin_gym_cliente SET user_id = %s WHERE id = %s
                    """, [user.id, cliente_id])
                    self.stdout.write(f"Usuario vinculado: {email} -> Cliente {cliente_id}")
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Usuario no encontrado para: {email}"))