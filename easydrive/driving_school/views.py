from venv import logger
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
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
                    client.provisional_license = True  
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
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from .models import Client
from .forms import ClientForm, ExamForm, InterviewForm, LessonForm, VehicleForm

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
    template_name = 'clients/client_interview_form.html'  # Nueva plantilla
    success_url = reverse_lazy('client_list')
    success_message = "Cliente y entrevista creados exitosamente"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['interview_form'] = InterviewForm(self.request.POST)
        else:
            context['interview_form'] = InterviewForm()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        interview_form = context['interview_form']
        
        if interview_form.is_valid():
            self.object = form.save()
            interview = interview_form.save(commit=False)
            interview.client = self.object
            interview.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

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

class EmployeeCreateView(CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_form.html'
    success_url = reverse_lazy('employee_list')

    def form_valid(self, form):
        # El método save() del formulario ahora maneja la creación del usuario
        return super().form_valid(form)

class EmployeeUpdateView(UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_form.html'
    success_url = reverse_lazy('employee_list')

class EmployeeDeleteView(DeleteView):
    model = Employee
    template_name = 'employees/employee_confirm_delete.html'
    success_url = reverse_lazy('employee_list')

from .models import Lesson
from .forms import LessonForm

class LessonListView(ListView):
    model = Lesson
    template_name = 'lessons/lesson_list.html'
    context_object_name = 'lessons'
    paginate_by = 10

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['lessons/partials/lesson_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(client__first_name__icontains=search_query) |
                Q(client__last_name__icontains=search_query) |
                Q(instructor__user__first_name__icontains=search_query) |
                Q(instructor__user__last_name__icontains=search_query) |
                Q(vehicle__license_plate__icontains=search_query) |
                Q(type__icontains=search_query)
            )
        
        return queryset

class LessonCreateView(SuccessMessageMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'lessons/lesson_form.html'
    success_url = reverse_lazy('lesson_list')
    success_message = "Lección creada exitosamente"

class LessonUpdateView(SuccessMessageMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'lessons/lesson_form.html'
    success_url = reverse_lazy('lesson_list')
    success_message = "Lección actualizada exitosamente"

class LessonDeleteView(DeleteView):
    model = Lesson
    template_name = 'lessons/lesson_confirm_delete.html'
    success_url = reverse_lazy('lesson_list')

class LessonDetailView(DetailView):
    model = Lesson
    template_name = 'lessons/lesson_detail.html'

#examenes
class ExamListView(ListView):
    model = Exam
    template_name = 'exams/exam_list.html'
    context_object_name = 'exams'
    paginate_by = 10

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['exams/partials/exam_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(client__first_name__icontains=search_query) |
                Q(client__last_name__icontains=search_query) |
                Q(instructor__user__first_name__icontains=search_query) |
                Q(instructor__user__last_name__icontains=search_query) |
                Q(type__icontains=search_query)
            )
        
        return queryset.order_by('-date')

class ExamCreateView(SuccessMessageMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = 'exams/exam_form.html'
    success_url = reverse_lazy('exam_list')
    success_message = "Examen creado exitosamente"

class ExamUpdateView(SuccessMessageMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = 'exams/exam_form.html'
    success_url = reverse_lazy('exam_list')
    success_message = "Examen actualizado exitosamente"

class ExamDeleteView(DeleteView):
    model = Exam
    template_name = 'exams/exam_confirm_delete.html'
    success_url = reverse_lazy('exam_list')

class ExamDetailView(DetailView):
    model = Exam
    template_name = 'exams/exam_detail.html'


#auto
class VehicleListView(ListView):
    model = Vehicle
    template_name = 'vehicles/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 10

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['vehicles/partials/vehicle_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(brand__icontains=search_query) |
                Q(model__icontains=search_query) |
                Q(license_plate__icontains=search_query) |
                Q(assigned_instructor__user__first_name__icontains=search_query) |
                Q(assigned_instructor__user__last_name__icontains=search_query)
            )
        
        return queryset.order_by('brand', 'model')

class VehicleCreateView(SuccessMessageMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/vehicle_form.html'
    success_url = reverse_lazy('vehicle_list')
    success_message = "Vehículo creado exitosamente"

class VehicleUpdateView(SuccessMessageMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/vehicle_form.html'
    success_url = reverse_lazy('vehicle_list')
    success_message = "Vehículo actualizado exitosamente"

class VehicleDeleteView(DeleteView):
    model = Vehicle
    template_name = 'vehicles/vehicle_confirm_delete.html'
    success_url = reverse_lazy('vehicle_list')

class VehicleDetailView(DetailView):
    model = Vehicle
    template_name = 'vehicles/vehicle_detail.html'

class ClientDetailView(DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['interview'] = self.object.interview
        return context
    
class InterviewUpdateView(SuccessMessageMixin, UpdateView):
    model = Interview
    form_class = InterviewForm
    template_name = 'clients/interview_form.html'
    success_url = reverse_lazy('client_list')
    success_message = "Entrevista actualizada exitosamente"

from django.contrib.auth.decorators import permission_required
from django.shortcuts import render
from django.db import connection
from django.core.paginator import Paginator
from .forms import ReportFilterForm
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

@permission_required('driving_school.view_reports')
def reports_dashboard(request):
    """Vista principal del dashboard de reportes"""
    report_types = [
        {'id': 'client_progress', 'name': 'Progreso de Clientes'},
        {'id': 'vehicle_usage', 'name': 'Uso de Vehículos'},
        {'id': 'instructor_hours', 'name': 'Horas de Instructores'},
        {'id': 'scheduled_lessons', 'name': 'Lecciones Programadas'},
        {'id': 'client_instructor', 'name': 'Clientes por Instructor/Sucursal'},
    ]
    
    return render(request, 'reports/dashboard.html', {'report_types': report_types})

def get_report_view(request, report_type):
    """Función central que maneja todos los reportes con filtros"""
    # Obtener parámetros de filtro
    form = ReportFilterForm(request.GET or None)
    
    if not form.is_valid():
        return render(request, 'reports/filter_form.html', {'form': form, 'report_type': report_type})
    
    # Procesar filtros
    filters = {
        'start_date': form.cleaned_data.get('start_date'),
        'end_date': form.cleaned_data.get('end_date'),
        'branch': form.cleaned_data.get('branch'),
        'instructor': form.cleaned_data.get('instructor'),
        'client': form.cleaned_data.get('client'),
        'vehicle': form.cleaned_data.get('vehicle'),
        'lesson_type': form.cleaned_data.get('lesson_type'),
    }
    
    # Obtener datos según el tipo de reporte
    data = []
    if report_type == 'client_progress':
        data = get_client_progress_data(filters)
    elif report_type == 'vehicle_usage':
        data = get_vehicle_usage_data(filters)
    elif report_type == 'instructor_hours':
        data = get_instructor_hours_data(filters)
    elif report_type == 'scheduled_lessons':
        data = get_scheduled_lessons_data(filters)
    elif report_type == 'client_instructor':
        data = get_client_instructor_data(filters)
    
    # Paginación
    paginator = Paginator(data, 25)  # 25 items por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'data': page_obj,
        'form': form,
        'report_type': report_type,
        'report_title': get_report_title(report_type),
    }
    
    if request.GET.get('export') == 'pdf':
        return generate_pdf_report(context, report_type)
    
    return render(request, 'reports/report_results.html', context)

# Funciones específicas para cada reporte
def get_client_progress_data(filters):
    """Reporte de progreso de clientes"""
    with connection.cursor() as cursor:
        query = """
            SELECT 
                c.id_client, 
                c.first_name || ' ' || c.last_name AS client_name,
                COUNT(l.id_lesson) AS total_lessons,
                MAX(l.date) AS last_lesson_date,
                c.provisional_license,
                b.name AS branch_name
            FROM 
                driving_school_client c
            LEFT JOIN 
                driving_school_lesson l ON c.id_client = l.client_id
            JOIN 
                driving_school_branch b ON c.branch_id = b.id_branch
            WHERE 1=1
        """
        
        params = []
        
        if filters['start_date']:
            query += " AND l.date >= %s"
            params.append(filters['start_date'])
            
        if filters['end_date']:
            query += " AND l.date <= %s"
            params.append(filters['end_date'])
            
        if filters['branch']:
            query += " AND b.id_branch = %s"
            params.append(filters['branch'])
            
        query += " GROUP BY c.id_client, b.name ORDER BY client_name"
        
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_vehicle_usage_data(filters):
    """Reporte de uso de vehículos"""
    with connection.cursor() as cursor:
        query = """
            SELECT 
                v.id_vehicle,
                v.plate_number,
                v.model,
                v.year,
                COUNT(l.id_lesson) AS total_lessons,
                SUM(l.kilometers) AS total_kilometers,
                AVG(l.kilometers) AS avg_kilometers_per_lesson
            FROM 
                driving_school_vehicle v
            LEFT JOIN 
                driving_school_lesson l ON v.id_vehicle = l.vehicle_id
            WHERE 1=1
        """
        
        params = []
        
        if filters['start_date']:
            query += " AND l.date >= %s"
            params.append(filters['start_date'])
            
        if filters['end_date']:
            query += " AND l.date <= %s"
            params.append(filters['end_date'])
            
        if filters['vehicle']:
            query += " AND v.id_vehicle = %s"
            params.append(filters['vehicle'])
            
        query += " GROUP BY v.id_vehicle ORDER BY total_lessons DESC"
        
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_instructor_hours_data(filters):
    """Reporte de horas de instructores"""
    with connection.cursor() as cursor:
        query = """
            SELECT 
                e.id_employee,
                u.first_name || ' ' || u.last_name AS instructor_name,
                b.name AS branch_name,
                COUNT(l.id_lesson) AS total_lessons,
                COUNT(DISTINCT l.client_id) AS total_clients
            FROM 
                driving_school_employee e
            JOIN 
                auth_user u ON e.user_id = u.id
            LEFT JOIN 
                driving_school_lesson l ON e.id_employee = l.instructor_id
            JOIN 
                driving_school_branch b ON e.branch_id = b.id_branch
            WHERE e.role = 'instructor'
        """
        
        params = []
        
        if filters['start_date']:
            query += " AND l.date >= %s"
            params.append(filters['start_date'])
            
        if filters['end_date']:
            query += " AND l.date <= %s"
            params.append(filters['end_date'])
            
        if filters['branch']:
            query += " AND b.id_branch = %s"
            params.append(filters['branch'])
            
        if filters['instructor']:
            query += " AND e.id_employee = %s"
            params.append(filters['instructor'])
            
        query += " GROUP BY e.id_employee, u.first_name, u.last_name, b.name ORDER BY total_lessons DESC"
        
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_scheduled_lessons_data(filters):
    """Reporte de lecciones programadas (mejorada)"""
    query = Lesson.objects.select_related(
        'client', 'instructor__user', 'vehicle', 'branch'
    ).order_by('date', 'time')
    
    if filters['start_date']:
        query = query.filter(date__gte=filters['start_date'])
        
    if filters['end_date']:
        query = query.filter(date__lte=filters['end_date'])
        
    if filters['branch']:
        query = query.filter(branch=filters['branch'])
        
    if filters['instructor']:
        query = query.filter(instructor=filters['instructor'])
        
    if filters['client']:
        query = query.filter(client=filters['client'])
        
    if filters['vehicle']:
        query = query.filter(vehicle=filters['vehicle'])
        
    if filters['lesson_type']:
        query = query.filter(type=filters['lesson_type'])
    
    return query

def get_client_instructor_data(filters):
    """Reporte de clientes por instructor/sucursal (mejorada)"""
    with connection.cursor() as cursor:
        query = """
            SELECT
                c.id_client,
                c.first_name || ' ' || c.last_name AS client_name,
                e.user.first_name || ' ' || e.user.last_name AS instructor_name,
                b.name AS branch_name,
                b.city,
                COUNT(l.id_lesson) AS total_lessons
            FROM
                driving_school_client c
            JOIN
                driving_school_branch b ON c.branch_id = b.id_branch
            LEFT JOIN
                driving_school_interview i ON c.id_client = i.client_id
            LEFT JOIN
                driving_school_employee e ON i.instructor_id = e.id_employee
            LEFT JOIN
                driving_school_lesson l ON c.id_client = l.client_id
            WHERE 1=1
        """
        
        params = []
        
        if filters['branch']:
            query += " AND b.id_branch = %s"
            params.append(filters['branch'])
            
        if filters['instructor']:
            query += " AND e.id_employee = %s"
            params.append(filters['instructor'])
            
        if filters['client']:
            query += " AND c.id_client = %s"
            params.append(filters['client'])
            
        if filters['start_date']:
            query += " AND l.date >= %s"
            params.append(filters['start_date'])
            
        if filters['end_date']:
            query += " AND l.date <= %s"
            params.append(filters['end_date'])
            
        query += " GROUP BY c.id_client, e.user.first_name, e.user.last_name, b.name, b.city"
        query += " ORDER BY client_name"
        
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def generate_pdf_report(context, report_type):
    """Genera un PDF profesional del reporte"""
    template_path = 'reports/pdf_template.html'
    template = get_template(template_path)
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    
    return response

def get_report_title(report_type):
    """Devuelve el título del reporte según su tipo"""
    titles = {
        'client_progress': 'Reporte de Progreso de Clientes',
        'vehicle_usage': 'Reporte de Uso de Vehículos',
        'instructor_hours': 'Reporte de Horas de Instructores',
        'scheduled_lessons': 'Reporte de Lecciones Programadas',
        'client_instructor': 'Reporte de Clientes por Instructor/Sucursal',
    }
    return titles.get(report_type, 'Reporte')