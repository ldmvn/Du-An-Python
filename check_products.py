import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from store.models import Product

products = list(Product.objects.all().values('id', 'name')[:10])
for p in products:
    print(f"ID: {p['id']} - {p['name']}")

if not products:
    print("No products found")
else:
    print(f"Total: {Product.objects.count()}")
