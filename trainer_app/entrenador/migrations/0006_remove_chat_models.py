from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('entrenador', '0005_fix_chat_foreign_keys'),
    ]

    operations = [
        migrations.RunSQL(
            "DROP TABLE IF EXISTS entrenador_chatmensaje;",
            reverse_sql="-- No reverse"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS entrenador_chatconversacion;",
            reverse_sql="-- No reverse"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS entrenador_alertaayuda;",
            reverse_sql="-- No reverse"
        ),
    ]