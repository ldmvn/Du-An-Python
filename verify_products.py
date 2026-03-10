import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import re

client = Client()

try:
    # Login as admin
    admin_user = User.objects.get(username='admin')
    client.login(username='admin', password='admin123')
    
    # Get dashboard
    response = client.get('/dashboard/')
    content = response.content.decode('utf-8')
    
    # Extract products from HTML
    product_names = re.findall(r'<strong>([^<]+)</strong><br>', content)
    product_prices = re.findall(r'<span class="admin-price">([^<]+)</span>', content)
    product_dates = re.findall(r'<td style="text-align: center; font-size: 12px; color: #6b7280;">\s*([^<]+)\s*</td>', content)
    
    print(f'✓ Dashboard loaded successfully')
    print(f'✓ Total products found: {len(product_names)}')
    print()
    print('Products in dashboard:')
    for i, name in enumerate(product_names[:8]):
        price = product_prices[i] if i < len(product_prices) else 'N/A'
        date = product_dates[i] if i < len(product_dates) else 'N/A'
        print(f'{i+1}. {name}: {price} (created {date})')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
