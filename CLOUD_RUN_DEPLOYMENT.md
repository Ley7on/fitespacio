# Guía de Despliegue en Google Cloud Run desde GitHub

## 1. Prerequisitos

### Crear Secrets en Google Cloud
Las contraseñas sensibles deben estar en Secret Manager:

```bash
# Crear secret para la contraseña de la base de datos
echo -n 'Hyf(/k"8TB[{89FJ' | gcloud secrets create DB_PASSWORD --data-file=-

# Crear secret para SECRET_KEY de admin_gym
echo -n 'pqtm2@mt5oye5oiq6)0i8bmquk@g94nyku$)^$rgu^n+99j=@2' | gcloud secrets create DJANGO_SECRET_KEY_ADMIN --data-file=-

# Crear secret para SECRET_KEY de trainer_app
echo -n '_x*)&evtnp8fb=f18#unq#i*2bc3jqs(%+(-)stl0@hopms&*6' | gcloud secrets create DJANGO_SECRET_KEY_TRAINER --data-file=-
```

### Habilitar APIs necesarias

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### Dar permisos a Cloud Build

```bash
# Obtener el número del proyecto
PROJECT_NUMBER=$(gcloud projects describe fitspace-478618 --format="value(projectNumber)")

# Dar permisos de Cloud Run Admin
gcloud projects add-iam-policy-binding fitspace-478618 \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin"

# Dar permisos de Service Account User
gcloud projects add-iam-policy-binding fitspace-478618 \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# Dar permisos para acceder a secrets
gcloud projects add-iam-policy-binding fitspace-478618 \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## 2. Configurar GitHub Repository

### Conectar repositorio a Cloud Build

1. Ve a: https://console.cloud.google.com/cloud-build/triggers
2. Clic en **"Conectar repositorio"**
3. Selecciona **GitHub**
4. Autoriza Google Cloud Build
5. Selecciona tu repositorio de FitSpace
6. Clic en **"Conectar"**

### Crear Trigger de Cloud Build

1. En la misma página, clic en **"Crear activador"**
2. Configura:
   - **Nombre:** `deploy-fitspace`
   - **Evento:** Push a una rama
   - **Rama:** `^main$` (o `^master$`)
   - **Tipo de configuración:** Cloud Build configuration file (yaml or json)
   - **Ubicación:** `/cloudbuild.yaml`
3. Clic en **"Crear"**

## 3. Actualizar settings.py para Cloud Run

Los archivos ya están configurados para detectar Cloud Run automáticamente.
Cloud Run usa variables de entorno:
- `PORT` - Puerto donde escucha (8080)
- `K_SERVICE` - Nombre del servicio (indica que está en Cloud Run)

## 4. Archivos necesarios en el repositorio

Asegúrate de que tu repositorio GitHub tenga:

```
fitspace/
├── cloudbuild.yaml              ← Configuración de CI/CD
├── admin_gym/
│   ├── Dockerfile              ← Imagen Docker para admin_gym
│   ├── requirements.txt
│   ├── manage.py
│   └── profit/
│       └── settings.py         ← Ya configurado para Cloud Run
└── trainer_app/
    ├── Dockerfile              ← Imagen Docker para trainer_app
    ├── requirements.txt
    ├── manage.py
    └── entrenador_app/
        └── settings.py         ← Ya configurado para Cloud Run
```

## 5. Variables que NO deben estar en el repositorio

**NUNCA subas a GitHub:**
- `.env` files
- Contraseñas en texto plano
- SECRET_KEYs
- Credenciales de base de datos

Todo esto se maneja con **Secret Manager** y variables de entorno en Cloud Run.

## 6. Actualizar ALLOWED_HOSTS

Después del primer despliegue, obtén las URLs:

```bash
# Ver URL de admin_gym
gcloud run services describe admin-gym --region=southamerica-west1 --format="value(status.url)"

# Ver URL de trainer_app
gcloud run services describe trainer-app --region=southamerica-west1 --format="value(status.url)"
```

Luego actualiza `ALLOWED_HOSTS` en ambos settings.py con esas URLs.

## 7. Desplegar

### Opción A: Desde GitHub (Automático)

1. Haz commit de todos los cambios
2. Push a la rama `main`:
   ```bash
   git add .
   git commit -m "Configurar Cloud Run deployment"
   git push origin main
   ```
3. Cloud Build se ejecutará automáticamente
4. Monitorea en: https://console.cloud.google.com/cloud-build/builds

### Opción B: Manual desde Cloud Shell

```bash
# Clonar repositorio
git clone https://github.com/TU_USUARIO/fitspace.git
cd fitspace

# Ejecutar build
gcloud builds submit --config=cloudbuild.yaml
```

## 8. Verificar el despliegue

```bash
# Estado de admin_gym
gcloud run services describe admin-gym --region=southamerica-west1

# Estado de trainer_app
gcloud run services describe trainer-app --region=southamerica-west1

# Ver logs de admin_gym
gcloud run services logs read admin-gym --region=southamerica-west1

# Ver logs de trainer_app
gcloud run services logs read trainer-app --region=southamerica-west1
```

## 9. Ejecutar migraciones

```bash
# Conectar a Cloud SQL y ejecutar migraciones
gcloud run jobs create admin-gym-migrate \
    --image=gcr.io/fitspace-478618/admin-gym:latest \
    --set-cloudsql-instances=fitspace-478618:southamerica-west1:free-trial-first-project \
    --set-env-vars=ENVIRONMENT=production,DB_NAME=fitspace,DB_USER=free-trial-first-project \
    --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,SECRET_KEY=DJANGO_SECRET_KEY_ADMIN:latest \
    --command="python" \
    --args="manage.py,migrate" \
    --region=southamerica-west1

gcloud run jobs execute admin-gym-migrate --region=southamerica-west1
```

## 10. Costos estimados

**Cloud Run (tier gratuito):**
- 2 millones de solicitudes/mes GRATIS
- 360,000 GB-segundos/mes GRATIS
- 180,000 vCPU-segundos/mes GRATIS

**Cloud SQL (tu instancia):**
- Free tier: MySQL db-f1-micro en Oregón

**Estimación para beta:**
- Con tráfico bajo: ~$0-5 USD/mes
- Cloud SQL ya lo tienes configurado (free tier)

## 11. Troubleshooting

### Error de conexión a base de datos
```bash
# Verificar que Cloud SQL permite conexiones desde Cloud Run
gcloud sql instances describe free-trial-first-project --format="value(settings.ipConfiguration)"
```

### Error de permisos
```bash
# Verificar service account de Cloud Run
gcloud run services describe admin-gym --region=southamerica-west1 --format="value(spec.template.spec.serviceAccountName)"
```

### Ver logs en tiempo real
```bash
gcloud run services logs tail admin-gym --region=southamerica-west1
gcloud run services logs tail trainer-app --region=southamerica-west1
```

## 12. Siguiente paso después del despliegue

1. Obtener las URLs públicas
2. Actualizar `ALLOWED_HOSTS` en settings.py
3. Push nuevamente para actualizar
4. Configurar dominio personalizado (opcional)
