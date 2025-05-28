# driving_school/forms.py
from django import forms
from .models import *

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

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['user', 'branch', 'role', 'phone', 'email']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': 'Usuario',
            'branch': 'Sucursal',
            'role': 'Rol',
            'phone': 'Teléfono',
            'email': 'Correo Electrónico'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = CustomUser.objects.filter(is_staff=True)


# leccion
class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        
        # Validar que la lección esté dentro del horario laboral
        if time and (time < time(8, 0) or time > time(20, 0)):
            raise forms.ValidationError("Las lecciones deben programarse entre 8:00 y 20:00")
        
        # Validar que el vehículo esté disponible
        if date and time and 'vehicle' in cleaned_data:
            conflicting_lessons = Lesson.objects.filter(
                date=date,
                time=time,
                vehicle=cleaned_data['vehicle']
            ).exclude(pk=self.instance.pk)
            
            if conflicting_lessons.exists():
                raise forms.ValidationError("El vehículo ya está asignado a otra lección en este horario")
        
        return cleaned_data