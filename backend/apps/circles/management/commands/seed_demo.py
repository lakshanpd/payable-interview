from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.circles.models import Circle
from apps.circles.services import CircleService
from apps.common.exceptions import ServiceError

User = get_user_model()

DEMO_PASSWORD = 'password123'
DEMO_USERNAMES = ['alice', 'bob', 'charlie', 'david']
DEMO_CIRCLE_NAME = 'Demo Circle'


class Command(BaseCommand):
    help = 'Create demo users (alice/bob/charlie/david, password "password123") and a 4-member demo circle, for trying out the app without registering by hand. Safe to run more than once.'

    def handle(self, *args, **options):
        users = {}
        for username in DEMO_USERNAMES:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com'},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=['password'])
                self.stdout.write(f'Created user {username} <{user.email}>')
            users[username] = user

        alice = users['alice']
        circle = Circle.objects.filter(name=DEMO_CIRCLE_NAME, admin=alice).first()
        if circle is None:
            circle = CircleService.create_circle(alice, DEMO_CIRCLE_NAME, contribution_amount=5000)
            self.stdout.write(f'Created circle "{circle.name}" (invite code {circle.invite_code})')

        for username in DEMO_USERNAMES[1:]:
            try:
                CircleService.join_circle(users[username], circle.invite_code)
                self.stdout.write(f'{username} joined {circle.name}')
            except ServiceError:
                pass  # already a member from a previous run

        self.stdout.write(self.style.SUCCESS('\nLog in with any of these (password: password123):'))
        for username in DEMO_USERNAMES:
            self.stdout.write(f'  {users[username].email}')
        self.stdout.write(f'\nCircle: "{circle.name}"  invite code: {circle.invite_code}  circle id: {circle.id}')
