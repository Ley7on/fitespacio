from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections, OperationalError
import socket


class Command(BaseCommand):
    help = 'Diagnosticar la conexión a la base de datos definida en settings (useful for RDS connectivity)'

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=float, default=5.0, help='TCP connect timeout in seconds')

    def handle(self, *args, **options):
        db = settings.DATABASES.get('default')
        if not db:
            self.stderr.write('No se encontró configuración de base de datos `default` en settings.')
            return

        host = db.get('HOST') or 'localhost'
        port = int(db.get('PORT') or 3306)

        self.stdout.write(f'Probing TCP connectivity to {host}:{port} (timeout={options["timeout"]}s)')

        # 1) TCP-level check
        try:
            with socket.create_connection((host, port), timeout=options['timeout']):
                self.stdout.write(self.style.SUCCESS(f'TCP connection to {host}:{port} succeeded'))
        except socket.gaierror as e:
            self.stderr.write(self.style.ERROR(f'DNS resolution failed for host `{host}`: {e}'))
            self._print_quick_checks(host, port)
            return
        except socket.timeout:
            self.stderr.write(self.style.ERROR(f'Connection to {host}:{port} timed out.'))
            self._print_quick_checks(host, port)
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Low-level socket error connecting to {host}:{port}: {e}'))
            self._print_quick_checks(host, port)
            return

        # 2) Try a Django DB connection (application-level)
        self.stdout.write('Attempting Django DB connection (will use configured DB engine) ...')
        try:
            conn = connections['default']
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            row = cursor.fetchone()
            if row and row[0] == 1:
                self.stdout.write(self.style.SUCCESS('Django DB connection successful (SELECT 1 returned 1)'))
            else:
                self.stderr.write(self.style.ERROR('Django DB connected but test query did not return expected result.'))
        except OperationalError as oe:
            self.stderr.write(self.style.ERROR(f'Database OperationalError: {oe}'))
            self._print_quick_checks(host, port)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Unexpected error when testing Django DB connection: {e}'))

    def _print_quick_checks(self, host, port):
        self.stdout.write('\nQuick checks and remediation steps:')
        self.stdout.write('- Verifica que la instancia RDS permita conexiones desde tu IP (Security Group inbound rules permiten 3306).')
        self.stdout.write('- Si la RDS NO es pública, configura un bastion/SSH tunnel o VPN para acceder a la VPC.')
        self.stdout.write('- Prueba desde PowerShell:')
        self.stdout.write('  Test-NetConnection -ComputerName ' + host + ' -Port ' + str(port))
        self.stdout.write('- Desde Linux/macOS:')
        self.stdout.write('  nc -vz ' + host + ' ' + str(port) + '  # o `telnet <host> 3306`')
        self.stdout.write('- Revisa el firewall local / reglas de red de tu ISP o corporación (puertos salientes bloqueados).')
        self.stdout.write('- Asegúrate que las credenciales (USER/PASSWORD) en settings/.env son correctas y no expiraron.')
        self.stdout.write('- Si necesitas un túnel SSH (ejemplo):')
        self.stdout.write("  ssh -L 3307:%s:%d usuario@bastion-host -N" % (host, port))
        self.stdout.write('  y luego apunta DB_HOST=127.0.0.1 DB_PORT=3307')
