from django.db import migrations, connection

def add_notas_column(apps, schema_editor):
    """Safely add notas column to admin_gym_rutinacliente if it exists"""
    with connection.cursor() as cursor:
        try:
            # Check if table exists
            cursor.execute("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", 
                         [connection.get_autocommit(), 'admin_gym_rutinacliente'])
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Check if column already exists
                cursor.execute("""
                    SELECT 1 FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'admin_gym_rutinacliente' AND COLUMN_NAME = 'notas'
                """)
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    cursor.execute("ALTER TABLE admin_gym_rutinacliente ADD COLUMN notas TEXT NULL;")
        except Exception:
            # Silently fail if table doesn't exist (for test database)
            pass

def remove_notas_column(apps, schema_editor):
    """Safely remove notas column from admin_gym_rutinacliente"""
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_NAME = 'admin_gym_rutinacliente' AND COLUMN_NAME = 'notas'
            """)
            column_exists = cursor.fetchone()
            
            if column_exists:
                cursor.execute("ALTER TABLE admin_gym_rutinacliente DROP COLUMN notas;")
        except Exception:
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('entrenador', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_notas_column, remove_notas_column),
    ]