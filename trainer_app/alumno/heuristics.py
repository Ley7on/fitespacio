from django.utils import timezone
from datetime import timedelta
from .models import PerfilAlumno, AccesoGimnasio, MensajeMotivacional, RegistroHabitoBueno, RegistroHabitoMalo

class MotorRecomendaciones:
    
    @staticmethod
    def analizar_alumno(alumno):
        """Analiza patrones del alumno y genera mensajes motivacionales"""
        mensajes = []
        
        # Análisis de asistencia
        mensajes.extend(MotorRecomendaciones._analizar_asistencia(alumno))
        
        # Análisis de hábitos
        mensajes.extend(MotorRecomendaciones._analizar_habitos(alumno))
        
        # Análisis de progreso
        mensajes.extend(MotorRecomendaciones._analizar_progreso(alumno))
        
        # Mensajes motivacionales
        mensajes.extend(MotorRecomendaciones._generar_motivacion(alumno))
        
        return mensajes
    
    @staticmethod
    def _analizar_asistencia(alumno):
        """Analiza patrones reales de asistencia al gimnasio"""
        mensajes = []
        hoy = timezone.now().date()
        
        try:
            from django.db import connection
            
            # Obtener datos de asistencia desde la tabla del admin
            dias_sin_entrenar = 30
            visitas_mes = 0
            
            try:
                with connection.cursor() as cursor:
                    # Último acceso
                    cursor.execute("""
                        SELECT fecha_hora FROM admin_gym_asistencia 
                        WHERE cliente_id = (SELECT id FROM admin_gym_cliente WHERE user_id = %s)
                        ORDER BY fecha_hora DESC LIMIT 1
                    """, [alumno.user.id])
                    
                    result = cursor.fetchone()
                    if result:
                        ultimo_acceso_fecha = result[0].date() if hasattr(result[0], 'date') else result[0]
                        dias_sin_entrenar = (hoy - ultimo_acceso_fecha).days
                    
                    # Visitas del mes
                    hace_30_dias = hoy - timedelta(days=30)
                    cursor.execute("""
                        SELECT COUNT(*) FROM admin_gym_asistencia 
                        WHERE cliente_id = (SELECT id FROM admin_gym_cliente WHERE user_id = %s)
                        AND fecha_hora >= %s
                    """, [alumno.user.id, hace_30_dias])
                    
                    result = cursor.fetchone()
                    visitas_mes = result[0] if result else 0
                    
            except Exception as e:
                # Fallback a tabla local
                ultimo_acceso = AccesoGimnasio.objects.filter(
                    alumno=alumno,
                    tipo_acceso='entrada'
                ).order_by('-fecha_acceso').first()
                
                if ultimo_acceso:
                    dias_sin_entrenar = (hoy - ultimo_acceso.fecha_acceso.date()).days
                
                hace_30_dias = hoy - timedelta(days=30)
                visitas_mes = AccesoGimnasio.objects.filter(
                    alumno=alumno,
                    tipo_acceso='entrada',
                    fecha_acceso__date__gte=hace_30_dias
                ).count()
            
            frecuencia_semanal = (visitas_mes * 7) / 30 if visitas_mes > 0 else 0

            # Mensaje positivo si el último acceso fue hoy (felicitar y mostrar racha)
            try:
                # Si obtuvimos una fecha del cursor, usamos esa como último acceso
                if 'ultimo_acceso_fecha' in locals() and ultimo_acceso_fecha == hoy:
                    # calcular racha usando tabla local como fallback
                    fechas = AccesoGimnasio.objects.filter(
                        alumno=alumno,
                        tipo_acceso='entrada'
                    ).dates('fecha_acceso', 'day').order_by('-fecha_acceso')

                    racha = 0
                    fecha_esperada = hoy
                    for f in fechas:
                        if f == fecha_esperada:
                            racha += 1
                            fecha_esperada -= timedelta(days=1)
                        else:
                            break

                    if racha > 0:
                        mensajes.append({
                            'tipo': 'asistencia',
                            'titulo': f'¡Racha de {racha} días! 🔥',
                            'contenido': f'¡Increíble! Has mantenido una racha de {racha} días consecutivos entrenando. ¡Sigue así!',
                            'prioridad': 1,
                            'accion_sugerida': ''
                        })
            except Exception:
                pass

            # Generar mensajes según patrones reales
            if dias_sin_entrenar >= 2 and dias_sin_entrenar < 5:
                mensajes.append({
                    'tipo': 'asistencia',
                    'titulo': '¿Todo bien?',
                    'contenido': f'Hace {dias_sin_entrenar} días que no te vemos por el gym. ¿Necesitas ajustar tu rutina o hay algo en lo que podamos ayudarte?',
                    'prioridad': 2,
                    'accion_sugerida': 'chat_entrenador'
                })
            elif dias_sin_entrenar >= 5 and dias_sin_entrenar < 7:
                mensajes.append({
                    'tipo': 'asistencia',
                    'titulo': '¿Necesitas ayuda?',
                    'contenido': 'Una semana sin entrenar puede hacer que pierdas el ritmo. ¿Hablamos sobre cómo retomar tu rutina de forma gradual?',
                    'prioridad': 3,
                    'accion_sugerida': 'chat_entrenador'
                })
            elif dias_sin_entrenar >= 7:
                mensajes.append({
                    'tipo': 'salud_mental',
                    'titulo': 'Te extrañamos',
                    'contenido': 'Sabemos que a veces la vida se complica. Tu entrenador está aquí para apoyarte. No dudes en contactarlo cuando estés listo.',
                    'prioridad': 3,
                    'accion_sugerida': 'chat_entrenador'
                })
            
            # Mensaje por baja frecuencia
            if frecuencia_semanal < 2 and visitas_mes > 0:
                mensajes.append({
                    'tipo': 'motivacion',
                    'titulo': '💪 Aumentemos la frecuencia',
                    'contenido': f'Has venido {visitas_mes} veces este mes. ¿Te parece si planificamos una rutina más constante para mejores resultados?',
                    'prioridad': 2,
                    'accion_sugerida': 'chat_entrenador'
                })
            
        except Exception as e:
            # Fallback en caso de error
            pass
        
        return mensajes
    
    @staticmethod
    def _analizar_habitos(alumno):
        """Analiza hábitos reales del alumno"""
        mensajes = []
        hoy = timezone.now().date()
        
        try:
            from .models import HabitoBueno, HabitoMalo, RegistroHabitoBueno, RegistroHabitoMalo
            
            # Analizar hábitos buenos no completados
            habitos_agua = HabitoBueno.objects.filter(
                alumno=alumno,
                tipo='agua',
                activo=True
            )
            
            for habito in habitos_agua:
                # Verificar últimos 3 días
                dias_sin_completar = 0
                for i in range(3):
                    fecha_check = hoy - timedelta(days=i)
                    registro = RegistroHabitoBueno.objects.filter(
                        habito=habito,
                        fecha=fecha_check
                    ).first()
                    
                    if not registro or registro.cantidad < habito.meta_diaria:
                        dias_sin_completar += 1
                
                if dias_sin_completar >= 2:
                    mensajes.append({
                        'tipo': 'habitos',
                        'titulo': '💧 Hidratación importante',
                        'contenido': f'No has completado tu meta de {habito.meta_diaria} {habito.unidad} de agua en los últimos días. ¡Tu cuerpo lo necesita!',
                        'prioridad': 2,
                        'accion_sugerida': 'registrar_habito'
                    })
            
            # Analizar hábitos de sueño
            habitos_sueno = HabitoBueno.objects.filter(
                alumno=alumno,
                tipo='sueno',
                activo=True
            )
            
            for habito in habitos_sueno:
                registros_recientes = RegistroHabitoBueno.objects.filter(
                    habito=habito,
                    fecha__gte=hoy - timedelta(days=3)
                ).count()
                
                if registros_recientes == 0:
                    mensajes.append({
                        'tipo': 'salud_mental',
                        'titulo': '😴 El descanso es clave',
                        'contenido': 'Un buen descanso es fundamental para tu recuperación y rendimiento. ¿Cómo has estado durmiendo?',
                        'prioridad': 2,
                        'accion_sugerida': 'registrar_habito'
                    })
            
            # Analizar hábitos malos frecuentes
            registros_malos_recientes = RegistroHabitoMalo.objects.filter(
                habito__alumno=alumno,
                fecha__gte=hoy - timedelta(days=7)
            ).count()
            
            if registros_malos_recientes >= 3:
                mensajes.append({
                    'tipo': 'salud_mental',
                    'titulo': '🎯 Enfoquemos en lo positivo',
                    'contenido': 'Has registrado varios hábitos que quieres cambiar. ¿Hablamos sobre estrategias para reemplazarlos con hábitos positivos?',
                    'prioridad': 2,
                    'accion_sugerida': 'chat_entrenador'
                })
            
        except Exception as e:
            # Fallback en caso de error
            pass
        
        return mensajes
    
    @staticmethod
    def _analizar_progreso(alumno):
        """Analiza progreso físico real del alumno"""
        mensajes = []
        hoy = timezone.now().date()
        
        try:
            from .models import ProgresoFisico, RegistroEjercicio
            
            # Verificar si ha registrado progreso físico recientemente
            ultimo_progreso = ProgresoFisico.objects.filter(
                alumno=alumno
            ).order_by('-fecha').first()
            
            if ultimo_progreso:
                dias_sin_progreso = (hoy - ultimo_progreso.fecha.date()).days
                
                if dias_sin_progreso >= 14:  # 2 semanas
                    mensajes.append({
                        'tipo': 'progreso',
                        'titulo': '📈 ¿Cómo vas?',
                        'contenido': 'Hace tiempo que no registras tu progreso físico. ¿Te parece si hacemos una evaluación para ver cómo vas?',
                        'prioridad': 2,
                        'accion_sugerida': 'registrar_progreso'
                    })
            
            # Analizar ejercicios - verificar si hay estancamiento
            ejercicios_recientes = RegistroEjercicio.objects.filter(
                alumno=alumno,
                fecha__gte=hoy - timedelta(days=21)  # 3 semanas
            ).values('ejercicio__nombre').distinct().count()
            
            if ejercicios_recientes == 0:
                mensajes.append({
                    'tipo': 'progreso',
                    'titulo': '🏋️‍♂️ ¡Vamos a entrenar!',
                    'contenido': 'No has registrado ejercicios recientemente. ¿Necesitas una rutina nueva o ayuda con la actual?',
                    'prioridad': 2,
                    'accion_sugerida': 'chat_entrenador'
                })
            
        except Exception as e:
            # Fallback en caso de error
            pass
        
        return mensajes
    
    @staticmethod
    def _generar_motivacion(alumno):
        """Genera mensajes motivacionales basados en datos reales"""
        mensajes = []
        hoy = timezone.now().date()
        
        try:
            # Calcular racha real de asistencia
            racha_actual = MotorRecomendaciones._calcular_racha_asistencia(alumno)
            
            if racha_actual >= 7:
                mensajes.append({
                    'tipo': 'motivacion',
                    'titulo': '🔥 ¡Increíble racha!',
                    'contenido': f'¡{racha_actual} días consecutivos viniendo al gym! Tu constancia es inspiradora. Sigue así, cada día te acercas más a tus objetivos.',
                    'prioridad': 1,
                    'accion_sugerida': ''
                })
            elif racha_actual >= 3:
                mensajes.append({
                    'tipo': 'motivacion',
                    'titulo': '💪 ¡Buen ritmo!',
                    'contenido': f'{racha_actual} días consecutivos. ¡Excelente! La constancia es la clave del éxito.',
                    'prioridad': 1,
                    'accion_sugerida': ''
                })
            
            # Verificar metas completadas recientemente
            from .models import Meta as MetaAlumno
            metas_completadas_recientes = MetaAlumno.objects.filter(
                alumno=alumno,
                estado='completada',
                fecha_completada__gte=hoy - timedelta(days=7)
            ).count()
            
            if metas_completadas_recientes > 0:
                mensajes.append({
                    'tipo': 'motivacion',
                    'titulo': '🏆 ¡Meta alcanzada!',
                    'contenido': '¡Felicidades por completar tu meta! Tu esfuerzo y dedicación están dando frutos. ¿Listo para el siguiente desafío?',
                    'prioridad': 1,
                    'accion_sugerida': 'crear_meta'
                })
            
        except Exception as e:
            # Fallback en caso de error
            pass
        
        return mensajes
    
    @staticmethod
    def _calcular_racha_asistencia(alumno):
        """Calcula la racha actual de asistencia desde tabla del admin"""
        try:
            from django.db import connection
            hoy = timezone.now().date()
            
            # Intentar desde tabla del admin primero
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT DISTINCT DATE(fecha_hora) as fecha
                        FROM admin_gym_asistencia 
                        WHERE cliente_id = (SELECT id FROM admin_gym_cliente WHERE user_id = %s)
                        ORDER BY fecha DESC
                    """, [alumno.user.id])
                    
                    fechas_data = cursor.fetchall()
                    if not fechas_data:
                        return 0
                    
                    fechas_acceso = [row[0] for row in fechas_data]
                    
            except Exception:
                # Fallback a tabla local
                fechas_acceso = AccesoGimnasio.objects.filter(
                    alumno=alumno,
                    tipo_acceso='entrada'
                ).dates('fecha_acceso', 'day').order_by('-fecha_acceso')
                
                if not fechas_acceso:
                    return 0
                
                fechas_acceso = list(fechas_acceso)
            
            racha = 0
            fecha_esperada = hoy
            
            # Verificar si hay actividad hoy o ayer
            if fechas_acceso[0] == hoy:
                racha = 1
                fecha_esperada = hoy - timedelta(days=1)
            elif fechas_acceso[0] == hoy - timedelta(days=1):
                racha = 1
                fecha_esperada = fechas_acceso[0] - timedelta(days=1)
            else:
                return 0
            
            # Contar días consecutivos hacia atrás
            for fecha in fechas_acceso[1:]:
                if fecha == fecha_esperada:
                    racha += 1
                    fecha_esperada -= timedelta(days=1)
                else:
                    break
            
            return racha
            
        except Exception:
            return 0
    
    @staticmethod
    def procesar_mensajes_alumno(alumno_id):
        """Procesa y guarda mensajes para un alumno específico"""
        try:
            alumno = PerfilAlumno.objects.get(id=alumno_id)
            
            # Evitar spam: máximo 2 mensajes por día
            hoy = timezone.now().date()
            mensajes_hoy = MensajeMotivacional.objects.filter(
                alumno=alumno,
                fecha_envio__date=hoy
            ).count()
            
            if mensajes_hoy >= 2:
                return []
            
            mensajes_generados = MotorRecomendaciones.analizar_alumno(alumno)
            mensajes_guardados = []
            
            for msg_data in mensajes_generados[:2]:  # Máximo 2 mensajes
                # Evitar duplicados recientes
                existe = MensajeMotivacional.objects.filter(
                    alumno=alumno,
                    titulo=msg_data['titulo'],
                    fecha_envio__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not existe:
                    mensaje = MensajeMotivacional.objects.create(
                        alumno=alumno,
                        **msg_data
                    )
                    mensajes_guardados.append(mensaje)
            
            return mensajes_guardados
            
        except PerfilAlumno.DoesNotExist:
            return []
    
    @staticmethod
    def ejecutar_analisis_diario():
        """Ejecuta análisis para todos los alumnos activos"""
        alumnos_activos = PerfilAlumno.objects.filter(estado='activo')
        
        for alumno in alumnos_activos:
            MotorRecomendaciones.procesar_mensajes_alumno(alumno.id)
