import os, sys, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Check project_detail.html for verbatim blocks or hidden characters
base = r'c:\Users\dell\Documents\HabourSpace\Software_Engineering\project\templates'

files_to_check = [
    r'dashboard\project_detail.html',
    r'partials\topbar.html',
    r'base.html',
]

for fname in files_to_check:
    path = os.path.join(base, fname)
    print(f"\n=== Checking {fname} ===")
    with open(path, 'rb') as f:
        raw = f.read()
    
    # Check for BOM
    if raw.startswith(b'\xef\xbb\xbf'):
        print("  WARNING: File has UTF-8 BOM!")
    
    # Check for verbatim blocks
    text = raw.decode('utf-8', errors='replace')
    if '{%' in text and 'verbatim' in text:
        print("  VERBATIM BLOCK FOUND!")
        idx = text.find('verbatim')
        print(f"  Context: {text[max(0,idx-50):idx+100]}")
    
    # Find ALL {{ }} occurrences and what's in them
    vars_found = re.findall(r'\{\{(.+?)\}\}', text)
    print(f"  Template vars ({len(vars_found)}):", vars_found[:10])
    
    # Check for non-standard curly braces
    non_ascii_braces = [(i, hex(ord(c))) for i, c in enumerate(text) if ord(c) > 127 and c in '{}']
    if non_ascii_braces:
        print(f"  NON-ASCII BRACES: {non_ascii_braces[:5]}")

# Also: test rendering the topbar snippet directly  
from django.template import engines
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.select_related('organization').first()

engine = engines['django']
snippet = '{{ user.role }} - {{ user.organization.name|default:"No Org" }}'
t = engine.from_string(snippet)
result = t.render({'user': user})
print(f"\nDirect snippet render: user.role={user.role!r}, org={getattr(user.organization, 'name', None)!r}")
print(f"Result: {result!r}")
