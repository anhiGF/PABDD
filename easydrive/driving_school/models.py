from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    is_manager = models.BooleanField(default=False)
    is_instructor = models.BooleanField(default=False)
    is_admin_staff = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)

class Branch(models.Model):
    id_branch = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return f"{self.name} - {self.city}"

class Employee(models.Model):
    ROLES = [
        ('Director', 'Director'),
        ('Instructor Senior', 'Instructor Senior'),
        ('Instructor', 'Instructor'),
        ('Administrativo', 'Administrativo'),
    ]
    
    id_employee = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLES)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"

class Client(models.Model):
    id_client = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    provisional_license = models.BooleanField(default=False)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Interview(models.Model):
    id_interview = models.AutoField(primary_key=True)
    date = models.DateField()
    comments = models.TextField(blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)

class Vehicle(models.Model):
    id_vehicle = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    license_plate = models.CharField(max_length=20, unique=True)
    inspection_date = models.DateField()
    assigned_instructor = models.OneToOneField(Employee, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.brand} {self.model} - {self.license_plate}"

class Lesson(models.Model):
    TYPES = [
        ('Individual', 'Individual'),
        ('Paquete', 'Paquete'),
    ]
    
    id_lesson = models.AutoField(primary_key=True)
    date = models.DateField()
    time = models.TimeField()
    type = models.CharField(max_length=20, choices=TYPES)
    progress = models.TextField(blank=True)
    kilometers = models.DecimalField(max_digits=5, decimal_places=2)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['date', 'time']

class Exam(models.Model):
    TYPES = [
        ('Teórico', 'Teórico'),
        ('Práctico', 'Práctico'),
    ]
    
    id_exam = models.AutoField(primary_key=True)
    date = models.DateField()
    type = models.CharField(max_length=20, choices=TYPES)
    result = models.BooleanField(null=True, blank=True)  # True=aprobado, False=reprobado
    failure_reason = models.TextField(blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)

class LessonLog(models.Model):
    id_log = models.AutoField(primary_key=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(auto_now_add=True)