# Generated manually to fix foreign key type mismatch

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('alumno', '0013_ejerciciorutinaalumno_ejercicio_entrenador_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE `alumno_sesionentrenamiento` (
                `id` int AUTO_INCREMENT NOT NULL PRIMARY KEY,
                `alumno_id` int NOT NULL,
                `rutina_id` bigint NULL,
                `rutina_nombre` varchar(150) NOT NULL,
                `fecha` date NOT NULL,
                `fecha_hora` datetime(6) NOT NULL,
                `notas` longtext NOT NULL,
                UNIQUE KEY `alumno_sesionentrenamien_alumno_id_rutina_id_fech_55dac6d5_uniq` (`alumno_id`, `rutina_id`, `fecha`),
                KEY `alumno_sesionentrena_rutina_id_a2e41b5f_fk_alumno_ru` (`rutina_id`),
                CONSTRAINT `alumno_sesionentrena_alumno_id_1ea080bd_fk_alumno_pe` 
                    FOREIGN KEY (`alumno_id`) REFERENCES `alumno_perfilalumno` (`id`) ON DELETE CASCADE,
                CONSTRAINT `alumno_sesionentrena_rutina_id_a2e41b5f_fk_alumno_ru` 
                    FOREIGN KEY (`rutina_id`) REFERENCES `alumno_rutinaalumno` (`id`) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """,
            reverse_sql="DROP TABLE IF EXISTS `alumno_sesionentrenamiento`;"
        ),
    ]
