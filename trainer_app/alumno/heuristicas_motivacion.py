from django.utils import timezone
from datetime import timedelta

from .models import PerfilAlumno, MensajeMotivacional, HabitoBueno, RegistroHabitoBueno, RegistroHabitoMalo, AccesoGimnasio, ProgresoFisico, RegistroEjercicio, Meta


def _mensaje_existente_hoy(alumno, tipo):
    hoy = timezone.now().date()
    return MensajeMotivacional.objects.filter(alumno=alumno, tipo=tipo, fecha_envio__date=hoy).exists()


def crear_mensaje(alumno, tipo, titulo, contenido, nivel='info', origen='', prioridad=2, accion_sugerida=''):
    # Evitar duplicados por tipo en el mismo día
    try:
        # Sólo evitar duplicados si ya existe un mensaje con el mismo título hoy
        hoy = timezone.now().date()
        existe = MensajeMotivacional.objects.filter(alumno=alumno, titulo=titulo, fecha_envio__date=hoy).exists()
        if existe:
            return None
        # Normalizar tipos para coincidir con las opciones del modelo y UI
        tipo_map = {
            'hidratacion': 'habitos',
            'sueno': 'habitos',
            'entrenamiento': 'asistencia',
            'habito': 'habitos',
            'meta': 'progreso'
        }
        tipo_para_guardar = tipo_map.get(tipo, tipo)

        return MensajeMotivacional.objects.create(
            alumno=alumno,
            tipo=tipo_para_guardar,
            titulo=titulo,
            contenido=contenido,
            prioridad=prioridad,
            nivel=nivel,
            origen=origen,
            accion_sugerida=accion_sugerida
        )
    except Exception:
        return None


def generar_mensajes_motivacionales(perfil):
    """
    Analiza registros recientes (últimos 7 días) y genera mensajes motivacionales.
    Se espera recibir un objeto `PerfilAlumno`.
    """
    try:
        hoy = timezone.now().date()
        inicio = hoy - timedelta(days=7)

        # 1) Hidratación (habitos tipo 'agua')
        try:
            habitos_agua = HabitoBueno.objects.filter(alumno=perfil, tipo='agua', activo=True)
            for hab in habitos_agua:
                # sumar cantidad hoy
                registro_hoy = RegistroHabitoBueno.objects.filter(habito=hab, fecha=hoy).first()
                cantidad = registro_hoy.cantidad if registro_hoy else 0
                meta = hab.meta_diaria or 1
                porcentaje = int((cantidad / meta) * 100) if meta else 0

                if porcentaje >= 100:
                    crear_mensaje(perfil, 'hidratacion', 'Hidratación completada 👏', f'¡Genial! Cumpliste tu meta de {meta} {hab.unidad} de agua hoy.', nivel='success', origen='accion_agua', prioridad=1)
                elif 50 <= porcentaje < 100:
                    crear_mensaje(perfil, 'hidratacion', 'Casi llegas a tu meta 💧', f'Llevas {cantidad}/{meta} {hab.unidad}. Termina el día con un último empujón.', nivel='warning', origen='accion_agua')
                else:
                    # después de las 18:00 advertencia
                    ahora = timezone.now()
                    if ahora.hour >= 18 and porcentaje < 50:
                        crear_mensaje(perfil, 'hidratacion', 'Recuerda hidratarte 💦', f'Llevas {cantidad}/{meta} {hab.unidad} hoy. Intenta beber más antes del final del día.', nivel='danger', origen='accion_agua')
        except Exception:
            pass

        # 2) Sueño (habitos tipo 'sueno')
        try:
            habitos_sueno = HabitoBueno.objects.filter(alumno=perfil, tipo='sueno', activo=True)
            for hab in habitos_sueno:
                registro = RegistroHabitoBueno.objects.filter(habito=hab).order_by('-fecha').first()
                if registro:
                    horas = registro.cantidad
                    if 7 <= horas <= 9:
                        titulo = f'Buen descanso 😴 - {horas}h'
                        contenido = f'Dormiste {horas} horas la última noche. Excelente para tu recuperación.'
                        crear_mensaje(perfil, 'sueno', titulo, contenido, nivel='success', origen='accion_sueno')
                    elif horas < 6 or horas > 10:
                        titulo = f'Revisa tu descanso - {horas}h'
                        contenido = f'Dormiste {horas} horas. Ajustar tu sueño puede mejorar tu rendimiento y ánimo.'
                        crear_mensaje(perfil, 'sueno', titulo, contenido, nivel='warning', origen='accion_sueno')
        except Exception:
            pass

        # 3) Entrenamientos
        try:
            # contar días con acceso/registro de ejercicio en últimos 7 días
            dias_entrenados = set()
            accesos = AccesoGimnasio.objects.filter(alumno=perfil, fecha_acceso__date__gte=inicio).dates('fecha_acceso', 'day')
            for d in accesos:
                dias_entrenados.add(d)
            ejercicios = RegistroEjercicio.objects.filter(alumno=perfil, fecha_registro__date__gte=inicio).dates('fecha_registro', 'day')
            for d in ejercicios:
                dias_entrenados.add(d)

            # racha: días consecutivos hasta hoy
            racha = 0
            fecha_esperada = hoy
            fechas_ordenadas = sorted(list(dias_entrenados), reverse=True)
            for f in fechas_ordenadas:
                if f == fecha_esperada:
                    racha += 1
                    fecha_esperada -= timedelta(days=1)
                else:
                    break

            if racha >= 1:
                crear_mensaje(perfil, 'entrenamiento', f'¡Racha de {racha} días! 🔥', f'Has entrenado {racha} días seguidos. Mantén el ritmo.', nivel='success', origen='accion_entrenamiento')

            # si no entrenó en N días
            ultimo = None
            if dias_entrenados:
                ultimo = max(dias_entrenados)
            if not ultimo:
                crear_mensaje(perfil, 'entrenamiento', 'Te hace falta entrenar', 'No hemos registrado entrenamientos recientemente. ¡Anímate a volver a la actividad!', nivel='warning', origen='inactividad')
            else:
                dias_sin = (hoy - ultimo).days
                if dias_sin >= 3:
                    crear_mensaje(perfil, 'entrenamiento', 'Retoma el entrenamiento', f'Hace {dias_sin} días desde tu último entrenamiento. Un pequeño plan puede ayudarte a retomar.', nivel='warning', origen='inactividad')
        except Exception:
            pass

        # 4) Habitos (rachas)
        try:
            # ejemplo: racha agua o sueño
            habitos = HabitoBueno.objects.filter(alumno=perfil, activo=True)
            for hab in habitos:
                registros = RegistroHabitoBueno.objects.filter(habito=hab, fecha__gte=inicio).dates('fecha', 'day')
                # contar racha simple
                racha_h = 0
                fecha_esperada = hoy
                for f in registros.order_by('-fecha'):
                    if f == fecha_esperada:
                        racha_h += 1
                        fecha_esperada -= timedelta(days=1)
                    else:
                        break
                if racha_h >= 5:
                    crear_mensaje(perfil, 'habito', f'¡Buena racha en {hab.nombre}! 🎉', f'Llevas {racha_h} días cumpliendo {hab.nombre}. ¡Excelente constancia!', nivel='success', origen='habito')
        except Exception:
            pass

        # 5) Metas
        try:
            metas = Meta.objects.filter(alumno=perfil, estado='activa')
            for m in metas:
                # si valor objetivo y hay progreso, evaluar porcentaje
                # aquí asumimos que Meta.valor_objetivo puede ser numérico en algunos casos (fallback simple)
                # Mejor sería usar ProgresoMeta si existe; usar ProgresoFisico como heurístico para peso
                if m.categoria == 'peso' and m.valor_objetivo:
                    try:
                        objetivo = float(str(m.valor_objetivo).replace('kg', '').strip())
                        ultimo_progreso = ProgresoFisico.objects.filter(alumno=perfil).order_by('-fecha').first()
                        if ultimo_progreso and ultimo_progreso.peso:
                            inicio_peso = None
                            # No tenemos peso inicial formal; saltar cálculo fino y solo avisar si cerca
                            if abs(ultimo_progreso.peso - objetivo) / max(objetivo,1) <= 0.2:
                                crear_mensaje(perfil, 'meta', 'Estás cerca de tu meta 🏁', f'Estás a menos del 20% de tu objetivo {m.titulo}. Sigue así.', nivel='success', origen='meta')
                    except Exception:
                        pass
        except Exception:
            pass

    except Exception:
        pass

    return True
