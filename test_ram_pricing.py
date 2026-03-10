import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from store.models import Product
from django.template.loader import render_to_string

product = Product.objects.first()
if product:
    # Get related products
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]
    
    # RAM options
    base_price = product.get_discounted_price()
    ram_options = [
        {'capacity': '128GB', 'price': base_price},
        {'capacity': '256GB', 'price': base_price + 500000},
        {'capacity': '512GB', 'price': base_price + 1000000},
    ]
    
    try:
        result = render_to_string('store/product_detail.html', {
            'product': product,
            'related_products': related_products,
            'colors': [('Hồng', '#ffb6c1'), ('Đen', '#1f2937')],
            'ram_options': ram_options,
            'base_price': base_price,
        })
        print('✓ Template rendered successfully')
        print('✓ Contains updatePrice function:', 'function updatePrice' in result)
        print('✓ Contains data-price attributes:', 'data-price=' in result)
        print('✓ Contains current-price id:', 'id="current-price"' in result)
        print('✓ Contains RAM options:', '128GB' in result and '256GB' in result and '512GB' in result)
        
        # Extract a sample of the price section
        if 'updatePrice' in result:
            start = result.find('function updatePrice')
            end = result.find('</script>')
            if start > 0 and end > start:
                script_section = result[start:min(end, start+500)]
                print('\n✓ Script section (first 500 chars):')
                print(script_section[:200] + '...')
    except Exception as e:
        print(f'✗ Template error: {e}')
        import traceback
        traceback.print_exc()
else:
    print('✗ No products found')
