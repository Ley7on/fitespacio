# views_rutinas_nuevo.py - Vista para el nuevo sistema de rutinas del alumno

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

@login_required
def rutinas_nuevo(request):
    """Vista principal del nuevo sistema de rutinas del alumno"""
    try:
        context = {
            'user': request.user,
        }
        
        return render(request, 'alumno/rutinas_nuevo.html', context)
        
    except Exception as e:
        logger.error(f"Error en rutinas_nuevo: {e}")
        context = {
            'user': request.user,
            'error_message': 'Error cargando las rutinas'
        }
        return render(request, 'alumno/rutinas_nuevo.html', context)