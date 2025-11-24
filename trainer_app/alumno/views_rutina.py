from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

from .models import RutinaAlumno, EjercicioRutinaAlumno, Ejercicio
from entrenador.models import Ejercicio as EjercicioEntrenador

logger = logging.getLogger(__name__)

@login_required
def obtener_ejercicios(request):
    """API para obtener lista de ejercicios disponibles"""
    try:
        # Intentar obtener ejercicios del modelo de entrenador primero
        ejercicios_entrenador = EjercicioEntrenador.objects.all()
        
        if ejercicios_entrenador.exists():
            ejercicios_data = []
            for ejercicio in ejercicios_entrenador:
                ejercicios_data.append({
                    'id': ejercicio.id,
                    'nombre': ejercicio.nombre,
                    'categoria': getattr(ejercicio, 'categoria', 'general'),
                    'grupo_muscular': getattr(ejercicio, 'grupo_muscular', 'general'),
                    'descripcion': getattr(ejercicio, 'descripcion', '')
                })
        else:
            # Fallback a ejercicios del modelo de alumno
            ejercicios_alumno = Ejercicio.objects.all()
            ejercicios_data = []
            for ejercicio in ejercicios_alumno:
                ejercicios_data.append({
                    'id': ejercicio.id,
                    'nombre': ejercicio.nombre,
                    'categoria': ejercicio.categoria,
                    'grupo_muscular': getattr(ejercicio, 'musculos_principales', 'general'),
                    'descripcion': ejercicio.descripcion
                })
        
        return JsonResponse({
            'success': True,
            'ejercicios': ejercicios_data
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo ejercicios: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error obteniendo ejercicios'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def crear_rutina(request):
    """API para crear una nueva rutina"""
    try:
        data = json.loads(request.body)
        
        # Crear la rutina
        rutina = Rutina.objects.create(
            nombre=data.get('nombre'),
            objetivo=data.get('objetivo', 'hipertrofia'),
            tipo='personalizada',
            status='activa',
            creado_por=request.user,
            descripcion=data.get('descripcion', '')
        )
        
        # Añadir ejercicios a la rutina
        ejercicios_data = data.get('ejercicios', [])
        for ejercicio_data in ejercicios_data:
            try:
                # Intentar obtener el ejercicio del modelo de entrenador primero
                ejercicio = None
                try:
                    ejercicio = EjercicioEntrenador.objects.get(id=ejercicio_data['id'])
                except EjercicioEntrenador.DoesNotExist:
                    # Fallback al modelo de alumno
                    ejercicio = Ejercicio.objects.get(id=ejercicio_data['id'])
                
                EjercicioRutina.objects.create(
                    rutina=rutina,
                    ejercicio=ejercicio,
                    orden=ejercicio_data.get('orden', 1),
                    series=ejercicio_data.get('series', 3),
                    repeticiones=ejercicio_data.get('repeticiones', 10),
                    descanso=ejercicio_data.get('descanso', 60),
                    notas=ejercicio_data.get('notas', '')
                )
                
            except (EjercicioEntrenador.DoesNotExist, Ejercicio.DoesNotExist):
                logger.warning(f"Ejercicio con ID {ejercicio_data['id']} no encontrado")
                continue
        
        return JsonResponse({
            'success': True,
            'rutina_id': rutina.id,
            'message': f'Rutina "{rutina.nombre}" creada exitosamente'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creando rutina: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)

@login_required
def editar_rutina(request, rutina_id):
    """Editar una rutina existente"""
    from .models import PerfilAlumno
    perfil_alumno = PerfilAlumno.objects.get(user=request.user)
    rutina = get_object_or_404(RutinaAlumno, id=rutina_id, alumno=perfil_alumno)
    
    if request.method == 'POST':
        try:
            # Actualizar datos básicos de la rutina
            rutina.nombre = request.POST.get('nombre')
            rutina.objetivo = request.POST.get('objetivo', 'hipertrofia')
            rutina.descripcion = request.POST.get('descripcion', '')
            rutina.save()
            
            # Eliminar ejercicios existentes
            rutina.ejercicios.all().delete()
            
            # Añadir nuevos ejercicios
            ejercicios_data = request.POST.getlist('ejercicios')
            for i, ejercicio_id in enumerate(ejercicios_data):
                try:
                    ejercicio = EjercicioEntrenador.objects.get(id=ejercicio_id)
                except EjercicioEntrenador.DoesNotExist:
                    ejercicio = Ejercicio.objects.get(id=ejercicio_id)
                
                EjercicioRutinaAlumno.objects.create(
                    rutina=rutina,
                    nombre=ejercicio.nombre,
                    orden=i + 1,
                    series=int(request.POST.get(f'series_{i}', 3)),
                    repeticiones=request.POST.get(f'repeticiones_{i}', '10'),
                    descanso=f"{request.POST.get(f'descanso_{i}', 60)}s",
                    notas=request.POST.get(f'notas_{i}', '')
                )
            
            messages.success(request, f'Rutina "{rutina.nombre}" actualizada exitosamente')
            return redirect('alumno:rutinas')
            
        except Exception as e:
            logger.error(f"Error editando rutina: {e}")
            messages.error(request, 'Error actualizando la rutina')
    
    # Obtener ejercicios de la rutina
    ejercicios_rutina = EjercicioRutina.objects.filter(rutina=rutina).order_by('orden')
    
    # Obtener todos los ejercicios disponibles
    ejercicios_disponibles = list(EjercicioEntrenador.objects.all()) + list(Ejercicio.objects.all())
    
    context = {
        'rutina': rutina,
        'ejercicios_rutina': ejercicios_rutina,
        'ejercicios_disponibles': ejercicios_disponibles
    }
    
    return render(request, 'alumno/editar_rutina.html', context)

@login_required
def eliminar_rutina(request, rutina_id):
    """Eliminar una rutina"""
    if request.method == 'POST':
        try:
            from .models import PerfilAlumno
            perfil_alumno = PerfilAlumno.objects.get(user=request.user)
            rutina = get_object_or_404(RutinaAlumno, id=rutina_id, alumno=perfil_alumno)
            nombre = rutina.nombre
            rutina.delete()
            
            messages.success(request, f'Rutina "{nombre}" eliminada exitosamente')
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Error eliminando rutina: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Error eliminando rutina'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)