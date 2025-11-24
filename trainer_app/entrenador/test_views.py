from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def test_alumnos(request):
    """Endpoint de prueba simple"""
    logger.info(f"[TEST] Endpoint llamado - Method: {request.method}")
    
    alumnos_test = [
        {
            'id': 28,
            'nombre': 'brandon',
            'email': 'riotytmc@gmail.com',
            'telefono': '918288312',
            'membresia': 'anual',
            'rutinas_asignadas': 1
        },
        {
            'id': 29,
            'nombre': 'Branko Alejandro Plaza Gonzalez',
            'email': 'branko.plaza@inacapmail.cl',
            'telefono': '962607213',
            'membresia': '6m',
            'rutinas_asignadas': 1
        },
        {
            'id': 30,
            'nombre': 'feer',
            'email': 'fernandresp12@gmail.com',
            'telefono': '962607213',
            'membresia': 'anual',
            'rutinas_asignadas': 2
        }
    ]
    
    logger.info(f"[TEST] Devolviendo {len(alumnos_test)} alumnos de prueba")
    
    response = JsonResponse(alumnos_test, safe=False)
    response['Content-Type'] = 'application/json; charset=utf-8'
    response['Access-Control-Allow-Origin'] = '*'
    return response