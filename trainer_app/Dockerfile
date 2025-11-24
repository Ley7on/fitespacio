# Usa una imagen base de Python ligera
FROM python:3.11-slim

# Instala dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de requerimientos e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copia todo el código de la aplicación (solo la subcarpeta trainer_app que se está construyendo)
COPY . .

# Crea los directorios para archivos estáticos, media y logs
RUN mkdir -p /app/media/qr_codes /app/media/exports /app/logs /app/static

# Configura la variable de entorno para que Django sepa dónde están los settings.
# Esto es CRÍTICO para collectstatic y el servidor web.
ENV DJANGO_SETTINGS_MODULE=trainer_app.settings

# Recopila archivos estáticos
RUN python manage.py collectstatic --noinput

# Expone el puerto que usará Gunicorn
EXPOSE 8000

# Comando para ejecutar Gunicorn cuando el contenedor se inicie
CMD ["gunicorn", "--bind", ":8000", "trainer_app.wsgi:application"]
