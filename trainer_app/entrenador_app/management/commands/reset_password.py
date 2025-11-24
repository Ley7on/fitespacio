from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

class Command(BaseCommand):
    help = 'Reset password for a user and show the new password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to reset password')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            
            # Generate new password
            new_password = get_random_string(12, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Password reset successfully for user: {username}\n'
                    f'New password: {new_password}\n'
                    f'Email: {user.email}'
                )
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error resetting password: {e}')
            )