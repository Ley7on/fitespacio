from django import forms
from .models import Cliente, Profesor, Sesion, Pago, Ejercicio, Rutina, EjercicioRutina, NotificacionTemplate, ConfiguracionSistema
from django.forms import inlineformset_factory
class ClienteForm(forms.ModelForm):

    
    class Meta:
        model = Cliente
        # Removed 'suspendido' from the admin form fields per request
        fields = ['rut', 'nombre', 'email', 'telefono', 'membresia']
        widgets = {
            'rut': forms.TextInput(attrs={'placeholder': '12345678-9', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'membresia': forms.Select(attrs={'class': 'form-select'}),
            'estado_membresia': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos opcionales
        self.fields['telefono'].required = False

        # Valores por defecto
        if not self.instance.pk:
            # Use the model's default membership key (anual / 6m / 3m)
            self.fields['membresia'].initial = 'anual'
    
    def clean_rut(self):
        from .utils import validar_rut, formatear_rut, calcular_dv
        rut = self.cleaned_data.get('rut', '').strip()
        
        if not rut:
            raise forms.ValidationError("RUT es obligatorio")
        
        if not validar_rut(rut):
            # Extraer solo los números para calcular el DV correcto
            rut_limpio = rut.upper().replace('.', '').replace('-', '').replace(' ', '')
            if len(rut_limpio) >= 2 and rut_limpio[:-1].isdigit():
                numero = rut_limpio[:-1]
                dv_correcto = calcular_dv(numero)
                raise forms.ValidationError(f"RUT inválido. El dígito verificador correcto para {numero} es: {dv_correcto}")
            else:
                raise forms.ValidationError(f"RUT inválido: {rut}")
        
        rut_formateado = formatear_rut(rut)
        
        # Verificar que no exista otro cliente ACTIVO con el mismo RUT
        if Cliente.objects.filter(rut=rut_formateado, activo=True).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un cliente activo con este RUT")
        
        return rut_formateado
    

    

class ProfesorForm(forms.ModelForm):
    class Meta:
        model = Profesor
        fields = ['rut', 'nombre', 'email', 'telefono', 'especialidad']
        widgets = {
            'rut': forms.TextInput(attrs={'placeholder': '12345678-9', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Entrenamiento funcional'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos opcionales
        self.fields['telefono'].required = False
        self.fields['especialidad'].required = False
    
    def clean_rut(self):
        from .utils import validar_rut, formatear_rut, calcular_dv
        rut = self.cleaned_data.get('rut', '').strip()
        
        if not rut:
            raise forms.ValidationError("RUT es obligatorio")
        
        if not validar_rut(rut):
            # Extraer solo los números para calcular el DV correcto
            rut_limpio = rut.upper().replace('.', '').replace('-', '').replace(' ', '')
            if len(rut_limpio) >= 2 and rut_limpio[:-1].isdigit():
                numero = rut_limpio[:-1]
                dv_correcto = calcular_dv(numero)
                raise forms.ValidationError(f"RUT inválido. El dígito verificador correcto para {numero} es: {dv_correcto}")
            else:
                raise forms.ValidationError(f"RUT inválido: {rut}")
        
        rut_formateado = formatear_rut(rut)
        
        # Verificar que no exista otro profesor con el mismo RUT
        if Profesor.objects.filter(rut=rut_formateado).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un profesor con este RUT")
        
        return rut_formateado

class SesionForm(forms.ModelForm):
    class Meta:
        model = Sesion
        fields = ['nombre', 'profesor', 'horario', 'cupo', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre de la sesión de entrenamiento'
            }),
            'profesor': forms.Select(attrs={
                'class': 'form-select',
            }),
            'horario': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'cupo': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 
                'placeholder': 'Cupo máximo'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la sesión (opcional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = False


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['cliente', 'monto', 'plan', 'vencimiento', 'estado']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            # Mostrar y aceptar montos en CLP (sin decimales)
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'placeholder': '0'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'vencimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Valores por defecto
        if not self.instance.pk:
            self.fields['estado'].initial = 'Pagado'
            self.fields['plan'].initial = 'anual'

    def clean_monto(self):
        """Asegurar que el monto sea un entero (CLP) y no tenga decimales.
        Si el usuario ingresa decimales por error, redondeamos al entero más cercano.
        """
        from decimal import Decimal, ROUND_HALF_UP

        monto = self.cleaned_data.get('monto')
        if monto is None:
            return monto

        try:
            # Convertir a Decimal y redondear a 0 decimales
            m = Decimal(monto).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        except Exception:
            raise forms.ValidationError('Monto inválido')

        if m < 0:
            raise forms.ValidationError('El monto no puede ser negativo')

        return m

class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = ['nombre', 'descripcion', 'tipo', 'grupo_muscular', 'instrucciones']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'instrucciones': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class RutinaForm(forms.ModelForm):
    class Meta:
        model = Rutina
        fields = ['nombre', 'descripcion', 'objetivo', 'es_plantilla']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class EjercicioRutinaForm(forms.ModelForm):
    class Meta:
        model = EjercicioRutina
        fields = ['ejercicio', 'series', 'repeticiones', 'peso_sugerido', 'tiempo_descanso', 'orden', 'notas']
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

EjercicioRutinaFormSet = inlineformset_factory(
    Rutina, EjercicioRutina, form=EjercicioRutinaForm, extra=1, can_delete=True
)

class QRValidationForm(forms.Form):
    qr_code = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Escanear o ingresar código QR'
    }))

class NotificacionTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificacionTemplate
        fields = ['nombre', 'tipo', 'asunto', 'mensaje', 'activo']
        widgets = {
            'mensaje': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }

class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = ['clave', 'valor', 'descripcion']
        widgets = {
            'valor': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }