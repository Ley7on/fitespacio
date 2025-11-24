# Generated manual migration to add nivel and origen to MensajeMotivacional
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('alumno', '0003_mensajemotivacional'),
    ]

    operations = [
        migrations.AddField(
            model_name='mensajemotivacional',
            name='nivel',
            field=models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('success', 'Success'), ('danger', 'Danger')], default='info', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mensajemotivacional',
            name='origen',
            field=models.CharField(blank=True, max_length=50, default=''),
            preserve_default=False,
        ),
    ]
