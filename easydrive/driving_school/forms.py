# driving_school/forms.py
from django import forms
from .models import *
from .models import Exam

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'phone', 'email', 'provisional_license', 'branch']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'provisional_license': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'phone': 'Teléfono',
            'email': 'Correo Electrónico',
            'provisional_license': 'Permiso Provisional',
            'branch': 'Sucursal'
        }
    
from .models import Branch

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'city', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sucursal'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
        }
        labels = {
            'name': 'Nombre',
            'city': 'Ciudad',
            'address': 'Dirección'
        }

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import Employee

User = get_user_model()

class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(
        max_length=128,
        required=False,  # No requerido para actualización
        widget=forms.PasswordInput,
        help_text="Dejar en blanco para no cambiar (solo actualización)"
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = Employee
        exclude = ['user']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and hasattr(self.instance, 'user'):
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
            self.fields['password'].required = False
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if not self.instance.pk and User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya existe")
        return username
    
    def save(self, commit=True):
        employee = super().save(commit=False)
        user_data = {
            'username': self.cleaned_data['username'],
            'first_name': self.cleaned_data['first_name'],
            'last_name': self.cleaned_data['last_name'],
            'email': self.cleaned_data['email'],
            'is_active': True
        }
        
        # Manejar la contraseña solo si se proporciona o es un nuevo usuario
        if 'password' in self.cleaned_data and self.cleaned_data['password']:
            user_data['password'] = make_password(self.cleaned_data['password'])
        
        # Actualizar o crear usuario
        if self.instance.pk and hasattr(self.instance, 'user'):
            user = self.instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        else:
            user = User.objects.create(**user_data)
            employee.user = user
        
        if commit:
            employee.save()
            self.save_m2m()
        
        return employee

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['date', 'time', 'type', 'progress', 'kilometers', 'client', 'instructor', 'vehicle']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'progress': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'kilometers': forms.NumberInput(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'date': 'Fecha',
            'time': 'Hora',
            'type': 'Tipo',
            'progress': 'Progreso',
            'kilometers': 'Kilómetros',
            'client': 'Cliente',
            'instructor': 'Instructor',
            'vehicle': 'Vehículo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = Employee.objects.filter(role__in=['Instructor', 'Instructor Senior'])

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['date', 'type', 'result', 'failure_reason', 'client', 'instructor']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'result': forms.Select(attrs={'class': 'form-select'}, choices=[(None, '----'), (True, 'Aprobado'), (False, 'Reprobado')]),
            'failure_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'date': 'Fecha',
            'type': 'Tipo',
            'result': 'Resultado',
            'failure_reason': 'Motivo de reprobación',
            'client': 'Cliente',
            'instructor': 'Instructor'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = Employee.objects.filter(role__in=['Instructor', 'Instructor Senior'])

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['brand', 'model', 'license_plate', 'inspection_date', 'assigned_instructor']
        widgets = {
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'inspection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'assigned_instructor': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'brand': 'Marca',
            'model': 'Modelo',
            'license_plate': 'Placa',
            'inspection_date': 'Fecha de Inspección',
            'assigned_instructor': 'Instructor Asignado'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_instructor'].queryset = Employee.objects.filter(
            role__in=['Instructor', 'Instructor Senior']
        )
        self.fields['assigned_instructor'].required = False

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['date', 'comments', 'instructor']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = Employee.objects.filter(
            role__in=['Instructor', 'Instructor Senior', 'Director']
        )