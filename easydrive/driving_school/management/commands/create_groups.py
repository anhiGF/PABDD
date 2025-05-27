# En driving_school/management/commands/create_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from driving_school.models import *

class Command(BaseCommand):
    help = 'Creates initial groups and permissions'

    def handle(self, *args, **options):
        # Create groups
        manager_group, created = Group.objects.get_or_create(name='Managers')
        instructor_group, created = Group.objects.get_or_create(name='Instructors')
        admin_group, created = Group.objects.get_or_create(name='AdminStaff')
        
        # Get all models
        models = [Branch, Employee, Client, Interview, Vehicle, Lesson, Exam]
        
        # Add permissions for each group
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            
            # Managers get all permissions
            for permission in permissions:
                manager_group.permissions.add(permission)
                
            # Instructors get view permissions
            view_perms = permissions.filter(codename__startswith='view')
            for perm in view_perms:
                instructor_group.permissions.add(perm)
                
            # Admin staff get add and view permissions
            add_view_perms = permissions.filter(codename__startswith='add') | view_perms
            for perm in add_view_perms:
                admin_group.permissions.add(perm)
        
        self.stdout.write(self.style.SUCCESS('Successfully created groups and permissions'))