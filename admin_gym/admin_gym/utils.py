def validar_rut(rut):
    # Elimina puntos, guiones y espacios
    rut = rut.upper().replace('.', '').replace('-', '').replace(' ', '')
    if len(rut) < 2:
        return False
    numero = rut[:-1]
    dv = rut[-1]
    if not numero.isdigit():
        return False
    
    suma = 0
    multiplicador = 2
    for c in reversed(numero):
        suma += int(c) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        dv_final = '0'
    elif dv_calculado == 10:
        dv_final = 'K'
    else:
        dv_final = str(dv_calculado)
    
    return dv == dv_final

def formatear_rut(rut):
    """
    Formatea un RUT al formato estándar 12.345.678-9
    """
    if not rut:
        return rut
    
    # Limpiar el RUT
    rut_limpio = rut.upper().replace('.', '').replace('-', '')
    
    if len(rut_limpio) < 2:
        return rut
    
    # Separar número y dígito verificador
    numero = rut_limpio[:-1]
    dv = rut_limpio[-1]
    
    # Formatear con puntos
    numero_formateado = ""
    for i, digit in enumerate(reversed(numero)):
        if i > 0 and i % 3 == 0:
            numero_formateado = "." + numero_formateado
        numero_formateado = digit + numero_formateado
    
    return f"{numero_formateado}-{dv}"

def calcular_dv(numero):
    """Calcula el dígito verificador de un RUT"""
    suma = 0
    multiplicador = 2
    for c in reversed(str(numero)):
        suma += int(c) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        return '0'
    elif dv_calculado == 10:
        return 'K'
    else:
        return str(dv_calculado)

def generar_password_temporal():
    """Genera una contraseña temporal de 6 caracteres"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))