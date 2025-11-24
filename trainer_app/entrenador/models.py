# entrenador/models.py - Sistema avanzado de rutinas

from django.db import models
from django.conf import settings
from django.utils.html import escape
from django.utils import timezone
from datetime import date, timedelta

class RutinaAlumnos(models.Model):
    rutina = models.ForeignKey('Rutina', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        db_table = 'entrenador_rutina_alumnos'
        unique_together = ('rutina', 'user')

class Ejercicio(models.Model):
    nombre = models.CharField(max_length=100)
    grupo_muscular = models.CharField(max_length=50)
    categoria = models.CharField(max_length=50, default='fuerza')
    descripcion = models.TextField(blank=True)
    video = models.FileField(upload_to='exercises/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    imagen_url = models.URLField(blank=True)

    def __str__(self):
        return escape(self.nombre)

class Rutina(models.Model):
    OBJETIVO_CHOICES = [
        ('fuerza', 'Fuerza'),
        ('hipertrofia', 'Hipertrofia'),
        ('resistencia', 'Resistencia'),
        ('perdida_grasa', 'Pérdida de grasa'),
        ('funcional', 'Entrenamiento Funcional'),
        ('rehabilitacion', 'Rehabilitación'),
    ]
    
    DIFICULTAD_CHOICES = [
        ('principiante', 'Principiante'),
        ('intermedio', 'Intermedio'),
        ('avanzado', 'Avanzado'),
        ('experto', 'Experto'),
    ]
    
    TIPO_CHOICES = [
        ('plantilla', 'Plantilla'),
        ('personalizada', 'Personalizada'),
        ('auto_generada', 'Auto-generada'),
    ]
    
    STATUS_CHOICES = [
        ('activa', 'Activa'),
        ('pausada', 'Pausada'),
        ('completada', 'Completada'),
        ('archivada', 'Archivada'),
    ]
    
    nombre = models.CharField(max_length=150)
    objetivo = models.CharField(max_length=20, choices=OBJETIVO_CHOICES, default='hipertrofia')
    dificultad = models.CharField(max_length=20, choices=DIFICULTAD_CHOICES, default='intermedio')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='personalizada')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='activa')
    duracion_estimada = models.PositiveIntegerField(default=60)
    frecuencia_semanal = models.PositiveIntegerField(default=3)
    semanas_duracion = models.PositiveIntegerField(default=4)
    tags = models.CharField(max_length=300, blank=True)
    descripcion = models.TextField(blank=True)
    notas_entrenador = models.TextField(blank=True)
    
    # Relaciones
    alumnos = models.ManyToManyField(settings.AUTH_USER_MODEL, through='RutinaAlumnos', related_name='rutinas_asignadas', blank=True)
    entrenador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rutinas_creadas')
    plantilla_base = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rutinas_derivadas')
    
    # Métricas y seguimiento
    veces_completada = models.PositiveIntegerField(default=0)
    rating_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    ultima_sesion = models.DateTimeField(null=True, blank=True)
    progreso_porcentaje = models.PositiveIntegerField(default=0)
    
    # Fechas
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)  # Cambiado de auto_now_add
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_actualizacion']
        indexes = [
            models.Index(fields=['entrenador', 'tipo']),
            models.Index(fields=['objetivo', 'dificultad']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        if self.tipo == 'plantilla':
            return f"📋 {self.nombre}"
        # Mostrar número de alumnos asignados si los hay
        try:
            if self.alumnos.exists():
                count = self.alumnos.count()
                return f"🏋️ {self.nombre} - {count} alumno{'' if count == 1 else 's'}"
        except Exception:
            pass
        return f"🏋️ {self.nombre}"
    
    @property
    def es_plantilla(self):
        return self.tipo == 'plantilla'
    
    @property
    def total_ejercicios(self):
        return self.ejercicios.count()
    
    def puede_ser_editada_por(self, usuario):
        # Entrenador siempre puede editar. Un alumno asignado puede editar solo si no es plantilla.
        if self.entrenador == usuario:
            return True
        if usuario and self.tipo != 'plantilla':
            try:
                return self.alumnos.filter(pk=getattr(usuario, 'pk', None)).exists()
            except Exception:
                return False
        return False

class DetalleEjercicio(models.Model):
    TIPO_CHOICES = [
        ('fuerza', 'Fuerza'),
        ('cardio', 'Cardio'),
        ('flexibilidad', 'Flexibilidad'),
        ('funcional', 'Funcional'),
    ]
    
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, related_name='ejercicios')
    nombre_ejercicio = models.CharField(max_length=150, default='Ejercicio sin nombre')
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='fuerza')
    
    # Configuración del ejercicio
    series = models.PositiveIntegerField(default=3)
    repeticiones = models.CharField(max_length=30, default="10-12")
    peso_inicial = models.CharField(max_length=50, blank=True)
    peso_objetivo = models.CharField(max_length=50, blank=True)
    tempo = models.CharField(max_length=20, blank=True)
    descanso = models.CharField(max_length=50, default="60-90s")
    rpe_objetivo = models.PositiveIntegerField(null=True, blank=True, help_text="RPE 1-10")
    
    # Progresiones y variaciones
    progresion_automatica = models.BooleanField(default=True)
    incremento_peso = models.CharField(max_length=20, default="2.5kg")
    incremento_reps = models.PositiveIntegerField(default=1)
    
    # Metadatos
    notas = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    imagen_url = models.URLField(blank=True)
    orden = models.PositiveIntegerField(default=1)
    es_superset = models.BooleanField(default=False)
    grupo_superset = models.CharField(max_length=10, blank=True)
    
    # Seguimiento
    completado_veces = models.PositiveIntegerField(default=0)
    mejor_peso = models.CharField(max_length=50, blank=True)
    fecha_mejor_marca = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['orden', 'grupo_superset']
        indexes = [
            models.Index(fields=['rutina', 'orden']),
            models.Index(fields=['tipo']),
        ]

    def __str__(self):
        superset = f" (SS-{self.grupo_superset})" if self.es_superset else ""
        return f"{self.nombre_ejercicio}{superset} - {self.series}x{self.repeticiones}"

class SesionEntrenamiento(models.Model):
    STATUS_CHOICES = [
        ('programada', 'Programada'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, related_name='sesiones')
    alumno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sesiones_entrenamiento')
    fecha_programada = models.DateTimeField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='programada')
    duracion_real = models.PositiveIntegerField(null=True, blank=True)  # minutos
    rating_sesion = models.PositiveIntegerField(null=True, blank=True)  # 1-5
    notas_alumno = models.TextField(blank=True)
    notas_entrenador = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_programada']

    def __str__(self):
        return f"Sesión {self.rutina.nombre} - {self.fecha_programada.date()}"


class ClaseSesion(models.Model):
    """Sesiones públicas creadas por administradores/entrenadores a las que varios alumnos pueden inscribirse."""
    TIPO_CHOICES = [
        ('clase', 'Clase'),
        ('entrenamiento', 'Entrenamiento'),
        ('evento', 'Evento'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='clase')
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    capacidad = models.PositiveIntegerField(null=True, blank=True, help_text='Null = ilimitado')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sesiones_creadas')
    creado_en = models.DateTimeField(auto_now_add=True)
    ubicacion = models.CharField(max_length=200, blank=True)
    publico = models.BooleanField(default=True)
    cancelada = models.BooleanField(default=False)

    class Meta:
        ordering = ['inicio']

    def __str__(self):
        return f"{self.titulo} - {self.inicio.strftime('%d/%m/%Y %H:%M')}"

    @property
    def inscritos_count(self):
        return self.inscripciones.filter(status='inscrito').count()

    @property
    def disponible(self):
        if self.cancelada:
            return False
        if self.capacidad is None:
            return True
        return self.inscritos_count < self.capacidad


class InscripcionSesion(models.Model):
    STATUS_CHOICES = [
        ('inscrito', 'Inscrito'),
        ('rechazado', 'Rechazado')
    ]

    sesion = models.ForeignKey(ClaseSesion, on_delete=models.CASCADE, related_name='inscripciones')
    alumno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscripciones_sesiones')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inscrito')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sesion', 'alumno')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.alumno.username} - {self.sesion.titulo} ({self.status})"

class RegistroEjercicio(models.Model):
    sesion = models.ForeignKey(SesionEntrenamiento, on_delete=models.CASCADE, related_name='registros')
    detalle_ejercicio = models.ForeignKey(DetalleEjercicio, on_delete=models.CASCADE)
    serie_numero = models.PositiveIntegerField()
    repeticiones_realizadas = models.PositiveIntegerField()
    peso_utilizado = models.CharField(max_length=50)
    rpe_percibido = models.PositiveIntegerField(null=True, blank=True)
    completado = models.BooleanField(default=True)
    notas = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['serie_numero']
        unique_together = ['sesion', 'detalle_ejercicio', 'serie_numero']

    def __str__(self):
        return f"S{self.serie_numero}: {self.repeticiones_realizadas}x{self.peso_utilizado}"

class RecomendacionSistema(models.Model):
    TIPO_CHOICES = [
        ('aumento_peso', 'Aumento de Peso'),
        ('aumento_reps', 'Aumento de Repeticiones'),
        ('cambio_ejercicio', 'Cambio de Ejercicio'),
        ('descanso', 'Día de Descanso'),
        ('alerta_estancamiento', 'Alerta de Estancamiento'),
        ('felicitacion', 'Felicitación por Progreso'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    alumno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recomendaciones')
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, related_name='recomendaciones')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    accion_sugerida = models.TextField()
    leida = models.BooleanField(default=False)
    aplicada = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aplicacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion', '-prioridad']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.alumno.get_full_name()}"

# Mantener modelos existentes
class RegistroProgreso(models.Model):
    detalle_ejercicio = models.ForeignKey(DetalleEjercicio, on_delete=models.CASCADE)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    peso_levantado_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    series_realizadas = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Progreso de {escape(self.detalle_ejercicio.nombre_ejercicio)}"

# NUEVO: registro de ejercicios completados por el alumno (logs de entrenamiento)
class EntrenamientoLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entrenamiento_logs')
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, null=True, blank=True, related_name='entrenamiento_logs')
    ejercicio_nombre = models.CharField(max_length=200)
    repeticiones = models.PositiveIntegerField(default=0)
    peso = models.CharField(max_length=50, blank=True)
    notas = models.TextField(blank=True)
    fecha = models.DateField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.ejercicio_nombre} - {self.user.username} - {self.fecha}"

class AsistenciaEntrenador(models.Model):
    entrenador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField(null=True, blank=True)
    notas = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['entrenador', 'fecha']
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Asistencia {escape(self.entrenador.username)} - {self.fecha}"

class ContadorSeries(models.Model):
    alumno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    entrenador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='series_asignadas')
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE)
    fecha_semana = models.DateField()  # Lunes de la semana
    total_series_rutina = models.IntegerField(default=0)
    total_series_semana = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['alumno', 'rutina', 'fecha_semana']
        ordering = ['-fecha_semana']
    
    def __str__(self):
        return f"Series {escape(self.alumno.username)} - Semana {self.fecha_semana}"

class PlantillaExcel(models.Model):
    entrenador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='plantillas_excel/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-fecha_subida']
    
    def __str__(self):
        return f"Plantilla {escape(self.nombre)} - {escape(self.entrenador.username)}"

class EventoCalendario(models.Model):
    TIPO_CHOICES = [
        ('sesion', 'Sesión de Entrenamiento'),
        ('evaluacion', 'Evaluación'),
        ('reunion', 'Reunión'),
        ('descanso', 'Día de Descanso'),
        ('otro', 'Otro'),
    ]
    
    entrenador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sesion')
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    alumno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='eventos_asignados', null=True, blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    completado = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['fecha_inicio']
    
    def __str__(self):
        return f"{escape(self.titulo)} - {self.fecha_inicio.date()}"