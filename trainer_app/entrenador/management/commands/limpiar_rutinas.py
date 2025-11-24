"""
Comando para limpiar rutinas específicas de la base de datos
Uso: python manage.py limpiar_rutinas --nombre "zumba"
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from entrenador.models import Rutina, DetalleEjercicio
from alumno.models import RutinaAlumno, EjercicioRutinaAlumno
from entrenador_app.admin_gym_models import (
    AdminGymRutina, 
    AdminGymEjercicioRutina, 
    AdminGymRutinaCliente
)


class Command(BaseCommand):
    help = 'Elimina rutinas específicas por nombre de todas las tablas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--nombre',
            type=str,
            help='Nombre de la rutina a eliminar (busca coincidencias parciales)',
            required=False
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma la eliminación (sin esto solo muestra lo que se eliminaría)',
        )

    def handle(self, *args, **options):
        nombre = options.get('nombre')
        confirmar = options['confirmar']
        
        # Si no se proporciona nombre, listar todas las rutinas
        if not nombre:
            self.listar_todas_rutinas()
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Buscando rutinas que contengan: '{nombre}'")
        self.stdout.write(f"{'='*60}\n")
        
        total_eliminadas = 0
        
        # 1. Buscar en tablas nuevas (entrenador.Rutina)
        rutinas_nuevas = Rutina.objects.filter(nombre__icontains=nombre)
        if rutinas_nuevas.exists():
            self.stdout.write(f"\n📋 Rutinas en entrenador_rutina: {rutinas_nuevas.count()}")
            for rutina in rutinas_nuevas:
                self.stdout.write(f"  - ID {rutina.id}: {rutina.nombre} (creada por {rutina.entrenador.username})")
                
                # Contar asignaciones
                asignaciones = RutinaAlumno.objects.filter(rutina_entrenador=rutina)
                ejercicios = DetalleEjercicio.objects.filter(rutina=rutina)
                
                self.stdout.write(f"    • {asignaciones.count()} asignaciones a alumnos")
                self.stdout.write(f"    • {ejercicios.count()} ejercicios")
                
                if confirmar:
                    with transaction.atomic():
                        # Eliminar ejercicios de rutinas de alumnos
                        for asig in asignaciones:
                            count_ej = EjercicioRutinaAlumno.objects.filter(rutina=asig).count()
                            EjercicioRutinaAlumno.objects.filter(rutina=asig).delete()
                            self.stdout.write(f"      ✓ Eliminados {count_ej} ejercicios de RutinaAlumno {asig.id}")
                        
                        # Eliminar asignaciones
                        count_asig = asignaciones.count()
                        asignaciones.delete()
                        self.stdout.write(f"      ✓ Eliminadas {count_asig} asignaciones")
                        
                        # Eliminar ejercicios de la rutina
                        count_ej = ejercicios.count()
                        ejercicios.delete()
                        self.stdout.write(f"      ✓ Eliminados {count_ej} ejercicios")
                        
                        # Eliminar la rutina
                        rutina.delete()
                        self.stdout.write(self.style.SUCCESS(f"      ✓ Rutina {rutina.id} eliminada"))
                        total_eliminadas += 1
        
        # 2. Buscar en alumno.RutinaAlumno (rutinas huérfanas sin rutina_entrenador)
        rutinas_alumno_huerfanas = RutinaAlumno.objects.filter(
            nombre__icontains=nombre,
            rutina_entrenador__isnull=True
        )
        if rutinas_alumno_huerfanas.exists():
            self.stdout.write(f"\n📋 Rutinas huérfanas en alumno_rutinaalumno: {rutinas_alumno_huerfanas.count()}")
            for rutina in rutinas_alumno_huerfanas:
                self.stdout.write(f"  - ID {rutina.id}: {rutina.nombre} (alumno: {rutina.alumno.user.username})")
                ejercicios_count = EjercicioRutinaAlumno.objects.filter(rutina=rutina).count()
                self.stdout.write(f"    • {ejercicios_count} ejercicios")
                
                if confirmar:
                    EjercicioRutinaAlumno.objects.filter(rutina=rutina).delete()
                    rutina.delete()
                    self.stdout.write(self.style.SUCCESS(f"      ✓ Rutina huérfana {rutina.id} eliminada"))
                    total_eliminadas += 1
        
        # 3. Buscar en tablas antiguas (admin_gym_rutina)
        rutinas_antiguas = AdminGymRutina.objects.filter(nombre__icontains=nombre)
        if rutinas_antiguas.exists():
            self.stdout.write(f"\n📋 Rutinas en admin_gym_rutina: {rutinas_antiguas.count()}")
            for rutina in rutinas_antiguas:
                self.stdout.write(f"  - ID {rutina.id}: {rutina.nombre}")
                
                asignaciones = AdminGymRutinaCliente.objects.filter(rutina=rutina)
                ejercicios = AdminGymEjercicioRutina.objects.filter(rutina=rutina)
                
                self.stdout.write(f"    • {asignaciones.count()} asignaciones a clientes")
                self.stdout.write(f"    • {ejercicios.count()} ejercicios")
                
                if confirmar:
                    with transaction.atomic():
                        asignaciones.delete()
                        ejercicios.delete()
                        rutina.delete()
                        self.stdout.write(self.style.SUCCESS(f"      ✓ Rutina antigua {rutina.id} eliminada"))
                        total_eliminadas += 1
        
        # Resumen
        self.stdout.write(f"\n{'='*60}")
        if confirmar:
            if total_eliminadas > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"✅ {total_eliminadas} rutinas eliminadas correctamente"
                ))
            else:
                self.stdout.write(self.style.WARNING("⚠️  No se encontraron rutinas para eliminar"))
        else:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  MODO SIMULACIÓN: No se eliminó nada. Usa --confirmar para eliminar realmente."
            ))
        self.stdout.write(f"{'='*60}\n")
    
    def listar_todas_rutinas(self):
        """Lista todas las rutinas en el sistema"""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("LISTADO DE TODAS LAS RUTINAS EN EL SISTEMA")
        self.stdout.write(f"{'='*60}\n")
        
        # Rutinas nuevas
        rutinas_nuevas = Rutina.objects.all()
        self.stdout.write(f"\n📋 entrenador_rutina: {rutinas_nuevas.count()} rutinas")
        for r in rutinas_nuevas[:10]:  # Primeras 10
            self.stdout.write(f"  - ID {r.id}: {r.nombre} (entrenador: {r.entrenador.username})")
        
        # Rutinas de alumnos
        rutinas_alumnos = RutinaAlumno.objects.all()
        self.stdout.write(f"\n📋 alumno_rutinaalumno: {rutinas_alumnos.count()} rutinas")
        for r in rutinas_alumnos[:10]:
            self.stdout.write(f"  - ID {r.id}: {r.nombre} (alumno: {r.alumno.user.username})")
        
        # Rutinas antiguas
        rutinas_antiguas = AdminGymRutina.objects.all()
        self.stdout.write(f"\n📋 admin_gym_rutina: {rutinas_antiguas.count()} rutinas")
        for r in rutinas_antiguas[:10]:
            self.stdout.write(f"  - ID {r.id}: {r.nombre}")
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Usa --nombre 'nombre_rutina' para buscar rutinas específicas")
        self.stdout.write(f"{'='*60}\n")
