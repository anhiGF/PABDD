"""
URL configuration for easydrive project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

# Importaciones necesarias
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views  # Importamos las vistas de autenticación con un alias
from driving_school import views  # Importamos todas las vistas de nuestra aplicación driving_school

# Definición de los patrones de URL
urlpatterns = [
    # URL para el panel de administración de Django (predefinido)
    path('admin/', admin.site.urls),
    
    # URL raíz que dirige a la página de inicio
    path('', views.home, name='home'),
    
    # URL para el dashboard principal de la aplicación
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # URLs para autenticación:
    # - Login usando la vista predefinida de Django pero con nuestro template personalizado
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    # - Logout usando la vista predefinida de Django
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # URL para el perfil de usuario
    path('profile/', views.profile_view, name='profile'), 

    # Sección de Reportes:
    # - Dashboard de reportes
    path('reports/', views.reports_dashboard, name='reports'),
    # - Vista dinámica para diferentes tipos de reportes
    path('reports/<str:report_type>/', views.get_report_view, name='report_view'),

    # CRUD para Sucursales:
    # - Listado de todas las sucursales (usando vista basada en clase)
    path('branch/', views.BranchListView.as_view(), name='branch_list'),
    # - Creación de nueva sucursal
    path('branch/create/', views.BranchCreateView.as_view(), name='branch_create'),
    # - Actualización de sucursal existente (por ID)
    path('branch/<int:pk>/update/', views.BranchUpdateView.as_view(), name='branch_update'),
    # - Eliminación de sucursal
    path('branch/<int:pk>/delete/', views.BranchDeleteView.as_view(), name='branch_delete'),

    # CRUD para Empleados:
    # - Listado de empleados
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    # - Creación de nuevo empleado
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    # - Actualización de empleado existente
    path('employees/<int:pk>/update/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    # - Eliminación de empleado
    path('employees/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),

    # CRUD para Clientes:
    # - Listado de clientes
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    # - Creación de nuevo cliente
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    # - Actualización de cliente existente
    path('clients/<int:pk>/update/', views.ClientUpdateView.as_view(), name='client_update'),
    # - Eliminación de cliente
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
    # - Detalle específico de un cliente
    path('clients/detalle/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    # - Edición de entrevista asociada a un cliente
    path('clients/entrevista/editar/<int:pk>/', views.InterviewUpdateView.as_view(), name='interview_update'),
    
    # CRUD para Lecciones:
    # - Listado de lecciones
    path('lessons/', views.LessonListView.as_view(), name='lesson_list'),
    # - Creación de nueva lección
    path('lessons/create/', views.LessonCreateView.as_view(), name='lesson_create'),
    # - Actualización de lección existente
    path('lessons/<int:pk>/update/', views.LessonUpdateView.as_view(), name='lesson_update'),
    # - Eliminación de lección
    path('lessons/<int:pk>/delete/', views.LessonDeleteView.as_view(), name='lesson_delete'),
    # - Detalle específico de una lección
    path('lessons/<int:pk>/', views.LessonDetailView.as_view(), name='lesson_detail'),

    # CRUD para Exámenes:
    # - Listado de exámenes
    path('exams/', views.ExamListView.as_view(), name='exam_list'),
    # - Creación de nuevo examen
    path('exams/create/', views.ExamCreateView.as_view(), name='exam_create'),
    # - Actualización de examen existente
    path('exams/<int:pk>/update/', views.ExamUpdateView.as_view(), name='exam_update'),
    # - Eliminación de examen
    path('exams/<int:pk>/delete/', views.ExamDeleteView.as_view(), name='exam_delete'),
    # - Detalle específico de un examen
    path('exams/<int:pk>/', views.ExamDetailView.as_view(), name='exam_detail'),

    # CRUD para Vehículos:
    # - Listado de vehículos
    path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    # - Creación de nuevo vehículo
    path('vehicles/nuevo/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    # - Actualización de vehículo existente
    path('vehicles/<int:pk>/update', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    # - Eliminación de vehículo
    path('vehicles/<int:pk>/delete', views.VehicleDeleteView.as_view(), name='vehicle_delete'),
    # - Detalle específico de un vehículo
    path('vehicles/<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
]