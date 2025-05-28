from venv import logger
from django.contrib import messages
from django.shortcuts import redirect
from django.db import connection
from django.db import transaction
from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from .models import *
from django.db.models.functions import TruncMonth

@login_required
def client_instructor_branch_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                c.id_client,
                c.first_name || ' ' || c.last_name AS client_name,
                e.user.first_name || ' ' || e.user.last_name AS instructor_name,
                b.name AS branch_name,
                b.city
            FROM
                driving_school_client c
            JOIN
                driving_school_branch b ON c.branch_id = b.id_branch
            LEFT JOIN
                driving_school_interview i ON c.id_client = i.client_id
            LEFT JOIN
                driving_school_employee e ON i.instructor_id = e.id_employee
            WHERE c.id_client = %s
        """, [request.user.client.id_client])
        
        row = cursor.fetchone()
    
    context = {
        'client': {
            'id': row[0],
            'name': row[1],
            'instructor': row[2],
            'branch': row[3],
            'city': row[4]
        }
    }
    return render(request, 'client_info.html', context)

@permission_required('driving_school.view_lesson')
def scheduled_lessons_view(request):
    lessons = Lesson.objects.select_related(
        'client', 'instructor__user', 'vehicle'
    ).filter(date=date.today()).order_by('time')
    
    return render(request, 'scheduled_lessons.html', {'lessons': lessons})


@transaction.atomic
def register_lesson(request):
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    lesson = form.save()
                    
                    # Actualizar progreso del cliente
                    client = lesson.client
                    client.provisional_license = True  # Ejemplo de actualización
                    client.save()
                    
                    # Registrar en el log
                    LessonLog.objects.create(lesson=lesson)
                    
                    messages.success(request, 'Lección registrada exitosamente')
                    return redirect('lessons')
            except Exception as e:
                messages.error(request, f'Error al registrar lección: {str(e)}')
    else:
        form = LessonForm()
    
    return render(request, 'register_lesson.html', {'form': form})

def create_stored_procedures():
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE OR REPLACE PROCEDURE register_lesson(
                p_date DATE,
                p_time TIME,
                p_type VARCHAR,
                p_progress TEXT,
                p_km NUMERIC,
                p_id_client INT,
                p_id_instructor INT,
                p_id_vehicle INT
            )
            LANGUAGE plpgsql
            AS $$
            BEGIN
                INSERT INTO driving_school_lesson (
                    date, time, type, progress, kilometers,
                    client_id, instructor_id, vehicle_id
                )
                VALUES (
                    p_date, p_time, p_type, p_progress, p_km,
                    p_id_client, p_id_instructor, p_id_vehicle
                );
            END;
            $$;
        """)
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION total_client_lessons(p_id_client INT)
            RETURNS INT
            LANGUAGE plpgsql
            AS $$
            DECLARE
                total INT;
            BEGIN
                SELECT COUNT(*) INTO total
                FROM driving_school_lesson
                WHERE client_id = p_id_client;
                
                RETURN total;
            END;
            $$;
        """)

def create_triggers():
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE OR REPLACE FUNCTION log_lesson_registration()
            RETURNS TRIGGER AS $$
            BEGIN
                INSERT INTO driving_school_lessonlog (
                    lesson_id, registration_date
                )
                VALUES (
                    NEW.id_lesson, NOW()
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        cursor.execute("""
            CREATE TRIGGER trg_log_lesson
            AFTER INSERT ON driving_school_lesson
            FOR EACH ROW
            EXECUTE FUNCTION log_lesson_registration();
        """)

#cliente
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from .models import Client
from .forms import ClientForm, LessonForm

class ClientListView(ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['clients/partials/client_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(branch__name__icontains=search_query)
            )
        
        return queryset.order_by('last_name', 'first_name')

class ClientCreateView(SuccessMessageMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client_list')
    success_message = "Cliente creado exitosamente"

class ClientUpdateView(SuccessMessageMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client_list')
    success_message = "Cliente actualizado exitosamente"

class ClientDeleteView(DeleteView):
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    success_url = reverse_lazy('client_list')
    
# driving_school/views.py
from django.db.models import Count, Sum, Case, When, IntegerField
from django.db.models.functions import TruncDate
import matplotlib.pyplot as plt
import io
import urllib, base64

@login_required
def reports_view(request):
    """
    Generate and display various reports and statistics about driving school operations.
    Includes lessons by client, today's schedule, exam results by instructor, and monthly lesson trends.
    """
    try:
        # Report 1: Top 10 clients by number of lessons
        lessons_by_client = Client.objects.annotate(
            total_lessons=Count('lesson'),
            total_kilometers=Sum('lesson__kilometers')
        ).order_by('-total_lessons')[:10]
        
        # Report 2: Today's schedule
        today_lessons = Lesson.objects.filter(date=date.today()).select_related(
            'client', 'instructor__user', 'vehicle'
        ).order_by('time')
        
        # Report 3: Exam results by instructor
        exam_stats = Employee.objects.filter(
            role__in=['Instructor', 'Instructor Senior']
        ).annotate(
            approved=Count(
                Case(
                    When(exam__result=True, then=1),
                    output_field=IntegerField()
                )
            ),
            failed=Count(
                Case(
                    When(exam__result=False, then=1),
                    output_field=IntegerField()
                )
            )
        ).order_by('-approved')
        
        # Generate monthly lesson chart
        plt.switch_backend('Agg')
        lessons_by_month = Lesson.objects.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            count=Count('id_lesson')  
        ).order_by('month')
        
        if lessons_by_month:
            months = [l['month'].strftime('%Y-%m') for l in lessons_by_month]
            counts = [l['count'] for l in lessons_by_month]
            
            plt.figure(figsize=(10, 5))
            plt.bar(months, counts)
            plt.title('Lecciones por mes')
            plt.xlabel('Mes')
            plt.ylabel('Número de lecciones')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convert plot to PNG image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plt.close()
            
            graphic = base64.b64encode(image_png).decode('utf-8')
        else:
            graphic = None
            
        context = {
            'lessons_by_client': lessons_by_client,
            'today_lessons': today_lessons,
            'exam_stats': exam_stats,
            'graphic': graphic,
        }
        return render(request, 'reports.html', context)
        
    except Exception as e:
        logger.error(f"Error generating reports: {str(e)}")
        messages.error(request, "Error generating reports. Please try again later.")
        return redirect('dashboard')

# Siempre usar parámetros en consultas SQL
def safe_query(request):
    search = request.GET.get('search')
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM clients WHERE name = %s", [search])

def home(request):
    return render(request, 'base.html')

@login_required
def dashboard(request):
    context = {
        'client_count': Client.objects.count(),
        'lessons_today': Lesson.objects.filter(date=date.today()).count(),
        'pending_exams': Exam.objects.filter(result__isnull=True).count(),
    }
    return render(request, 'dashboard.html', context)

from django.views.generic import ListView
from .models import Lesson

class LessonListView(ListView):
    model = Lesson
    template_name = 'lesson_list.html'
    context_object_name = 'lessons'

from django.views.generic import ListView
from .models import Exam

class ExamListView(ListView):
    model = Exam
    template_name = 'exam_list.html'
    context_object_name = 'exams'
    ordering = ['-date']  # Ordenar por fecha descendente

class VehicleListView(ListView):
    model = Vehicle
    template_name = 'vehicle_list.html'
    context_object_name = 'vehicles'

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def profile_view(request):
    return render(request, 'profile.html', {
        'user': request.user
    })

from .models import Branch
from .forms import BranchForm  
from django.db.models import Q

class BranchListView(ListView):
    model = Branch
    template_name = 'branch_list.html'
    context_object_name = 'branches'
    paginate_by = 10

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['partials/branch_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(address__icontains=search_query)
            )
        
        return queryset.order_by('name')
    
class BranchCreateView(SuccessMessageMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = 'branch_form.html'
    success_url = reverse_lazy('branch_list')
    success_message = "Sucursal creada exitosamente"

class BranchUpdateView(SuccessMessageMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = 'branch_form.html'
    success_url = reverse_lazy('branch_list')
    success_message = "Sucursal actualizada exitosamente"

class BranchDeleteView(DeleteView):
    model = Branch
    template_name = 'branch_confirm_delete.html'
    success_url = reverse_lazy('branch_list')

from .models import Employee
from .forms import EmployeeForm

class EmployeeListView(ListView):
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 10

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['employees/partials/employee_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(role__icontains=search_query) |
                Q(branch__name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        return queryset.order_by('user__last_name')

class EmployeeCreateView(SuccessMessageMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_form.html'
    success_url = reverse_lazy('employee_list')
    success_message = "Empleado creado exitosamente"

class EmployeeUpdateView(SuccessMessageMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_form.html'
    success_url = reverse_lazy('employee_list')
    success_message = "Empleado actualizado exitosamente"

class EmployeeDeleteView(DeleteView):
    model = Employee
    template_name = 'employees/employee_confirm_delete.html'
    success_url = reverse_lazy('employee_list')