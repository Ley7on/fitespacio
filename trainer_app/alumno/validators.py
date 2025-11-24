"""
Validadores para el flujo de creación de rutinas del alumno.
"""


def validate_payload(data):
    """
    Valida el payload JSON para crear una rutina personalizada.
    
    Retorna:
        (is_valid: bool, result: dict)
        - Si es válido: (True, {"nombre": ..., "objetivo": ..., "dia": ..., "ejercicios": [...]})
        - Si no es válido: (False, {"campo": ["error1", "error2"], ...})
    """
    errors = {}
    
    # Validar nombre
    nombre = data.get("nombre", "").strip() if isinstance(data.get("nombre"), str) else ""
    if not nombre:
        errors.setdefault("nombre", []).append("El nombre es requerido.")
    elif len(nombre) < 2:
        errors.setdefault("nombre", []).append("El nombre debe tener al menos 2 caracteres.")
    elif len(nombre) > 100:
        errors.setdefault("nombre", []).append("El nombre no puede exceder 100 caracteres.")
    
    # Validar objetivo
    objetivo = data.get("objetivo", "").strip() if isinstance(data.get("objetivo"), str) else ""
    objetivo_choices = ["fuerza", "hipertrofia", "resistencia", "perdida_grasa", "funcional"]
    if not objetivo:
        errors.setdefault("objetivo", []).append("El objetivo es requerido.")
    elif objetivo.lower() not in objetivo_choices:
        errors.setdefault("objetivo", []).append(
            f"Objetivo inválido. Debe ser uno de: {', '.join(objetivo_choices)}"
        )
    
    # Validar descripcion (opcional)
    descripcion = data.get("descripcion", "").strip() if isinstance(data.get("descripcion"), str) else ""
    
    # Validar dia (opcional)
    dias_choices = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    dia = data.get("dia", "").strip() if isinstance(data.get("dia"), str) else ""
    if dia and dia.lower() not in dias_choices:
        errors.setdefault("dia", []).append(
            f"Día inválido. Debe ser uno de: {', '.join(dias_choices)}"
        )
    
    # Validar ejercicios
    ejercicios = data.get("ejercicios", [])
    if not isinstance(ejercicios, list):
        errors.setdefault("ejercicios", []).append("Los ejercicios debe ser una lista.")
    elif len(ejercicios) == 0:
        errors.setdefault("ejercicios", []).append("Debe incluir al menos 1 ejercicio.")
    else:
        ejercicios_validados = []
        for idx, ej in enumerate(ejercicios):
            if not isinstance(ej, dict):
                errors.setdefault(f"ejercicios[{idx}]", []).append("Cada ejercicio debe ser un objeto JSON.")
                continue
            
            ej_errors = {}
            
            # Nombre del ejercicio
            ej_nombre = ej.get("nombre", "").strip() if isinstance(ej.get("nombre"), str) else ""
            if not ej_nombre:
                ej_errors.setdefault("nombre", []).append("El nombre del ejercicio es requerido.")
            elif len(ej_nombre) < 2:
                ej_errors.setdefault("nombre", []).append("El nombre debe tener al menos 2 caracteres.")
            elif len(ej_nombre) > 120:
                ej_errors.setdefault("nombre", []).append("El nombre no puede exceder 120 caracteres.")
            
            # Series
            try:
                series = int(ej.get("series", 0))
                if series <= 0:
                    ej_errors.setdefault("series", []).append("Las series deben ser mayor a 0.")
            except (ValueError, TypeError):
                ej_errors.setdefault("series", []).append("Las series deben ser un número entero.")
            
            # Repeticiones (reps)
            reps = ej.get("reps", "").strip() if isinstance(ej.get("reps"), str) else ""
            if not reps:
                ej_errors.setdefault("reps", []).append("Las repeticiones son requeridas.")
            
            # Descanso (opcional, en segundos)
            try:
                descanso = int(ej.get("descanso", 60))
                if descanso < 0:
                    ej_errors.setdefault("descanso", []).append("El descanso no puede ser negativo.")
            except (ValueError, TypeError):
                ej_errors.setdefault("descanso", []).append("El descanso debe ser un número.")
            
            # Peso (opcional)
            peso_val = None
            if ej.get("peso") is not None:
                try:
                    peso_val = int(ej.get("peso"))
                    if peso_val < 0:
                        ej_errors.setdefault("peso", []).append("El peso no puede ser negativo.")
                except (ValueError, TypeError):
                    ej_errors.setdefault("peso", []).append("El peso debe ser un número.")
            
            if ej_errors:
                for campo, msgs in ej_errors.items():
                    errors.setdefault(f"ejercicios[{idx}].{campo}", []).extend(msgs)
            else:
                ejercicios_validados.append({
                    "nombre": ej_nombre,
                    "series": series,
                    "reps": reps,
                    "peso": peso_val,
                    "descanso": descanso,
                })
    
    if errors:
        return False, errors
    
    # Retornar datos limpios
    cleaned = {
        "nombre": nombre,
        "objetivo": objetivo.lower(),
        "descripcion": descripcion,
        "dia": dia.lower() if dia else "",
        "ejercicios": ejercicios_validados if isinstance(ejercicios, list) else [],
    }
    
    return True, cleaned
