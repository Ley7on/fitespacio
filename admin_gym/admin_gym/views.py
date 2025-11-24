from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import escape
from django.core.exceptions import ValidationError
from .models import Cliente, Profesor, Sesion, Asistencia, Pago, PerfilUsuario
from .forms import ClienteForm, ProfesorForm, SesionForm, PagoForm
import csv
import json
import logging
from datetime import timedelta
import calendar
from datetime import date

logger = logging.getLogger(__name__)

# --- Autenticación ---
def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Complete todos los campos')
            return render(request, 'admin_gym/login.html')
        
        try:
            user = authenticate(request, username=username, password=password)
            if user and user.is_active:
                login(request, user)
                
                # Verificar si debe cambiar contraseña
                try:
                    perfil = PerfilUsuario.objects.get(user=user)
                    if perfil.debe_cambiar_password:
                        return redirect('cambiar_password')
                except PerfilUsuario.DoesNotExist:
                    if not user.is_superuser:
                        messages.error(request, 'Usuario sin permisos válidos')
                        logout(request)
                        return render(request, 'admin_gym/login.html')
                
                logger.info(f'Login exitoso para usuario: {username}')
                return redirect('dashboard')
            else:
                logger.warning(f'Intento de login fallido para usuario: {username}')
                messages.error(request, 'Credenciales incorrectas')
        except Exception as e:
            logger.error(f'Error en login: {str(e)}')
            messages.error(request, 'Error interno del sistema')
    
    return render(request, 'admin_gym/login.html')

def custom_logout(request):
    logout(request)
    return redirect('login')

# --- Helpers ---
def es_admin(user):
    if not user.is_active:
        return False
    if user.is_superuser:
        return True
    try:
        perfil = PerfilUsuario.objects.get(user=user, activo=True)
        return perfil.rol in ['admin', 'recepcion']
    except PerfilUsuario.DoesNotExist:
        return False

def crear_usuario(nombre, email, rut, rol='cliente'):
    from .utils import validar_rut, formatear_rut, generar_password_temporal
    
    # Validaciones
    if not nombre or len(nombre.strip()) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres")
    
    if not email or '@' not in email:
        raise ValueError("Email inválido")
    
    if not validar_rut(rut):
        raise ValueError(f"RUT inválido: {rut}")
    
    # Verificar si el email ya existe
    if User.objects.filter(email=email).exists():
        raise ValueError(f"Ya existe un usuario con el email: {email}")
    
    rut_formateado = formatear_rut(rut)
    
    # Verificar si el RUT ya existe
    if User.objects.filter(username=rut_formateado).exists():
        raise ValueError(f"Ya existe un usuario con el RUT: {rut_formateado}")
    
    password = generar_password_temporal()
    
    try:
        user = User.objects.create_user(
            username=rut_formateado, 
            email=email, 
            password=password,
            first_name=nombre.split()[0] if nombre else '',
            last_name=' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else ''
        )
    except Exception as e:
        raise ValueError(f"Error al crear usuario: {str(e)}")
    
    PerfilUsuario.objects.get_or_create(
        user=user, 
        defaults={'debe_cambiar_password': True, 'rol': rol}
    )
    
    # Enviar credenciales por email
    try:
        asunto = "Credenciales de acceso - Fitspace "
        mensaje = f"""
Hola {nombre},

Tus credenciales de acceso al sistema Fitspace son:

Usuario (RUT): {rut_formateado}
Contraseña temporal: {password}

Por favor, cambia tu contraseña en el primer inicio de sesión.

URL de acceso: 

Saludos,
Equipo Fitspace
        """
        
        send_mail(
            asunto,
            mensaje,
            'proyectogym12@gmail.com',
            [email],
            fail_silently=False,
        )
        
        print(f"[EMAIL] Credenciales enviadas exitosamente a {email}")
        
    except Exception as e:
        print(f"[EMAIL] Error enviando a {email}: {e}")
        print(f"[CREDENCIALES] Usuario: {rut_formateado}, Password: {password}, Email: {email}")
    
    return user, password

@login_required
def cambiar_password(request):
    perfil = get_object_or_404(PerfilUsuario, user=request.user)
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            perfil.debe_cambiar_password = False
            perfil.save()
            messages.success(request, "Contraseña cambiada exitosamente.")
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'admin_gym/cambiar_contraseña.html', {'form': form})

# --- Vistas principales ---
@login_required
@user_passes_test(es_admin)
def dashboard(request):
    hoy = timezone.now().date()
    clientes_presentes = Asistencia.objects.filter(fecha__date=hoy).values('cliente').distinct().count()
    pagos_pendientes = Pago.objects.filter(estado='Pendiente').count()
    total_clientes = Cliente.objects.filter(activo=True).count()
    total_profesores = Profesor.objects.count()
    asistencias_recientes = Asistencia.objects.select_related('cliente').order_by('-fecha')[:10]
    
    return render(request, 'admin_gym/dashboard.html', {
        'asistencias_hoy': clientes_presentes,
        'pagos_pendientes': pagos_pendientes,
        'total_clientes': total_clientes,
        'total_profesores': total_profesores,
        'asistencias_recientes': asistencias_recientes,
    })

@login_required
@user_passes_test(es_admin)
def usuarios(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            try:
                cliente = form.save(commit=False)
                user, password = crear_usuario(cliente.nombre, cliente.email, cliente.rut)
                cliente.user = user
                cliente.save()
                messages.success(request, f"Cliente {cliente.nombre} creado exitosamente. Credenciales enviadas.")
                return redirect('usuarios')
            except ValueError as e:
                messages.error(request, f"Error de validación: {str(e)}")
            except Exception as e:
                messages.error(request, f"Error al crear cliente: {str(e)}")
        else:
            # Mostrar errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        form = ClienteForm()

    clientes = Cliente.objects.all()
    hoy = timezone.now().date()
    for usuario in clientes:
        usuario.asistio_hoy = Asistencia.objects.filter(cliente=usuario, fecha__date=hoy).exists()

    return render(request, 'admin_gym/usuarios.html', {'form': form, 'usuarios': clientes})

@login_required
@user_passes_test(es_admin)
def usuario_detalle(request, usuario_id):
    usuario = get_object_or_404(Cliente, id=usuario_id)
    hoy = timezone.now().date()
    asistencia = Asistencia.objects.filter(cliente=usuario, fecha__date=hoy).first()
    estado = "Presente" if asistencia else "Ausente"
    return render(request, 'admin_gym/usuario_detalle.html', {'usuario': usuario, 'estado': estado})

@login_required
@user_passes_test(es_admin)
def modificar_usuario(request, usuario_id):
    cliente = get_object_or_404(Cliente, pk=usuario_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('usuarios')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'admin_gym/modificar_usuario.html', {'form': form, 'cliente': cliente})

@login_required
@user_passes_test(es_admin)
def eliminar_usuario(request, usuario_id):
    if request.method == 'POST':
        try:
            cliente = get_object_or_404(Cliente, pk=usuario_id)
            nombre = cliente.nombre
            
            # Eliminar usuario asociado de Django
            if cliente.user:
                cliente.user.delete()
            
            # Eliminar cliente de la BD
            cliente.delete()
            
            messages.success(request, f"Cliente {nombre} eliminado completamente de la base de datos.")
        except Cliente.DoesNotExist:
            messages.error(request, "El cliente que intentas eliminar no existe.")
        except Exception as e:
            messages.error(request, f"Error al eliminar cliente: {str(e)}")
    else:
        messages.error(request, "Método no permitido. Use POST para eliminar.")
    
    return redirect('usuarios')

@login_required
@user_passes_test(es_admin)
def marcar_asistencia(request, usuario_id):
    cliente = get_object_or_404(Cliente, id=usuario_id)
    hoy = timezone.now().date()
    Asistencia.objects.get_or_create(
        cliente=cliente,
        fecha__date=hoy,
        defaults={'fecha': timezone.now()}
    )
    messages.success(request, f"Asistencia marcada para {cliente.nombre}.")
    return redirect('usuarios')

@login_required
@user_passes_test(es_admin)
def profesores(request):
    if request.method == 'POST':
        form = ProfesorForm(request.POST)
        if form.is_valid():
            try:
                profesor = form.save(commit=False)
                user, password = crear_usuario(profesor.nombre, profesor.email, profesor.rut, 'entrenador')
                user.is_staff = True  # Marcar como staff para que sea reconocido como entrenador
                user.save()
                profesor.user = user
                profesor.save()
                messages.success(request, f"Profesor {profesor.nombre} creado exitosamente. Credenciales enviadas.")
                return redirect('profesores')
            except ValueError as e:
                messages.error(request, f"Error de validación: {str(e)}")
            except Exception as e:
                messages.error(request, f"Error al crear profesor: {str(e)}")
        else:
            # Mostrar errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        form = ProfesorForm()
    
    profesores = Profesor.objects.all()
    return render(request, 'admin_gym/profesores.html', {'profesores': profesores, 'form': form})

@login_required
@user_passes_test(es_admin)
def editar_profesor(request, profesor_id):
    profesor = get_object_or_404(Profesor, pk=profesor_id)
    if request.method == 'POST':
        form = ProfesorForm(request.POST, instance=profesor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profesor {profesor.nombre} actualizado exitosamente.")
            return redirect('profesores')
    else:
        form = ProfesorForm(instance=profesor)
    return render(request, 'admin_gym/modificar_usuario.html', {'form': form, 'profesor': profesor})

@login_required
@user_passes_test(es_admin)
def eliminar_profesor(request, profesor_id):
    if request.method == 'POST':
        try:
            profesor = get_object_or_404(Profesor, pk=profesor_id)
            nombre = profesor.nombre
            
            # Eliminar usuario asociado de Django
            if profesor.user:
                profesor.user.delete()
            
            # Eliminar profesor de la BD
            profesor.delete()
            
            messages.success(request, f"Profesor {nombre} eliminado completamente de la base de datos.")
        except Profesor.DoesNotExist:
            messages.error(request, "El profesor que intentas eliminar no existe.")
        except Exception as e:
            messages.error(request, f"Error al eliminar profesor: {str(e)}")
    else:
        messages.error(request, "Método no permitido. Use POST para eliminar.")
    
    return redirect('profesores')

@login_required
@user_passes_test(es_admin)
def sesiones(request):
    if request.method == 'POST':
        form = SesionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sesiones')
    else:
        form = SesionForm()
    sesiones = Sesion.objects.select_related('profesor').all()
    return render(request, 'admin_gym/sesiones.html', {'sesiones': sesiones, 'form': form})

@login_required
@user_passes_test(es_admin)
def pagos(request):
    if request.method == 'POST':
        form = PagoForm(request.POST)
        if form.is_valid():
            # Crear instancia sin guardar para calcular vencimiento automáticamente
            pago = form.save(commit=False)

            # Fecha de inicio para el cálculo (usar fecha de pago actual si no hay otra)
            inicio = date.today()

            def add_months(d, months):
                """Agregar meses a una fecha manejando fin de mes correctamente."""
                year = d.year + (d.month - 1 + months) // 12
                month = (d.month - 1 + months) % 12 + 1
                day = d.day
                # Obtener último día del mes destino
                last_day = calendar.monthrange(year, month)[1]
                if day > last_day:
                    day = last_day
                return date(year, month, day)

            # Mapear planes a meses
            meses_por_plan = {
                'anual': 12,
                '6m': 6,
                '3m': 3,
            }

            meses = meses_por_plan.get(pago.plan, 0)
            if meses > 0:
                venc = add_months(inicio, meses)
            else:
                # Si no se reconoce el plan, usar 1 año por defecto
                venc = add_months(inicio, 12)

            pago.vencimiento = venc
            pago.save()
            messages.success(request, "Pago registrado exitosamente.")
            return redirect('pagos')
    else:
        form = PagoForm()
    
    pagos = Pago.objects.select_related('cliente').all()
    return render(request, 'admin_gym/pagos.html', {'form': form, 'pagos': pagos})

@login_required
@user_passes_test(es_admin)
def reportes(request):
    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    total_clientes = Cliente.objects.filter(activo=True).count()
    total_asistencias = Asistencia.objects.filter(fecha__date__gte=hace_30_dias).count()
    ingresos_totales = Pago.objects.filter(
        fecha_pago__date__gte=hace_30_dias,
        estado='Pagado'
    ).aggregate(total=Sum('monto'))['total'] or 0
    
    clientes_activos = Cliente.objects.filter(activo=True, estado_membresia='activa').count()
    tasa_retencion = round((clientes_activos / total_clientes * 100), 1) if total_clientes > 0 else 0
    
    clientes_recientes = Cliente.objects.filter(activo=True).order_by('-fecha_registro')[:10]
    
    # Agregar total pagado a cada cliente
    for cliente in clientes_recientes:
        total_pagado = Pago.objects.filter(
            cliente=cliente,
            estado='Pagado'
        ).aggregate(total=Sum('monto'))['total'] or 0
        cliente.total_pagado = total_pagado
    
    return render(request, 'admin_gym/reportes.html', {
        'total_clientes': total_clientes,
        'total_asistencias': total_asistencias,
        'ingresos_totales': ingresos_totales,
        'tasa_retencion': tasa_retencion,
        'clientes_recientes': clientes_recientes,
    })

@login_required
@user_passes_test(es_admin)
def configuracion(request):
    return render(request, 'admin_gym/configuracion.html')

@login_required
@user_passes_test(es_admin)
def avisar_pago(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id)
    if request.method == "POST":
        try:
            send_mail(
                'Recordatorio de pago - GymPro',
                f'Hola {pago.cliente.nombre},\n\nTe recordamos que tienes un pago pendiente por ${pago.monto} correspondiente a tu membresía {pago.get_plan_display()}.\n\nFecha de vencimiento: {pago.vencimiento.strftime("%d/%m/%Y")}\n\nPor favor, realiza el pago para continuar disfrutando de nuestros servicios.\n\nSaludos,\nEquipo GymPro',
                'proyectogym12@gmail.com',
                [pago.cliente.email],
                fail_silently=False,
            )
            messages.success(request, f'Recordatorio enviado a {pago.cliente.nombre}.')
        except Exception as e:
            messages.error(request, f'Error al enviar email: {str(e)}')
    return redirect('pagos')

@login_required
@user_passes_test(es_admin)
def marcar_pagado(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id)
    if request.method == "POST":
        pago.estado = 'Pagado'
        pago.save()
        
        # Actualizar estado del cliente
        pago.cliente.estado_membresia = 'activa'
        pago.cliente.fecha_vencimiento = pago.vencimiento
        pago.cliente.save()
        
        messages.success(request, f'Pago de {pago.cliente.nombre} marcado como pagado.')
    return redirect('pagos')

@login_required
@user_passes_test(es_admin)
def marcar_vencido(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id)
    if request.method == "POST":
        pago.estado = 'Vencido'
        pago.save()
        
        # Actualizar estado del cliente
        pago.cliente.estado_membresia = 'vencida'
        pago.cliente.save()
        
        # Enviar notificación de vencimiento
        try:
            send_mail(
                'Membresía Vencida - GymPro',
                f'Hola {pago.cliente.nombre},\n\nTu membresía ha vencido. Para continuar usando nuestros servicios, por favor renueva tu membresía.\n\nMonto: ${pago.monto}\nPlan: {pago.get_plan_display()}\n\nContacta con nosotros para renovar.\n\nSaludos,\nEquipo GymPro',
                'proyectogym12@gmail.com',
                [pago.cliente.email],
                fail_silently=False,
            )
            messages.success(request, f'Pago marcado como vencido y notificación enviada a {pago.cliente.nombre}.')
        except Exception as e:
            messages.warning(request, f'Pago marcado como vencido pero error enviando email: {str(e)}')
    return redirect('pagos')

# --- Exportación ---
@login_required
@user_passes_test(es_admin)
def exportar_reporte_pdf(request):
    try:
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from io import BytesIO
    except ImportError:
        return HttpResponse("Error: ReportLab no está instalado", status=500)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("Reporte de Gimnasio", styles['Title']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generado el: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Métricas
    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    total_clientes = Cliente.objects.filter(activo=True).count()
    total_asistencias = Asistencia.objects.filter(fecha__date__gte=hace_30_dias).count()
    ingresos_totales = Pago.objects.filter(fecha_pago__date__gte=hace_30_dias, estado='Pagado').aggregate(total=Sum('monto'))['total'] or 0
    
    metricas_data = [
        ['Métrica', 'Valor'],
        ['Total Clientes Activos', str(total_clientes)],
        ['Asistencias (30 días)', str(total_asistencias)],
        ['Ingresos (30 días)', f'${ingresos_totales:,.2f}'],
    ]
    
    metricas_table = Table(metricas_data)
    metricas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(metricas_table)
    story.append(Spacer(1, 30))
    
    # Clientes
    story.append(Paragraph("Clientes Recientes", styles['Heading2']))
    clientes_recientes = Cliente.objects.filter(activo=True).order_by('-fecha_registro')[:10]
    
    clientes_data = [['Nombre', 'Email', 'Fecha Registro', 'Estado']]
    for cliente in clientes_recientes:
        clientes_data.append([
            cliente.nombre,
            cliente.email,
            cliente.fecha_registro.strftime('%d/%m/%Y'),
            cliente.get_estado_membresia_display()
        ])
    
    clientes_table = Table(clientes_data)
    clientes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(clientes_table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_gimnasio_{hoy.strftime("%Y%m%d")}.pdf"'
    return response

@login_required
@user_passes_test(es_admin)
def exportar_reporte_excel(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reporte_clientes_{timezone.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response)
    writer.writerow(['Nombre', 'Email', 'RUT', 'Teléfono', 'Fecha Registro', 'Estado Membresía', 'Total Pagado'])
    
    clientes = Cliente.objects.filter(activo=True)
    for cliente in clientes:
        total_pagado = Pago.objects.filter(cliente=cliente, estado='Pagado').aggregate(total=Sum('monto'))['total'] or 0
        writer.writerow([
            cliente.nombre,
            cliente.email,
            cliente.rut,
            cliente.telefono,
            cliente.fecha_registro.strftime('%d/%m/%Y'),
            cliente.get_estado_membresia_display(),
            f'${total_pagado:,.2f}'
        ])
    
    return response

# --- APIs para QR Scanner ---
@login_required
@user_passes_test(es_admin)
def scanner_qr(request):
    return render(request, 'admin_gym/scanner_qr.html')

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@login_required
@user_passes_test(es_admin)
def validar_qr_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        data = json.loads(request.body)
        qr_code = data.get('qr_code', '').strip()
        
        # Validar entrada
        if not qr_code:
            return JsonResponse({'success': False, 'message': 'Código QR inválido'})
        
        # Parsear QR del alumno: user_id:token:timestamp
        try:
            parts = qr_code.split(':')
            if len(parts) != 3:
                raise ValueError("Formato QR inválido")
            
            user_id = int(parts[0])
            token = parts[1]
            timestamp = float(parts[2])
            
            # Verificar que no haya expirado (5 minutos)
            import time
            if time.time() - timestamp > 300:
                return JsonResponse({'success': False, 'message': 'QR expirado'})
            
        except (ValueError, IndexError):
            logger.warning(f'QR code no válido: {qr_code}')
            return JsonResponse({'success': False, 'message': 'Código QR no válido'})
        
        # Buscar cliente por user_id
        try:
            cliente = Cliente.objects.select_related('user').get(user_id=user_id, activo=True)
        except Cliente.DoesNotExist:
            logger.warning(f'Cliente no encontrado para user_id: {user_id}')
            return JsonResponse({'success': False, 'message': 'Cliente no encontrado'})
        
        # Verificar si puede acceder
        if not cliente.puede_acceder():
            estado = cliente.get_estado_membresia_display()
            logger.info(f'Acceso denegado para cliente {cliente.nombre}: {estado}')
            return JsonResponse({
                'success': False, 
                'message': f'Acceso denegado - Estado: {estado}'
            })
        
        # Verificar si ya marcó asistencia en las últimas 12 horas
        hace_12_horas = timezone.now() - timedelta(hours=12)
        asistencia_existente = Asistencia.objects.filter(
            cliente=cliente,
            fecha__gte=hace_12_horas
        ).first()
        
        if asistencia_existente:
            tiempo_restante = asistencia_existente.fecha + timedelta(hours=12) - timezone.now()
            horas_restantes = int(tiempo_restante.total_seconds() // 3600)
            minutos_restantes = int((tiempo_restante.total_seconds() % 3600) // 60)
            
            return JsonResponse({
                'success': False, 
                'message': f'{escape(cliente.nombre)} ya marcó asistencia. Podrá marcar nuevamente en {horas_restantes}h {minutos_restantes}m'
            })
        
        # Crear nueva asistencia
        Asistencia.objects.create(
            cliente=cliente,
            fecha=timezone.now()
        )
        
        logger.info(f'Asistencia registrada para cliente: {cliente.nombre}')
        return JsonResponse({
            'success': True,
            'message': 'Asistencia registrada exitosamente',
            'cliente_nombre': escape(cliente.nombre),
            'hora': timezone.now().strftime('%H:%M')
        })
        
    except json.JSONDecodeError:
        logger.error('Datos JSON inválidos en validar_qr_api')
        return JsonResponse({'success': False, 'message': 'Datos JSON inválidos'})
    except Exception as e:
        logger.error(f'Error en validar_qr_api: {str(e)}')
        return JsonResponse({'success': False, 'message': 'Error interno del sistema'})

@login_required
def asistencias_hoy_api(request):
    hace_12_horas = timezone.now() - timedelta(hours=12)
    asistencias = Asistencia.objects.filter(
        fecha__gte=hace_12_horas
    ).select_related('cliente').order_by('-fecha')[:20]
    
    data = {
        'asistencias': [
            {
                'cliente_nombre': asistencia.cliente.nombre,
                'hora': asistencia.fecha.strftime('%H:%M'),
                'fecha': asistencia.fecha.strftime('%d/%m/%Y'),
                'tiempo_transcurrido': str(timezone.now() - asistencia.fecha).split('.')[0]  # Formato HH:MM:SS
            }
            for asistencia in asistencias
        ]
    }
    
    return JsonResponse(data)

@login_required
def dashboard_stats_api(request):
    hoy = timezone.now().date()
    asistencias_hoy = Asistencia.objects.filter(fecha__date=hoy).values('cliente').distinct().count()
    asistencias_recientes = Asistencia.objects.select_related('cliente').order_by('-fecha')[:10]
    
    data = {
        'asistencias_hoy': asistencias_hoy,
        'asistencias_recientes': [
            {
                'cliente_nombre': asistencia.cliente.nombre,
                'fecha': asistencia.fecha.strftime('%d/%m/%Y %H:%M')
            }
            for asistencia in asistencias_recientes
        ]
    }
    
    return JsonResponse(data)