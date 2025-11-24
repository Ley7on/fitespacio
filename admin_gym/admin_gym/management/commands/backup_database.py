from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import subprocess
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    RNF-02: Backup automático de base de datos diaria
    Comando para realizar backup de la base de datos
    """
    help = 'Realiza backup de la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directorio donde guardar el backup (default: backups)'
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Días de backups a mantener (default: 30)'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        keep_days = options['keep_days']
        
        self.stdout.write("Iniciando backup de base de datos...")
        
        # Crear directorio de backup si no existe
        backup_path = Path(output_dir)
        backup_path.mkdir(exist_ok=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        db_config = settings.DATABASES['default']
        
        if db_config['ENGINE'] == 'django.db.backends.mysql':
            backup_file = backup_path / f"gym_backup_{timestamp}.sql"
            success = self.backup_mysql(db_config, backup_file)
        elif db_config['ENGINE'] == 'django.db.backends.sqlite3':
            backup_file = backup_path / f"gym_backup_{timestamp}.sqlite3"
            success = self.backup_sqlite(db_config, backup_file)
        else:
            self.stdout.write(
                self.style.ERROR(f"Motor de BD no soportado: {db_config['ENGINE']}")
            )
            return
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Backup completado: {backup_file}")
            )
            
            # Limpiar backups antiguos
            self.cleanup_old_backups(backup_path, keep_days)
            
            # Log del backup
            logger.info(f"Backup exitoso: {backup_file}")
        else:
            self.stdout.write(
                self.style.ERROR("Error durante el backup")
            )
            logger.error("Error durante el backup de base de datos")

    def backup_mysql(self, db_config, backup_file):
        """Realizar backup de MySQL usando mysqldump"""
        try:
            cmd = [
                'mysqldump',
                f"--host={db_config['HOST']}",
                f"--port={db_config['PORT']}",
                f"--user={db_config['USER']}",
                '--single-transaction',
                '--routines',
                '--triggers',
                db_config['NAME']
            ]
            
            # Agregar password si existe
            if db_config['PASSWORD']:
                cmd.append(f"--password={db_config['PASSWORD']}")
            
            # Ejecutar mysqldump
            with open(backup_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5 minutos timeout
                )
            
            if result.returncode == 0:
                # Comprimir el archivo
                self.compress_file(backup_file)
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(f"Error mysqldump: {result.stderr}")
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.ERROR("Timeout durante el backup")
            )
            return False
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR("mysqldump no encontrado. Instalar MySQL client.")
            )
            return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error durante backup: {e}")
            )
            return False

    def backup_sqlite(self, db_config, backup_file):
        """Realizar backup de SQLite usando VACUUM INTO para consistencia"""
        try:
            import sqlite3
            
            db_path = db_config['NAME']
            if not os.path.exists(db_path):
                self.stdout.write(
                    self.style.ERROR(f"Archivo de BD no encontrado: {db_path}")
                )
                return False
            
            # Usar VACUUM INTO para backup consistente
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(f"VACUUM INTO '{backup_file}'")
                conn.close()
            except sqlite3.OperationalError:
                # Fallback para versiones antiguas de SQLite
                conn.close()
                import shutil
                shutil.copy2(db_path, backup_file)
            
            # Comprimir
            self.compress_file(backup_file)
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error durante backup SQLite: {e}")
            )
            return False

    def compress_file(self, file_path):
        """Comprimir archivo de backup usando gzip"""
        try:
            import gzip
            import shutil
            
            compressed_file = f"{file_path}.gz"
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Eliminar archivo original
            os.remove(file_path)
            
            self.stdout.write(f"Archivo comprimido: {compressed_file}")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"No se pudo comprimir: {e}")
            )

    def cleanup_old_backups(self, backup_dir, keep_days):
        """Eliminar backups antiguos"""
        try:
            cutoff_date = timezone.now() - timezone.timedelta(days=keep_days)
            
            deleted_count = 0
            for backup_file in backup_dir.glob("gym_backup_*"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                self.stdout.write(f"Eliminados {deleted_count} backups antiguos")
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Error limpiando backups antiguos: {e}")
            )

    def verify_backup(self, backup_file):
        """Verificar integridad del backup"""
        try:
            if backup_file.suffix == '.gz':
                import gzip
                with gzip.open(backup_file, 'rt') as f:
                    # Leer primeras líneas para verificar
                    first_lines = [f.readline() for _ in range(5)]
                    return any('CREATE' in line or 'INSERT' in line for line in first_lines)
            else:
                with open(backup_file, 'r') as f:
                    first_lines = [f.readline() for _ in range(5)]
                    return any('CREATE' in line or 'INSERT' in line for line in first_lines)
                    
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"No se pudo verificar backup: {e}")
            )
            return False