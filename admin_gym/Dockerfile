# Dockerfile para admin_gym en Cloud Run
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/media/qr_codes /app/media/exports /app/logs /app/static

# Colectar archivos estáticos
RUN python manage.py collectstatic --noinput

# Exponer puerto
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 profit.wsgi:application
