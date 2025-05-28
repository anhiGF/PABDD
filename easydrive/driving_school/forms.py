# driving_school/forms.py
from datetime import timezone
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from .models import *

# ==============================================
# VALIDADORES PERSONALIZADOS
# ==============================================

# Validador para solo letras (incluye acentos y espacios)
letters_only = RegexValidator(
    r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    'Este campo solo permite letras y espacios.'
)

# Validador para campos alfanuméricos con caracteres básicos
no_special_chars = RegexValidator(
    r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,-]+$',
    'No se permiten caracteres especiales excepto .,-'
)

# Validador para teléfonos (números, espacios, +, -)
phone_validator = RegexValidator(
    r'^[\d\s+-]+$',
    'Solo números, espacios y los caracteres + -'
)

# Validador para placas de vehículos (letras, números, guiones)
license_plate_validator = RegexValidator(
    r'^[a-zA-Z0-9-]+$',
    'Solo letras, números y guiones (-)'
)

# Validador para emails institucionales (opcional)
def validate_company_email(value):
    if not value.endswith('@easydrive.com'):
        raise ValidationError('Debe usar un correo corporativo (@easydrive.com)')

# ==============================================
# FORMULARIO DE CLIENTE (VALIDACIONES COMPLETAS)
# ==============================================

class ClientForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=100,
        validators=[letters_only],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=100,
        validators=[letters_only],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Apellido'
    )
    phone = forms.CharField(
        max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Teléfono'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Correo Electrónico'
    )

    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'phone', 'email', 'provisional_license', 'branch']
        widgets = {
            'provisional_license': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'provisional_license': 'Permiso Provisional',
            'branch': 'Sucursal'
        }

    def clean_email(self):
        """Valida que el correo no esté registrado"""
        email = self.cleaned_data.get('email')
        if Client.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este correo ya está registrado')
        return email

# ==============================================
# FORMULARIO DE SUCURSAL (VALIDACIONES COMPLETAS)
# ==============================================

class BranchForm(forms.ModelForm):
    name = forms.CharField(
        validators=[no_special_chars],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: EasyDrive Centro'}),
        label='Nombre'
    )
    city = forms.CharField(
        validators=[letters_only],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Madrid'}),
        label='Ciudad'
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Calle, número, código postal'}),
        label='Dirección',
        validators=[RegexValidator(
            r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,#-]+$',
            'No se permiten caracteres especiales excepto .,-#'
        )]
    )

    class Meta:
        model = Branch
        fields = ['name', 'city', 'address']

# ==============================================
# FORMULARIO DE EMPLEADO (VALIDACIONES COMPLETAS)
# ==============================================

User = get_user_model()

class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        validators=[letters_only],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        validators=[letters_only],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Apellido'
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre de Usuario'
    )
    password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Dejar en blanco para no cambiar (solo actualización)"
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        validators=[validate_company_email]  # Solo correos corporativos
    )

    class Meta:
        model = Employee
        exclude = ['user']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        if not self.instance.pk and User.objects.filter(username=username).exists():
            raise ValidationError("Este usuario ya existe")
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
        
        if 'password' in self.cleaned_data and self.cleaned_data['password']:
            user_data['password'] = make_password(self.cleaned_data['password'])
        
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

# ==============================================
# FORMULARIO DE VEHÍCULO (VALIDACIONES COMPLETAS)
# ==============================================

class VehicleForm(forms.ModelForm):
    brand = forms.CharField(
        validators=[no_special_chars],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Marca'
    )
    model = forms.CharField(
        validators=[no_special_chars],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Modelo'
    )
    license_plate = forms.CharField(
        validators=[license_plate_validator],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Placa'
    )
    inspection_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Fecha de Inspección'
    )

    class Meta:
        model = Vehicle
        fields = ['brand', 'model', 'license_plate', 'inspection_date', 'assigned_instructor']
        widgets = {
            'assigned_instructor': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'assigned_instructor': 'Instructor Asignado'
        }

    def clean_license_plate(self):
        plate = self.cleaned_data.get('license_plate')
        if Vehicle.objects.filter(license_plate=plate).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Esta placa ya está registrada')
        return plate

# ==============================================
# FORMULARIO DE LECCIÓN (VALIDACIONES COMPLETAS)
# ==============================================

class LessonForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Fecha'
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label='Hora'
    )
    kilometers = forms.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Kilómetros'
    )

    class Meta:
        model = Lesson
        fields = ['date', 'time', 'type', 'progress', 'kilometers', 'client', 'instructor', 'vehicle']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'progress': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'type': 'Tipo',
            'progress': 'Progreso',
            'client': 'Cliente',
            'instructor': 'Instructor',
            'vehicle': 'Vehículo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = Employee.objects.filter(role__in=['Instructor', 'Instructor Senior'])

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        instructor = cleaned_data.get('instructor')
        vehicle = cleaned_data.get('vehicle')

        if date and date < timezone.now().date():
            raise ValidationError("No se pueden agendar lecciones en fechas pasadas")

        if instructor and vehicle and instructor != vehicle.assigned_instructor:
            raise ValidationError("El instructor no está asignado a este vehículo")

        return cleaned_data

# ==============================================
# FORMULARIO DE EXAMEN (VALIDACIONES COMPLETAS)
# ==============================================

class ExamForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Fecha'
    )
    failure_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Motivo de reprobación'
    )

    class Meta:
        model = Exam
        fields = ['date', 'type', 'result', 'failure_reason', 'client', 'instructor']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'result': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'type': 'Tipo',
            'result': 'Resultado',
            'client': 'Cliente',
            'instructor': 'Instructor'
        }

    def clean(self):
        cleaned_data = super().clean()
        result = cleaned_data.get('result')
        failure_reason = cleaned_data.get('failure_reason')

        if result is False and not failure_reason:
            raise ValidationError("Debe especificar el motivo de reprobación")

        return cleaned_data

# ==============================================
# FORMULARIO DE ENTREVISTA (VALIDACIONES COMPLETAS)
# ==============================================

class InterviewForm(forms.ModelForm):
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        validators=[RegexValidator(
            r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,;!?()-]+$',
            'No se permiten caracteres especiales excepto .,;!?()-'
        )],
        label='Comentarios'
    )

    class Meta:
        model = Interview
        fields = ['date', 'comments', 'instructor']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = Employee.objects.filter(
            role__in=['Instructor', 'Instructor Senior', 'Director']
        )


from django import forms
from .models import *

class ReportFilterForm(forms.Form):
    start_date = forms.DateField(
        label='Fecha inicial',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    end_date = forms.DateField(
        label='Fecha final',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    branch = forms.ModelChoiceField(
        label='Sucursal',
        queryset=Branch.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    instructor = forms.ModelChoiceField(
        label='Instructor',
        queryset=Employee.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    client = forms.ModelChoiceField(
        label='Cliente',
        queryset=Client.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vehicle = forms.ModelChoiceField(
        label='Vehículo',
        queryset=Vehicle.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    lesson_type = forms.ChoiceField(
        label='Tipo de lección',
        choices=LESSON_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("La fecha inicial no puede ser mayor que la fecha final")
        
        return cleaned_data
    
class InstructorHoursFilterForm(forms.Form):
    instructor = forms.ModelChoiceField(
        queryset=Employee.objects.filter(role='instructor'),
        required=False,
        label="Instructor",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date = forms.DateField(
        required=False,
        label="Fecha inicial",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    end_date = forms.DateField(
        required=False,
        label="Fecha final", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )