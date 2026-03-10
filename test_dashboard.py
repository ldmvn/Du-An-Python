import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

client = Client()

# Login as admin
try:
    admin_user = User.objects.get(username='admin')
    client.login(username='admin', password='admin123')
    
    # Get dashboard
    response = client.get('/dashboard/')
    print(f'Status: {response.status_code}')
    print(f'URL: {response.wsgi_request.path}')
    print(f'Context is None: {response.context is None}')
    print(f'Template: {response.templates}')
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        print(f'Content length: {len(content)}')
        
        if 'iPhone' in content:
            print('✓ Products are in HTML')
        else:
            print('✗ Products NOT in HTML')
        
        if 'Quản lý sản phẩm' in content:
            print('✓ Admin dashboard template rendered')
        
        # Print first 1000 chars to debug
        print('\n--- First 1000 chars of HTML ---')
        print(content[:1000])
        
        # Count product rows in table
        import re
        product_rows = len(re.findall(r'<tr>', content))
        print(f'\nTotal table rows: {product_rows}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
