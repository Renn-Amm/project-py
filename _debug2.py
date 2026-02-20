import os, sys, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.projects.models import Project

User = get_user_model()
user = User.objects.first()

print("User:", user.email if user else "NONE")
if not user:
    sys.exit(1)

c = Client()
c.force_login(user)

project = Project.objects.filter(organization=user.organization).first()
if project:
    url = f'/dashboard/projects/{project.id}/'
else:
    url = '/dashboard/projects/'

print("URL:", url)
response = c.get(url)
content = response.content.decode('utf-8')

# Find ALL {{ }} patterns
literals = re.findall(r'\{\{[^}]+\}\}', content)
print("Literal {{ }} count:", len(literals))
if literals:
    print("FIRST 5:", literals[:5])
else:
    print("NONE FOUND - template renders cleanly locally")

# Check specific patterns from user's report
for pattern in ['col.label', 'col.tasks', 'm.user.email', 'user.organization', 'user.role']:
    if pattern in content:
        print(f"FOUND LITERAL: {pattern}")
    else:
        print(f"OK (not literal): {pattern}")
