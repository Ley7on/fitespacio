from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import *
import re

class EntrenadorRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    telefono = forms.CharField(max_length=15, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'username',
            'email',
            'telefono',
            'password1',
            'password2',
            Submit('submit', 'Registrar Entrenador', css_class='btn btn-primary')
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este email ya está registrado.")
        return email
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not re.match(r'^\+?1?\d{9,15}$', telefono):
            raise ValidationError("Formato de teléfono inválido.")
        return telefono

class RutinaForm(forms.ModelForm):
    class Meta:
        model = Rutina
        fields = ['nombre', 'alumno', 'fecha_revision']
        widgets = {
            'fecha_revision': forms.DateInput(attrs={'type': 'date'}),
            'alumno': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'nombre',
            'alumno',
            'fecha_revision',
            Submit('submit', 'Crear Rutina', css_class='btn btn-success')
        )

class DetalleEjercicioForm(forms.ModelForm):
    class Meta:
        model = DetalleEjercicio
        fields = ['ejercicio', 'series', 'repeticiones']
        widgets = {
            'ejercicio': forms.Select(attrs={'class': 'form-select'}),
            'series': forms.NumberInput(attrs={'min': '1', 'max': '10'}),
        }

class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = ['nombre', 'grupo_muscular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'grupo_muscular': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AsistenciaEntrenadorForm(forms.ModelForm):
    class Meta:
        model = AsistenciaEntrenador
        fields = ['fecha', 'hora_entrada', 'hora_salida', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora_entrada': forms.TimeInput(attrs={'type': 'time'}),
            'hora_salida': forms.TimeInput(attrs={'type': 'time'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

class EventoCalendarioForm(forms.ModelForm):
    class Meta:
        model = EventoCalendario
        fields = ['titulo', 'descripcion', 'tipo', 'fecha_inicio', 'fecha_fin', 'alumno', 'color']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'titulo',
            'descripcion',
            Row(
                Column('tipo', css_class='form-group col-md-6 mb-0'),
                Column('color', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('fecha_inicio', css_class='form-group col-md-6 mb-0'),
                Column('fecha_fin', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'alumno',
            Submit('submit', 'Crear Evento', css_class='btn btn-primary')
        )

class PlantillaExcelForm(forms.ModelForm):
    class Meta:
        model = PlantillaExcel
        fields = ['nombre', 'archivo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}),
        }
    
    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            if not archivo.name.endswith(('.xlsx', '.xls')):
                raise ValidationError("Solo se permiten archivos Excel (.xlsx, .xls)")
            if archivo.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError("El archivo no puede ser mayor a 5MB")
        return archivo