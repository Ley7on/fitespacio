from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import *
import re

class AlumnoRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    telefono = forms.CharField(max_length=15, required=True)
    fecha_nacimiento = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    plan = forms.ChoiceField(choices=PerfilAlumno.PLAN_CHOICES, required=True)
    
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
            Row(
                Column('telefono', css_class='form-group col-md-6 mb-0'),
                Column('fecha_nacimiento', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'plan',
            'password1',
            'password2',
            Submit('submit', 'Registrar Alumno', css_class='btn btn-primary')
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

class PerfilAlumnoForm(forms.ModelForm):
    class Meta:
        model = PerfilAlumno
        fields = ['telefono', 'fecha_nacimiento', 'plan', 'foto_perfil', 'descripcion', 
                 'instagram', 'facebook', 'twitter']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'foto_perfil': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('telefono', css_class='form-group col-md-6 mb-0'),
                Column('fecha_nacimiento', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'plan',
            'foto_perfil',
            'descripcion',
            Row(
                Column('instagram', css_class='form-group col-md-4 mb-0'),
                Column('facebook', css_class='form-group col-md-4 mb-0'),
                Column('twitter', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Actualizar Perfil', css_class='btn btn-success')
        )

class ProgresoFisicoForm(forms.ModelForm):
    class Meta:
        model = ProgresoFisico
        fields = ['peso', 'grasa_corporal', 'masa_muscular', 'notas']
        widgets = {
            'peso': forms.NumberInput(attrs={'step': '0.1', 'min': '30', 'max': '300'}),
            'grasa_corporal': forms.NumberInput(attrs={'step': '0.1', 'min': '5', 'max': '50'}),
            'masa_muscular': forms.NumberInput(attrs={'step': '0.1', 'min': '20', 'max': '80'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

class HabitoBuenoForm(forms.ModelForm):
    class Meta:
        model = HabitoBueno
        fields = ['tipo', 'nombre', 'descripcion', 'meta_diaria', 'unidad']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'meta_diaria': forms.NumberInput(attrs={'min': '1', 'max': '20'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('tipo', css_class='form-group col-md-6 mb-0'),
                Column('nombre', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'descripcion',
            Row(
                Column('meta_diaria', css_class='form-group col-md-6 mb-0'),
                Column('unidad', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Crear Hábito', css_class='btn btn-success')
        )

class RegistroHabitoBuenoForm(forms.ModelForm):
    class Meta:
        model = RegistroHabitoBueno
        fields = ['fecha', 'cantidad', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'cantidad': forms.NumberInput(attrs={'min': '0', 'max': '50'}),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

class HabitoMaloForm(forms.ModelForm):
    class Meta:
        model = HabitoMalo
        fields = ['tipo', 'nombre', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

class RegistroHabitoMaloForm(forms.ModelForm):
    class Meta:
        model = RegistroHabitoMalo
        fields = ['fecha', 'intensidad', 'descripcion_situacion', 'reflexion']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'descripcion_situacion': forms.Textarea(attrs={'rows': 3}),
            'reflexion': forms.Textarea(attrs={'rows': 3}),
        }

class RegistroEjercicioForm(forms.ModelForm):
    class Meta:
        model = RegistroEjercicio
        fields = ['ejercicio', 'fecha', 'series', 'repeticiones', 'peso', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'series': forms.NumberInput(attrs={'min': '1', 'max': '10'}),
            'repeticiones': forms.NumberInput(attrs={'min': '1', 'max': '100'}),
            'peso': forms.NumberInput(attrs={'step': '0.5', 'min': '0', 'max': '500'}),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'ejercicio',
            'fecha',
            Row(
                Column('series', css_class='form-group col-md-4 mb-0'),
                Column('repeticiones', css_class='form-group col-md-4 mb-0'),
                Column('peso', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'notas',
            Submit('submit', 'Registrar Ejercicio', css_class='btn btn-primary')
        )

class MetaForm(forms.ModelForm):
    class Meta:
        model = Meta
        fields = ['titulo', 'descripcion', 'categoria', 'fecha_objetivo', 'valor_objetivo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'fecha_objetivo': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'titulo',
            'descripcion',
            Row(
                Column('categoria', css_class='form-group col-md-6 mb-0'),
                Column('fecha_objetivo', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'valor_objetivo',
            Submit('submit', 'Crear Meta', css_class='btn btn-success')
        )

class AccionMetaForm(forms.ModelForm):
    class Meta:
        model = AccionMeta
        fields = ['descripcion']
        widgets = {
            'descripcion': forms.TextInput(attrs={'placeholder': 'Describe la acción a realizar...'}),
        }

class ProgresoMetaForm(forms.ModelForm):
    class Meta:
        model = ProgresoMeta
        fields = ['fecha', 'valor_actual', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

class MensajeMotivacionalForm(forms.ModelForm):
    class Meta:
        model = MensajeMotivacional
        fields = ['tipo', 'titulo', 'contenido', 'prioridad', 'accion_sugerida']
        widgets = {
            'contenido': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'titulo',
            Row(
                Column('tipo', css_class='form-group col-md-6 mb-0'),
                Column('prioridad', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'contenido',
            'accion_sugerida',
            Submit('submit', 'Enviar Mensaje', css_class='btn btn-primary')
        )