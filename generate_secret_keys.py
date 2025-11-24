# Script de Generación de SECRET_KEY para Google Cloud
# Ejecuta este script para generar SECRET_KEYs únicos

from django.core.management.utils import get_random_secret_key

print("=" * 70)
print("GENERADOR DE SECRET_KEYS PARA GOOGLE CLOUD")
print("=" * 70)
print()

print("📝 Copia estas SECRET_KEYs en tus archivos app.yaml:")
print()

print("1️⃣  ADMIN_GYM (admin_gym/app.yaml):")
print("-" * 70)
admin_key = get_random_secret_key()
print(f"DJANGO_SECRET_KEY: \"{admin_key}\"")
print()

print("2️⃣  TRAINER_APP (trainer_app/app.yaml):")
print("-" * 70)
trainer_key = get_random_secret_key()
print(f"SECRET_KEY: \"{trainer_key}\"")
print()

print("=" * 70)
print("⚠️  IMPORTANTE:")
print("   - NO compartas estas claves públicamente")
print("   - NO las subas a Git")
print("   - Úsalas SOLO en app.yaml")
print("   - Genera nuevas claves para producción real")
print("=" * 70)
