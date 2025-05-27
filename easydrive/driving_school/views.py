from django.db import connection
from django.db import transaction
from datetime import date
from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from .models import *

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

