from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'List all users in the system'

    def handle(self, *args, **options):
        users = User.objects.all().order_by('username')
        
        if not users:
            self.stdout.write(self.style.WARNING('No users found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {users.count()} users:'))
        self.stdout.write('-' * 80)
        
        for user in users:
            status = []
            if user.is_superuser:
                status.append('SUPERUSER')
            if user.is_staff:
                status.append('STAFF')
            if not user.is_active:
                status.append('INACTIVE')
            
            status_str = f" [{', '.join(status)}]" if status else ""
            
            self.stdout.write(
                f'Username: {user.username:<20} | '
                f'Email: {user.email:<30} | '
                f'Name: {user.get_full_name():<25} | '
                f'ID: {user.id:<5}{status_str}'
            )