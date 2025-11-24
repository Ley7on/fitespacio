from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.html import escape
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
import re
import uuid
import json

class Profesor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    rut = models.CharField(max_length=12, unique=True, help_text="RUT con formato 12345678-9")
    nombre = models.CharField(max_length=100)
    
    def clean(self):
        if self.nombre and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', self.nombre):
            raise ValidationError('El nombre solo puede contener letras y espacios')
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    especialidad = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return escape(self.nombre)
class PerfilUsuario(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('entrenador', 'Entrenador'),
        ('recepcion', 'Recepción'),
        ('cliente', 'Cliente'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    debe_cambiar_password = models.BooleanField(default=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='cliente')
    permisos_especiales = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Perfil de {escape(self.user.username)}"

class Cliente(models.Model):
    TIPOS_MEMBRESIA = [
        ('anual', 'Anual'),
        ('6m', '6 Meses'),
        ('3m', '3 Meses'),
    ]
    ESTADOS_MEMBRESIA = [
        ('activa', 'Activa'),
        ('vencida', 'Vencida'),
        ('morosa', 'Morosa'),
        ('pausada', 'Pausada'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    rut = models.CharField(max_length=12, unique=True, help_text="RUT con formato 12345678-9")
    nombre = models.CharField(max_length=100)
    
    def clean(self):
        if self.nombre and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', self.nombre):
            raise ValidationError('El nombre solo puede contener letras y espacios')
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    membresia = models.CharField(max_length=10, choices=TIPOS_MEMBRESIA, default='anual')
    estado_membresia = models.CharField(max_length=10, choices=ESTADOS_MEMBRESIA, default='activa')
    suspendido = models.BooleanField(default=False)
    qr_code = models.CharField(max_length=100, unique=True, blank=True)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    profesor_asignado = models.ForeignKey(Profesor, on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = str(uuid.uuid4())
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """Generar código QR único para el cliente"""
        import qrcode
        from io import BytesIO
        from django.core.files.base import ContentFile
        
        # Generar nuevo token si no existe
        if not self.qr_code:
            self.qr_code = str(uuid.uuid4())
        
        # Crear QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_code)
        qr.make(fit=True)
        
        # Generar imagen
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Guardar archivo
        filename = f'qr_{self.id}_{uuid.uuid4().hex[:8]}.png'
        self.qr_image.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=False
        )
        
        return self.qr_code
    
    def puede_acceder(self):
        return self.activo and self.estado_membresia == 'activa' and not self.suspendido

    def __str__(self):
        return escape(self.nombre)

class Sesion(models.Model):
    nombre = models.CharField(max_length=100)
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)
    clientes = models.ManyToManyField(Cliente, related_name='sesiones')
    horario = models.DateTimeField()
    cupo = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    descripcion = models.TextField(blank=True)
    personalizada = models.BooleanField(default=False)

    def __str__(self):
        return f"{escape(self.nombre)} ({self.horario})"
    
    class Meta:
        verbose_name = 'Sesión de Entrenamiento'
        verbose_name_plural = 'Sesiones de Entrenamiento'

class Asistencia(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    sesion = models.ForeignKey(Sesion, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{escape(self.cliente.nombre)} - {self.fecha:%Y-%m-%d %H:%M}"

class Pago(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    # Usar CLP (pesos chilenos) — sin decimales. Guardamos como DecimalField con 0 decimales
    # para mantener compatibilidad con formatos monetarios en el código, pero sin
    # permitir centavos.
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    fecha_pago = models.DateTimeField(default=timezone.now)
    plan = models.CharField(max_length=10, choices=Cliente.TIPOS_MEMBRESIA, default='anual')
    vencimiento = models.DateField()
    estado = models.CharField(max_length=10, choices=[
        ('Pagado', 'Pagado'),
        ('Pendiente', 'Pendiente'),
        ('Vencido', 'Vencido'),
    ], default='Pendiente')

    def __str__(self):
        return f"{escape(self.cliente.nombre)} - {self.plan} - {self.estado}"
class CredencialPendiente(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    rut = models.CharField(max_length=20)
    password_temporal = models.CharField(max_length=128)  # Aumentado para hash
    enviado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def set_password_temporal(self, raw_password):
        """Hashear password temporal"""
        self.password_temporal = make_password(raw_password)
    
    def check_password_temporal(self, raw_password):
        """Verificar password temporal"""
        return check_password(raw_password, self.password_temporal)

class Ejercicio(models.Model):
    TIPOS_EJERCICIO = [
        ('fuerza', 'Fuerza'),
        ('resistencia', 'Resistencia'),
        ('flexibilidad', 'Flexibilidad'),
        ('cardio', 'Cardiovascular'),
    ]
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_EJERCICIO)
    grupo_muscular = models.CharField(max_length=50)
    instrucciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return escape(self.nombre)

class Rutina(models.Model):
    OBJETIVOS = [
        ('fuerza', 'Fuerza'),
        ('resistencia', 'Resistencia'),
        ('perdida_peso', 'Pérdida de Peso'),
        ('ganancia_muscular', 'Ganancia Muscular'),
        ('general', 'Acondicionamiento General'),
    ]
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    objetivo = models.CharField(max_length=20, choices=OBJETIVOS)
    es_plantilla = models.BooleanField(default=False)
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return escape(self.nombre)

class EjercicioRutina(models.Model):
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, related_name='ejercicios')
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE)
    series = models.PositiveIntegerField()
    repeticiones = models.PositiveIntegerField(null=True, blank=True)
    peso_sugerido = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tiempo_descanso = models.PositiveIntegerField(help_text="Segundos", null=True, blank=True)
    orden = models.PositiveIntegerField()
    notas = models.TextField(blank=True)
    
    class Meta:
        ordering = ['orden']

class RutinaCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE)
    asignado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    
class RegistroProgreso(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE)
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    series_completadas = models.PositiveIntegerField()
    repeticiones = models.PositiveIntegerField(null=True, blank=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tiempo = models.PositiveIntegerField(null=True, blank=True, help_text="Segundos")
    rpe = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)], null=True, blank=True)
    notas = models.TextField(blank=True)
    enfoque_dia = models.CharField(max_length=100, blank=True, help_text="Ej: Fuerza, Resistencia, etc.")
    estado_animo = models.CharField(max_length=50, blank=True)
    calidad_sueno = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)], null=True, blank=True)
    nivel_energia = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)], null=True, blank=True)
    visto_por_profesor = models.BooleanField(default=False)
    
class AccesoQR(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    qr_code = models.CharField(max_length=100)
    fecha_acceso = models.DateTimeField(auto_now_add=True)
    exitoso = models.BooleanField()
    motivo_fallo = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=50, unique=True)
    valor = models.TextField()
    descripcion = models.CharField(max_length=200)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
class NotificacionTemplate(models.Model):
    TIPOS = [
        ('racha', 'Racha de Asistencia'),
        ('felicitacion', 'Felicitación'),
        ('motivacional', 'Motivacional'),
        ('recordatorio', 'Recordatorio'),
    ]
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    activo = models.BooleanField(default=True)
    
class NotificacionEnviada(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    template = models.ForeignKey(NotificacionTemplate, on_delete=models.CASCADE)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    exitoso = models.BooleanField()
    
class AuditoriaEvento(models.Model):
    TIPOS_EVENTO = [
        ('alta_usuario', 'Alta de Usuario'),
        ('baja_usuario', 'Baja de Usuario'),
        ('cambio_estado', 'Cambio de Estado'),
        ('acceso_denegado', 'Acceso Denegado'),
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tipo_evento = models.CharField(max_length=20, choices=TIPOS_EVENTO)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    datos_adicionales = models.JSONField(default=dict, blank=True)
    
class RecomendacionSistema(models.Model):
    TIPOS_RECOMENDACION = [
        ('estancamiento', 'Estancamiento Detectado'),
        ('progresion_excesiva', 'Progresión Excesiva'),
        ('sobrecarga', 'Sobrecarga/Fatiga'),
        ('cambio_rutina', 'Cambio de Rutina Sugerido'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS_RECOMENDACION)
    descripcion = models.TextField()
    recomendacion = models.TextField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    respondido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

class ComentarioProgreso(models.Model):
    registro_progreso = models.ForeignKey(RegistroProgreso, on_delete=models.CASCADE, related_name='comentarios')
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']

