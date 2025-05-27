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