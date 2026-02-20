import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.template import Template, Context, RequestContext
from django.template.loader import get_template
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

# Try to get a real user from the DB
try:
    user = User.objects.first()
    print(f"Got user: {user}")
    print(f"  user.role: {user.role!r}")
    print(f"  user.organization: {getattr(user, 'organization', 'ATTR_MISSING')}")
    if user.organization:
        print(f"  user.organization.name: {user.organization.name!r}")
except Exception as e:
    print(f"DB error: {e}")
    user = None

# Render just the relevant snippet
snippet = """
{{ user.role }} | {{ user.organization.name|default:"No Org" }}
"""
factory = RequestFactory()
req = factory.get('/')
if user:
    req.user = user
    from django.template import engines
    engine = engines['django']
    t = engine.from_string(snippet)
    # Try with RequestContext
    from django.template import RequestContext
    ctx = RequestContext(req, {'user': user})
    result = t.render(ctx.flatten())
    print(f"\nRendered snippet: {result!r}")
else:
    print("No user found in DB.")

# Also check topbar source bytes around the critical lines
print("\n--- Topbar.html raw bytes (lines 57-62) ---")
topbar_path = r'templates\partials\topbar.html'
with open(topbar_path, 'rb') as f:
    content = f.read()
lines = content.split(b'\n')
for i, line in enumerate(lines[56:63], start=57):
    print(f"Line {i}: {line!r}")
