# FitSpace - Sistema de Gestión de Gimnasio

Sistema completo de gestión de gimnasio con dos aplicaciones Django:
- **admin_gym**: Sistema administrativo del gimnasio
- **trainer_app**: Sistema para entrenadores y alumnos

## 🚀 Despliegue en Google Cloud Run

Este proyecto está configurado para desplegarse automáticamente en Google Cloud Run desde GitHub.

### Prerequisitos

1. Cuenta de Google Cloud con billing activado
2. Repositorio en GitHub
3. Cloud SQL MySQL instance configurada

### Configuración Rápida

1. **Crear secrets en Google Cloud Secret Manager:**

```bash
# Contraseña de la base de datos
echo -n 'TU_PASSWORD_BD' | gcloud secrets create DB_PASSWORD --data-file=-

# Secret Key para admin_gym
echo -n 'TU_SECRET_KEY_ADMIN' | gcloud secrets create DJANGO_SECRET_KEY_ADMIN --data-file=-

# Secret Key para trainer_app
echo -n 'TU_SECRET_KEY_TRAINER' | gcloud secrets create DJANGO_SECRET_KEY_TRAINER --data-file=-
```

2. **Habilitar APIs necesarias:**

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com secretmanager.googleapis.com
```

3. **Conectar GitHub a Cloud Build:**

- Ve a: https://console.cloud.google.com/cloud-build/triggers
- Conecta tu repositorio de GitHub
- Crea un trigger apuntando a `cloudbuild.yaml`

4. **Push a GitHub:**

```bash
git add .
git commit -m "Deploy to Cloud Run"
git push origin main
```

### Arquitectura

```
GitHub Push → Cloud Build → Container Registry → Cloud Run
                                                      ↓
                                              Cloud SQL MySQL
```

### Variables de Entorno en Producción

Cloud Run configura automáticamente:
- `K_SERVICE`: Nombre del servicio
- `PORT`: Puerto (8080)
- `DB_NAME`: fitspace
- `DB_USER`: Usuario de Cloud SQL
- `DB_PASSWORD`: Desde Secret Manager
- `SECRET_KEY`: Desde Secret Manager

### Desarrollo Local

1. **Instalar dependencias:**

```bash
cd admin_gym
pip install -r requirements.txt

cd ../trainer_app
pip install -r requirements.txt
```

2. **Configurar archivo .env:**

```env
DEBUG=True
DB_HOST=34.176.41.244
DB_NAME=fitspace
DB_USER=tu_usuario
DB_PASSWORD=tu_password
```

3. **Ejecutar servidores:**

```bash
# Terminal 1 - Admin
cd admin_gym
python manage.py runserver 8000

# Terminal 2 - Trainer
cd trainer_app
python manage.py runserver 8001
```

### Estructura del Proyecto

```
fitspace/
├── admin_gym/              # Sistema administrativo
│   ├── Dockerfile
│   ├── manage.py
│   ├── requirements.txt
│   └── profit/            # Configuración
├── trainer_app/           # Sistema de entrenadores
│   ├── Dockerfile
│   ├── manage.py
│   ├── requirements.txt
│   └── entrenador_app/   # Configuración
├── cloudbuild.yaml        # CI/CD de Google Cloud
├── .gitignore
└── README.md
```

### Documentación Completa

- [Guía de Despliegue en Cloud Run](CLOUD_RUN_DEPLOYMENT.md)
- [Configuración de Cloud SQL](CLOUD_SQL_SETUP.md)

### URLs de Producción

Después del despliegue:
- Admin: `https://admin-gym-XXXXX-uc.a.run.app`
- Trainer: `https://trainer-app-XXXXX-uc.a.run.app`

### Costos Estimados

Con el tier gratuito de Cloud Run:
- 2M requests/mes GRATIS
- Cloud SQL: f1-micro (tier gratuito disponible)
- **Estimado para beta: $0-5 USD/mes**

### Soporte

Para más información, consulta la documentación en `/docs` o abre un issue.

## 📝 Licencia

Proyecto privado - FitSpace 2025
