# Generated manually to fix cascade and unique constraint

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('alumno', '0014_sesionentrenamiento'),
    ]

    operations = [
        # Primero eliminar el constraint de FK antiguo
        migrations.RunSQL(
            sql="ALTER TABLE `alumno_sesionentrenamiento` DROP FOREIGN KEY `alumno_sesionentrena_rutina_id_a2e41b5f_fk_alumno_ru`;",
            reverse_sql="ALTER TABLE `alumno_sesionentrenamiento` ADD CONSTRAINT `alumno_sesionentrena_rutina_id_a2e41b5f_fk_alumno_ru` FOREIGN KEY (`rutina_id`) REFERENCES `alumno_rutinaalumno` (`id`) ON DELETE SET NULL;"
        ),
        # Luego eliminar el constraint único
        migrations.RunSQL(
            sql="ALTER TABLE `alumno_sesionentrenamiento` DROP INDEX `alumno_sesionentrenamien_alumno_id_rutina_id_fech_55dac6d5_uniq`;",
            reverse_sql="ALTER TABLE `alumno_sesionentrenamiento` ADD UNIQUE KEY `alumno_sesionentrenamien_alumno_id_rutina_id_fech_55dac6d5_uniq` (`alumno_id`, `rutina_id`, `fecha`);"
        ),
        # Agregar el nuevo constraint con CASCADE
        migrations.RunSQL(
            sql="ALTER TABLE `alumno_sesionentrenamiento` ADD CONSTRAINT `alumno_sesionentrena_rutina_id_a2e41b5f_fk_alumno_ru` FOREIGN KEY (`rutina_id`) REFERENCES `alumno_rutinaalumno` (`id`) ON DELETE CASCADE;",
            reverse_sql="ALTER TABLE `alumno_sesionentrenamiento` DROP FOREIGN KEY `alumno_sesionentrena_rutina_id_a2e41b5f_fk_alumno_ru`;"
        ),
    ]
