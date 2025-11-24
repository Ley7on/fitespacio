from django.db import models
from django.conf import settings

# Modelos espejo de las tablas del sistema administrador (admin_gym_*)
# No gestionados por Django (managed=False) para no alterar su esquema.

class AdminGymCliente(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    telefono = models.CharField(max_length=20)
    activo = models.BooleanField()
    fecha_registro = models.DateTimeField()
    membresia = models.CharField(max_length=10)
    estado_membresia = models.CharField(max_length=10)
    suspendido = models.BooleanField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    qr_code = models.CharField(max_length=100)
    qr_image = models.CharField(max_length=100)
    profesor_asignado = models.ForeignKey(
        'AdminGymProfesor', models.DO_NOTHING, null=True, blank=True
    )
    rut = models.CharField(max_length=12)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    foto_perfil = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'admin_gym_cliente'
        app_label = 'entrenador_app'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.nombre} ({self.email})"
    
    @property
    def facebook(self):
        return ""
    
    @property
    def instagram(self):
        return ""
    
    @property
    def twitter(self):
        return ""


class AdminGymProfesor(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    telefono = models.CharField(max_length=20)
    especialidad = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, null=True, blank=True)
    rut = models.CharField(max_length=12)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'admin_gym_profesor'
        app_label = 'entrenador_app'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class AdminGymRutina(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    objetivo = models.CharField(max_length=20)
    es_plantilla = models.BooleanField()
    fecha_creacion = models.DateTimeField()
    activa = models.BooleanField()
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'admin_gym_rutina'
        app_label = 'entrenador_app'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.nombre


class AdminGymEjercicio(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20)
    grupo_muscular = models.CharField(max_length=50)
    instrucciones = models.TextField()
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'admin_gym_ejercicio'
        app_label = 'entrenador_app'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class AdminGymEjercicioRutina(models.Model):
    id = models.BigAutoField(primary_key=True)
    series = models.PositiveIntegerField()
    repeticiones = models.PositiveIntegerField(null=True, blank=True)
    peso_sugerido = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tiempo_descanso = models.PositiveIntegerField(null=True, blank=True)
    orden = models.PositiveIntegerField()
    notas = models.TextField()
    ejercicio = models.ForeignKey(AdminGymEjercicio, models.DO_NOTHING)
    rutina = models.ForeignKey(AdminGymRutina, models.DO_NOTHING)
    video_url = models.URLField(blank=True, default='')
    video_duration_s = models.PositiveIntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'admin_gym_ejerciciorutina'
        app_label = 'entrenador_app'
        ordering = ['rutina_id', 'orden']


class AdminGymRutinaCliente(models.Model):
    id = models.BigAutoField(primary_key=True)
    fecha_asignacion = models.DateTimeField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activa = models.BooleanField()
    asignado_por = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING)
    cliente = models.ForeignKey(AdminGymCliente, models.DO_NOTHING)
    rutina = models.ForeignKey(AdminGymRutina, models.DO_NOTHING)
    # notas = models.TextField(blank=True, default='')  # Comentado temporalmente

    class Meta:
        managed = False
        db_table = 'admin_gym_rutinacliente'
        app_label = 'entrenador_app'
        ordering = ['-fecha_asignacion']


class AdminGymRecomendacionSistema(models.Model):
    id = models.BigAutoField(primary_key=True)
    tipo = models.CharField(max_length=20)
    descripcion = models.TextField()
    recomendacion = models.TextField()
    estado = models.CharField(max_length=10)
    fecha_creacion = models.DateTimeField()
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    cliente = models.ForeignKey(AdminGymCliente, models.DO_NOTHING)
    respondido_por = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'admin_gym_recomendacionsistema'
        app_label = 'entrenador_app'
        ordering = ['-fecha_creacion']


class UserAppMapping(models.Model):
    APP_TYPES = (
        ('admin', 'admin'),
        ('entrenador', 'entrenador'),
        ('cliente', 'cliente'),
    )

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)
    app_type = models.CharField(max_length=20, choices=APP_TYPES)
    created_at = models.DateTimeField(auto_now_add=False, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'user_app_mapping'
        app_label = 'entrenador_app'
        unique_together = (('user', 'app_type'),)
        ordering = ['user_id', 'app_type']

    def __str__(self):
        return f"{self.user_id}:{self.app_type}"


class EntrenamientoLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING)
    rutina = models.ForeignKey(AdminGymRutina, models.DO_NOTHING, null=True, blank=True)
    ejercicio_nombre = models.CharField(max_length=200)
    repeticiones = models.PositiveIntegerField(null=True, blank=True)
    fecha = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'entrenamiento_log'
        app_label = 'entrenador_app'
        ordering = ['-fecha']