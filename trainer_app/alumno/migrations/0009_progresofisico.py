# Generated manually to fix missing ProgresoFisico table

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('alumno', '0008_rutina_ejerciciorutina'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgresoFisico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('peso', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('grasa_corporal', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ('masa_muscular', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ('notas', models.TextField(blank=True)),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='alumno.perfilalumno')),
            ],
            options={
                'ordering': ['-fecha'],
            },
        ),
    ]