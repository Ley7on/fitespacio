from django.db import models
from django.contrib.auth.models import User
from django.utils.html import escape
from django.utils import timezone
import pyotp
import qrcode
from io import BytesIO
import base64
from django.conf import settings

class InformacionAlumno(models.Model):
    GENERO_CHOICES = [
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('otro', 'Otro'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_completo = models.CharField(max_length=200)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    altura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Altura en cm")
    peso_actual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Peso en kg")
    porcentaje_grasa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Porcentaje de grasa corporal")
    imc = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    informacion_completa = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Calcular IMC automáticamente
        if self.altura and self.peso_actual:
            altura_m = float(self.altura) / 100  # Convertir cm a metros
            self.imc = float(self.peso_actual) / (altura_m ** 2)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.user.username}"
    
    class Meta:
        db_table = 'informacion_alumno'

class PerfilAlumno(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('vip', 'VIP'),
    ]
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='basic')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activo')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    qr_secret = models.CharField(max_length=32, unique=True)
    
    # Campos de perfil
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    descripcion = models.TextField(max_length=500, blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    facebook = models.CharField(max_length=100, blank=True)
    twitter = models.CharField(max_length=100, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.qr_secret:
            self.qr_secret = pyotp.random_base32()
        super().save(*args, **kwargs)
    
    def generar_qr_code(self):
        totp = pyotp.TOTP(self.qr_secret, interval=300)  # 5 minutos
        token = totp.now()
        qr_data = f"{self.user.id}:{token}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def validar_qr(self, token):
        totp = pyotp.TOTP(self.qr_secret, interval=300)
        return totp.verify(token, valid_window=1)
    
    def __str__(self):
        return escape(f"{self.user.get_full_name()} - {self.plan}")

class AccesoGimnasio(models.Model):
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    fecha_acceso = models.DateTimeField(auto_now_add=True)
    tipo_acceso = models.CharField(max_length=20, choices=[
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('denegado', 'Denegado'),
    ])
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_acceso']

class ProgresoFisico(models.Model):
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grasa_corporal = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    masa_muscular = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notas = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha']

class NotificacionMotivacional(models.Model):
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-fecha_envio']

class HabitoBueno(models.Model):
    TIPO_CHOICES = [
        ('agua', 'Tomar Agua'),
        ('sueno', 'Dormir Bien'),
        ('ejercicio', 'Ejercicio Extra'),
        ('meditacion', 'Meditación'),
        ('lectura', 'Lectura'),
        ('otro', 'Otro'),
    ]
    
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    meta_diaria = models.IntegerField(default=1)  # Ej: 8 vasos de agua
    unidad = models.CharField(max_length=20, default='veces')  # vasos, horas, etc.
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.alumno.user.username}"

class RegistroHabitoBueno(models.Model):
    habito = models.ForeignKey(HabitoBueno, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    cantidad = models.IntegerField(default=1)
    notas = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['habito', 'fecha']
        ordering = ['-fecha']

class HabitoMalo(models.Model):
    TIPO_CHOICES = [
        ('alimentacion', 'Mala Alimentación'),
        ('sueno', 'Mal Sueño'),
        ('procrastinacion', 'Procrastinación'),
        ('sedentarismo', 'Sedentarismo'),
        ('estres', 'Manejo del Estrés'),
        ('otro', 'Otro'),
    ]
    
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.alumno.user.username}"

class RegistroHabitoMalo(models.Model):
    INTENSIDAD_CHOICES = [
        (1, 'Leve'),
        (2, 'Moderado'),
        (3, 'Grave'),
    ]
    
    habito = models.ForeignKey(HabitoMalo, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    intensidad = models.IntegerField(choices=INTENSIDAD_CHOICES, default=1)
    descripcion_situacion = models.TextField()
    reflexion = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_registro']

class MensajeMotivacional(models.Model):
    TIPO_CHOICES = [
        ('asistencia', 'Asistencia'),
        ('habitos', 'Hábitos'),
        ('progreso', 'Progreso'),
        ('motivacion', 'Motivación'),
        ('salud_mental', 'Salud Mental'),
    ]
    
    PRIORIDAD_CHOICES = [
        (1, 'Baja'),
        (2, 'Media'),
        (3, 'Alta'),
    ]
    
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=100)
    contenido = models.TextField()
    prioridad = models.IntegerField(choices=PRIORIDAD_CHOICES, default=2)
    leido = models.BooleanField(default=False)
    NIVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Danger'),
    ]
    nivel = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='info')
    origen = models.CharField(max_length=50, blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    accion_sugerida = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['-prioridad', '-fecha_envio']
    
    def __str__(self):
        return f"{self.titulo} - {self.alumno.user.username}"

    @property
    def es_leido(self):
        return self.leido

class Ejercicio(models.Model):
    CATEGORIA_CHOICES = [
        ('empuje', 'Tren Superior - Empuje'),
        ('traccion', 'Tren Superior - Tracción'),
        ('piernas', 'Tren Inferior'),
        ('core', 'Núcleo (Core)'),
    ]
    
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    descripcion = models.TextField()
    maquina_requerida = models.CharField(max_length=100)
    imagen = models.CharField(max_length=50)  # Nombre del archivo de imagen
    musculos_principales = models.CharField(max_length=200)
    
    def __str__(self):
        return self.nombre

class RegistroEjercicio(models.Model):
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    series = models.IntegerField(default=1)
    repeticiones = models.IntegerField(default=1)
    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notas = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"{self.ejercicio.nombre} - {self.alumno.user.username} - {self.fecha}"

class Meta(models.Model):
    CATEGORIA_CHOICES = [
        ('peso', 'Peso Corporal'),
        ('fuerza', 'Fuerza'),
        ('resistencia', 'Resistencia'),
        ('habitos', 'Hábitos'),
        ('general', 'General'),
    ]
    
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('completada', 'Completada'),
        ('pausada', 'Pausada'),
        ('cancelada', 'Cancelada'),
    ]
    
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    fecha_objetivo = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    valor_objetivo = models.CharField(max_length=100, blank=True)  # Ej: "75kg", "100 flexiones"
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.alumno.user.username}"

class AccionMeta(models.Model):
    meta = models.ForeignKey(Meta, on_delete=models.CASCADE, related_name='acciones')
    descripcion = models.CharField(max_length=200)
    completada = models.BooleanField(default=False)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['completada', '-fecha_creacion']
    
    def __str__(self):
        return f"{self.descripcion} - {self.meta.titulo}"

class ProgresoMeta(models.Model):
    meta = models.ForeignKey(Meta, on_delete=models.CASCADE, related_name='progresos')
    fecha = models.DateField(default=timezone.now)
    valor_actual = models.CharField(max_length=100)
    notas = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.meta.titulo} - {self.valor_actual} - {self.fecha}"

# Rutinas del alumno - Sistema nuevo
class RutinaAlumno(models.Model):
    OBJETIVO_CHOICES = [
        ('fuerza', 'Fuerza'),
        ('hipertrofia', 'Ganancia Muscular'),
        ('resistencia', 'Resistencia'),
        ('perdida_grasa', 'Pérdida de Grasa'),
        ('funcional', 'Entrenamiento Funcional'),
    ]
    
    TIPO_CHOICES = [
        ('asignada', 'Asignada por Entrenador'),
        ('personal', 'Rutina Personal'),
    ]
    
    DIAS_CHOICES = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    ]
    
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE, related_name='rutinas')
    nombre = models.CharField(max_length=150)
    objetivo = models.CharField(max_length=20, choices=OBJETIVO_CHOICES)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    dia_asignado = models.CharField(max_length=20, choices=DIAS_CHOICES, null=True, blank=True)
    
    # Para rutinas asignadas por entrenador
    rutina_entrenador = models.ForeignKey('entrenador.Rutina', on_delete=models.CASCADE, null=True, blank=True)
    asignada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    
    # Para rutinas personales
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['dia_asignado', '-fecha_creacion']
    
    def __str__(self):
        tipo_icon = '👨🏫' if self.tipo == 'asignada' else '💪'
        dia = f" - {self.get_dia_asignado_display()}" if self.dia_asignado else ""
        return f"{tipo_icon} {self.nombre}{dia}"

class EjercicioRutinaAlumno(models.Model):
    rutina = models.ForeignKey(RutinaAlumno, on_delete=models.CASCADE, related_name='ejercicios')
    nombre = models.CharField(max_length=150)
    series = models.PositiveIntegerField()
    repeticiones = models.CharField(max_length=30)  # Ej: "10-12" o "15"
    peso = models.CharField(max_length=50, blank=True)  # Ej: "20kg" o "peso corporal"
    descanso = models.CharField(max_length=50, default="60s")
    notas = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=1)
    
    # Referencia al ejercicio original del entrenador para sincronización automática
    ejercicio_entrenador = models.ForeignKey('entrenador.DetalleEjercicio', on_delete=models.SET_NULL, null=True, blank=True, related_name='ejercicios_alumnos')
    
    class Meta:
        ordering = ['orden']
    
    def __str__(self):
        return f"{self.nombre} - {self.series}x{self.repeticiones}"


class SesionEntrenamiento(models.Model):
    """
    Registro de sesiones de entrenamiento completadas por el alumno.
    Permite trackear consistencia y generar estadísticas.
    """
    id = models.AutoField(primary_key=True)  # Usar AutoField para compatibilidad con PerfilAlumno
    alumno = models.ForeignKey(PerfilAlumno, on_delete=models.CASCADE, related_name='sesiones_entrenamiento')
    rutina = models.ForeignKey(RutinaAlumno, on_delete=models.CASCADE, null=True, blank=True, related_name='sesiones_completadas')
    rutina_nombre = models.CharField(max_length=150)  # Guardamos el nombre por si se borra la rutina
    fecha = models.DateField(default=timezone.now)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha', '-fecha_hora']
        # Removido unique_together porque con CASCADE no necesitamos prevenir duplicados de rutinas eliminadas
        verbose_name = 'Sesión de Entrenamiento'
        verbose_name_plural = 'Sesiones de Entrenamiento'
    
    def __str__(self):
        return f"{self.alumno.user.username} - {self.rutina_nombre} - {self.fecha}"