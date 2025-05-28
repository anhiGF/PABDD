"""
URL configuration for easydrive project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from driving_school import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # CRUD clientes
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/update/', views.ClientUpdateView.as_view(), name='client_update'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
    
    # Reportes
    path('reports/', views.reports_view, name='reports'),
    path('lessons/', views.LessonListView.as_view(), name='lesson_list'),
    path('exams/', views.ExamListView.as_view(), name='exam_list'),
    path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('profile/', views.profile_view, name='profile'),
     path('employees/', views.EmployeeListView.as_view(), name='employee_list'),

     # CRUD sucursales
    path('branch/', views.BranchListView.as_view(), name='branch_list'),
    path('branch/create/', views.BranchCreateView.as_view(), name='branch_create'),
    path('branch/<int:pk>/update/', views.BranchUpdateView.as_view(), name='branch_update'),
    path('branch/<int:pk>/delete/', views.BranchDeleteView.as_view(), name='branch_delete'),
]