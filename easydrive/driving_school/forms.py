# driving_school/forms.py
from django import forms
from .models import *

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = '__all__'
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'provisional_license': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'provisional_license': 'Permiso provisional válido',
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Client.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado")
        return email
    
# En forms.py
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