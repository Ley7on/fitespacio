# Usa una imagen base de Python
FROM python:3.11-slim

# Instala dependencias del sistema necesarias para la base de datos
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

# Copia todo el código de la aplicación (solo la subcarpeta trainer_app)
COPY . .

# Crea los directorios para archivos estáticos, media y logs
RUN mkdir -p /app/media/qr_codes /app/media/exports /app/logs /app/static

# Recopila archivos estáticos (asegurando que manage.py se ejecute en el contexto correcto)
# Aquí está la clave: Django necesita saber dónde está su settings.
# Asegúrate de que el módulo settings esté configurado correctamente para la app.
# En tu settings.py ya manejamos la variable DJANGO_SETTINGS_MODULE
ENV DJANGO_SETTINGS_MODULE=trainer_app.settings
RUN python manage.py collectstatic --noinput

# Expone el puerto que usará Gunicorn
EXPOSE 8000

# Comando para ejecutar Gunicorn cuando el contenedor se inicie
CMD ["gunicorn", "--bind", ":8000", "trainer_app.wsgi:application"]
