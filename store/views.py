from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
import requests

from .models import Product, ProductSpecification, UserProfile, Category, Order, OrderItem, Banner, Wishlist
from .forms import ProductForm, UserProfileForm, UserExtendedProfileForm, ChangePasswordForm, CategoryForm, UserManagementForm, CheckoutForm


# ================== UTILS ==================
def is_admin(user):
    return user.is_staff


def get_base_context(request):
    """Return common context vars needed by base.html"""
    cart = request.session.get('cart', {})
    wishlist = request.session.get('wishlist', [])
    orders = request.session.get('orders', [])
    
    user_display_name = 'Khách'
    if request.user.is_authenticated:
        user_display_name = request.user.username
    
    return {
        'cart_count': len(cart),
        'wishlist_count': len(wishlist),
        'order_count': len(orders),
        'user_display_name': user_display_name,
    }


# ================== LOGIN ==================
def login_view(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')

        # Support login bằng username hoặc email
        user = None
        try:
            # Thử authenticate qua username trước
            user = authenticate(request, username=username_or_email, password=password)
            if not user:
                # Nếu không thành công, tìm user bằng email và authenticate
                try:
                    user_by_email = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_by_email.username, password=password)
                except User.DoesNotExist:
                    pass
        except:
            pass

        if user:
            login(request, user)
            return redirect('store:home')
        else:
            messages.error(request, '❌ Sai tên đăng nhập/email hoặc mật khẩu')
            return redirect('store:login')

    context = get_base_context(request)
    context['auth_type'] = 'login'
    return render(request, 'store/auth.html', context)


# ================== REGISTER ==================
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email') or username  # Dùng username làm email nếu không có
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if not username or not password1 or not password2:
            messages.error(request, '❌ Vui lòng nhập đầy đủ thông tin')
            return redirect('store:register')

        if password1 != password2:
            messages.error(request, '❌ Mật khẩu không khớp')
            return redirect('store:register')

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Tên đăng nhập đã tồn tại')
            return redirect('store:register')

        if email and User.objects.filter(email=email).exists():
            messages.error(request, '❌ Email đã tồn tại')
            return redirect('store:register')

        # Tạo user với username và email
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password1
        )
        messages.success(request, '✅ Đăng ký thành công! Vui lòng đăng nhập')
        return redirect('store:login')

    context = get_base_context(request)
    context['auth_type'] = 'register'
    return render(request, 'store/auth.html', context)


# ================== HOME ==================
@login_required(login_url='store:login')
def home(request):
    q = request.GET.get('q')
    brand = request.GET.get('brand', '').strip()
    price_range = request.GET.get('price_range', '')
    sort_by = request.GET.get('sort_by', '')
    
    products = Product.objects.all()

    if q:
        products = products.filter(name__icontains=q)

    # Filter by brand (category) if provided
    if brand:
        products = products.filter(category__name__iexact=brand)

    # Filter by price range
    if price_range:
        if price_range == 'under_5m':
            products = products.filter(price__lt=5000000)
        elif price_range == '5m_10m':
            products = products.filter(price__gte=5000000, price__lt=10000000)
        elif price_range == '10m_20m':
            products = products.filter(price__gte=10000000, price__lt=20000000)
        elif price_range == 'over_20m':
            products = products.filter(price__gte=20000000)
    
    # Sort products
    if sort_by:
        if sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        elif sort_by == 'newest':
            products = products.order_by('-created_at')
        elif sort_by == 'rating':
            products = products.order_by('-id')  # Placeholder - you might want actual rating sorting

    # Get wishlist products
    wishlist_ids = request.session.get('wishlist', [])
    wishlist_products = Product.objects.filter(id__in=wishlist_ids)

    # pull all categories (used as "brands"/manufacturers on the homepage)
    categories = Category.objects.all()

    context = get_base_context(request)
    context.update({
        'products': products,
        'categories': categories,
        'selected_brand': brand,
        'search_query': q,
        'price_range': price_range,
        'sort_by': sort_by,
        'wishlist_products': wishlist_products,
    })
    return render(request, 'store/home.html', context)


# ================== PRODUCT DETAIL ==================
@login_required(login_url='store:login')
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    
    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]
    
    # Color options for display
    colors = [
        ('Hồng', '#ffb6c1'),
        ('Đen', '#1f2937'),
        ('Xanh dương', '#3b82f6'),
        ('Vàng', '#fbbf24'),
        ('Xanh lá', '#10b981'),
    ]
    
    # RAM options with price increments
    # Base price is the product's discounted price
    base_price = product.get_discounted_price()
    ram_options = [
        {'capacity': '128GB', 'price': base_price},
        {'capacity': '256GB', 'price': base_price + 500000},
        {'capacity': '512GB', 'price': base_price + 1000000},
    ]
    
    context = get_base_context(request)
    context.update({
        'product': product,
        'related_products': related_products,
        'colors': colors,
        'ram_options': ram_options,
        'base_price': base_price,
    })
    return render(request, 'store/product_detail.html', context)


# ================== PRODUCT SEARCH ==================
@login_required(login_url='store:login')
def product_search(request):
    q = request.GET.get('q', '')
    brand = request.GET.get('brand', '').strip()
    
    products = Product.objects.all()
    
    if q:
        products = products.filter(name__icontains=q)

    # if a brand (category name) was specified, filter accordingly
    if brand:
        products = products.filter(category__name__iexact=brand)

    context = get_base_context(request)
    context.update({
        'products': products,
        'search_query': q,
        'brand': brand,
    })
    return render(request, 'store/search.html', context)


# ================== CART ==================
@login_required(login_url='store:login')
def add_to_cart(request, product_id):
    product_id = str(product_id)
    
    try:
        product = Product.objects.get(id=int(product_id))
        cart = request.session.get('cart', {})
        
        if product_id in cart:
            # Item already in cart - increase quantity
            if isinstance(cart[product_id], dict):
                # New format
                cart[product_id]['quantity'] += 1
            else:
                # Old format - convert to new format and add
                old_qty = cart[product_id]
                cart[product_id] = {
                    'name': product.name,
                    'price': product.get_discounted_price(),
                    'quantity': old_qty + 1,
                    'image': product.image.url if product.image else ''
                }
        else:
            # New item - add with new format
            cart[product_id] = {
                'name': product.name,
                'price': product.get_discounted_price(),
                'quantity': 1,
                'image': product.image.url if product.image else ''
            }
        
        request.session['cart'] = cart
        messages.success(request, '🛒 Đã thêm vào giỏ hàng')
    except Product.DoesNotExist:
        messages.error(request, '❌ Sản phẩm không tồn tại')
    
    return redirect('store:home')


@login_required(login_url='store:login')
def cart_view(request):
    cart = request.session.get('cart', {})
    products = []
    total = 0

    for product_id, cart_item in cart.items():
        try:
            product = Product.objects.get(id=int(product_id))
            
            # Handle both old format (int) and new format (dict)
            if isinstance(cart_item, dict):
                # New format from AJAX: {'name': str, 'price': int, 'quantity': int, 'image': str}
                product.quantity = cart_item.get('quantity', 1)
                product.price = cart_item.get('price', product.get_discounted_price())
            else:
                # Old format: just an integer quantity
                product.quantity = cart_item
                product.price = product.get_discounted_price()
            
            product.subtotal = product.price * product.quantity
            total += product.subtotal
            products.append(product)
        except (Product.DoesNotExist, ValueError):
            pass

    context = get_base_context(request)
    context.update({
        'products': products,
        'total': total
    })
    return render(request, 'store/cart.html', context)


@login_required(login_url='store:login')
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session['cart'] = cart
    return redirect('store:cart_detail')


@login_required(login_url='store:login')
def update_cart_quantity(request, product_id):
    """Update quantity of a product in cart via AJAX"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id = str(product_id)
        
        try:
            new_quantity = int(request.POST.get('quantity', 1))
            if new_quantity < 1:
                new_quantity = 1
            elif new_quantity > 99:
                new_quantity = 99
                
            if product_id in cart:
                cart[product_id] = new_quantity
                request.session['cart'] = cart
                
                # Calculate new subtotal
                product = Product.objects.get(id=int(product_id))
                subtotal = product.price * new_quantity
                
                return JsonResponse({
                    'success': True,
                    'quantity': new_quantity,
                    'price': product.price,
                    'subtotal': subtotal,
                    'subtotal_formatted': f"{subtotal:,.0f}₫"
                })
            else:
                return JsonResponse({'success': False, 'error': 'Sản phẩm không có trong giỏ hàng'})
                
        except (ValueError, Product.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại'})
    
    return JsonResponse({'success': False, 'error': 'Phương thức không hợp lệ'})


@login_required(login_url='store:login')
def clear_cart(request):
    """Clear all items from cart"""
    request.session['cart'] = {}
    messages.success(request, '🗑️ Đã xóa toàn bộ giỏ hàng')
    return redirect('store:cart_detail')


# ================== CHECKOUT ==================
@login_required(login_url='store:login')
def checkout(request):
    product_id = request.GET.get('product_id') or request.POST.get('product_id')
    quantity = request.GET.get('quantity', '1') or request.POST.get('quantity', '1')
    
    if not product_id:
        messages.error(request, '❌ Sản phẩm không tồn tại')
        return redirect('store:home')
    
    try:
        product = Product.objects.get(id=int(product_id))
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
    except (Product.DoesNotExist, ValueError):
        messages.error(request, '❌ Sản phẩm không tồn tại')
        return redirect('store:home')
    
    if request.method == 'POST':
        # Process checkout form using CheckoutForm
        form = CheckoutForm(request.POST)
        
        if form.is_valid():
            fullname = form.cleaned_data['fullname']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            address = form.cleaned_data['address']
            city = form.cleaned_data['city']
            district = form.cleaned_data['district']
            ward = form.cleaned_data['ward']
            payment_method = form.cleaned_data['payment_method']
            
            # Combine address with district and ward for full address
            full_address = f"{address}, {ward}, {district}, {city}"
            
            try:
                # Create Order
                from datetime import datetime
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                total_amount = product.get_discounted_price() * quantity
                
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    total_amount=total_amount,
                    status='pending',
                    payment_method=payment_method
                )
                
                # Create OrderItem
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.get_discounted_price()
                )
                
                # Get or create user profile
                user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                
                # Update user profile with shipping info
                user_profile.phone = phone
                user_profile.address = full_address  # Save full address including district/ward
                user_profile.save()
                
                # Update user's name/email
                parts = fullname.split(' ', 1)
                request.user.first_name = parts[0] if len(parts) > 0 else ''
                request.user.last_name = parts[1] if len(parts) > 1 else ''
                request.user.email = email
                request.user.save()
                
                messages.success(request, f'✅ Đặt hàng thành công! Mã đơn hàng: {order_number}')
                return redirect('store:order_success')
            
            except Exception as e:
                messages.error(request, f'❌ Lỗi: {str(e)}. Vui lòng thử lại!')
                context = get_base_context(request)
                context.update({
                    'product': product,
                    'quantity': quantity,
                    'total_price': product.get_discounted_price() * quantity,
                    'form': form,
                })
                return render(request, 'store/checkout.html', context)
        else:
            # Form validation failed - display errors
            context = get_base_context(request)
            context.update({
                'product': product,
                'quantity': quantity,
                'total_price': product.get_discounted_price() * quantity,
                'form': form,
            })
            return render(request, 'store/checkout.html', context)
    else:
        # GET request - initialize form with pre-filled data
        initial_data = {
            'email': request.user.email if request.user.is_authenticated else '',
        }
        form = CheckoutForm(initial=initial_data)
    
    context = get_base_context(request)
    context.update({
        'product': product,
        'quantity': quantity,
        'total_price': product.get_discounted_price() * quantity,
        'form': form,
    })
    return render(request, 'store/checkout.html', context)



@login_required(login_url='store:login')
def checkout_from_cart(request):
    """Checkout process for cart items"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.error(request, '❌ Giỏ hàng của bạn trống')
        return redirect('store:cart_detail')
    
    # Get cart items
    cart_items = []
    total_amount = 0
    
    for product_id, cart_item in cart.items():
        try:
            product = Product.objects.get(id=int(product_id))
            
            # Handle both old format (int) and new format (dict)
            if isinstance(cart_item, dict):
                # New format from AJAX: {'name': str, 'price': int, 'quantity': int, 'image': str}
                quantity = cart_item.get('quantity', 1)
                price = cart_item.get('price', product.get_discounted_price())
            else:
                # Old format: just an integer quantity
                quantity = cart_item
                price = product.get_discounted_price()
            
            item_total = price * quantity
            total_amount += item_total
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'price': price,
                'total': item_total
            })
        except Product.DoesNotExist:
            # Remove invalid product from cart
            del cart[product_id]
            request.session['cart'] = cart
    
    if not cart_items:
        messages.error(request, '❌ Không có sản phẩm hợp lệ trong giỏ hàng')
        return redirect('store:cart_detail')
    
    if request.method == 'POST':
        # Process checkout form using CheckoutForm
        form = CheckoutForm(request.POST)
        
        if form.is_valid():
            fullname = form.cleaned_data['fullname']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            address = form.cleaned_data['address']
            city = form.cleaned_data['city']
            district = form.cleaned_data['district']
            ward = form.cleaned_data['ward']
            payment_method = form.cleaned_data['payment_method']
            
            # Combine address with district and ward for full address
            full_address = f"{address}, {ward}, {district}, {city}"
            
            try:
                # Create Order
                from datetime import datetime
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    total_amount=total_amount,
                    status='pending',
                    payment_method=payment_method
                )
                
                # Create OrderItems for all cart items
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        quantity=item['quantity'],
                        price=item['price']
                    )
                
                # Clear cart after successful order
                request.session['cart'] = {}
                
                # Get or create user profile
                user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                
                # Update user profile with shipping info
                user_profile.phone = phone
                user_profile.address = full_address  # Save full address including district/ward
                user_profile.save()
                
                # Update user's name/email
                parts = fullname.split(' ', 1)
                request.user.first_name = parts[0] if len(parts) > 0 else ''
                request.user.last_name = parts[1] if len(parts) > 1 else ''
                request.user.email = email
                request.user.save()
                
                messages.success(request, f'✅ Đặt hàng thành công! Mã đơn hàng: {order_number}')
                return redirect('store:order_success')
            
            except Exception as e:
                messages.error(request, f'❌ Lỗi: {str(e)}. Vui lòng thử lại!')
                context = get_base_context(request)
                context.update({
                    'cart_items': cart_items,
                    'total_amount': total_amount,
                    'form': form,
                })
                return render(request, 'store/checkout.html', context)
        else:
            # Form validation failed - display errors
            context = get_base_context(request)
            context.update({
                'cart_items': cart_items,
                'total_amount': total_amount,
                'form': form,
            })
            return render(request, 'store/checkout.html', context)
    else:
        # GET request - initialize form with pre-filled data
        initial_data = {
            'email': request.user.email if request.user.is_authenticated else '',
        }
        form = CheckoutForm(initial=initial_data)
    
    context = get_base_context(request)
    context.update({
        'cart_items': cart_items,
        'total_amount': total_amount,
        'form': form,
    })
    return render(request, 'store/checkout.html', context)


# ================== WISHLIST ==================
@login_required(login_url='store:login')
def wishlist(request):
    wishlist = request.session.get('wishlist', [])
    products = Product.objects.filter(id__in=wishlist)
    
    context = get_base_context(request)
    context['products'] = products
    return render(request, 'store/wishlist.html', context)


@login_required(login_url='store:login')
def wishlist_toggle(request):
    product_id = request.GET.get('product_id')
    wishlist = request.session.get('wishlist', [])
    
    if product_id:
        product_id = int(product_id)
        if product_id in wishlist:
            wishlist.remove(product_id)
            status = 'removed'
        else:
            wishlist.append(product_id)
            status = 'added'
        
        request.session['wishlist'] = wishlist
        return JsonResponse({'status': status, 'wishlist_count': len(wishlist)})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ================== COMPARE ==================
@login_required(login_url='store:login')
def compare_view(request):
    compare_list = request.session.get('compare', [])
    products = Product.objects.filter(id__in=compare_list)
    
    context = get_base_context(request)
    context['products'] = products
    return render(request, 'store/compare.html', context)


# ================== USER PROFILE ==================
@login_required(login_url='store:login')
def profile(request):
    user = request.user
    # Get or create UserProfile
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        
        if action == 'update_profile':
            # Update user info
            user_form = UserProfileForm(request.POST, instance=user)
            profile_form = UserExtendedProfileForm(request.POST, instance=user_profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, '✅ Cập nhật thông tin thành công')
                return redirect('store:profile')
        
        elif action == 'change_password':
            # Change password
            password_form = ChangePasswordForm(request.POST)
            
            if password_form.is_valid():
                old_password = password_form.cleaned_data['old_password']
                new_password1 = password_form.cleaned_data['new_password1']
                new_password2 = password_form.cleaned_data['new_password2']
                
                # Check old password
                if not user.check_password(old_password):
                    messages.error(request, '❌ Mật khẩu hiện tại không đúng')
                    return redirect('store:profile')
                
                # Check if new passwords match
                if new_password1 != new_password2:
                    messages.error(request, '❌ Mật khẩu mới không khớp')
                    return redirect('store:profile')
                
                # Change password
                user.set_password(new_password1)
                user.save()
                
                # Re-login to prevent logout
                login(request, user)
                messages.success(request, '✅ Đổi mật khẩu thành công')
                return redirect('store:profile')
    
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = UserExtendedProfileForm(instance=user_profile)
        password_form = ChangePasswordForm()
    
    context = get_base_context(request)
    context.update({
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
    })
    context['auth_type'] = 'profile'
    return render(request, 'store/profile.html', context)


@login_required(login_url='store:login')
def order_tracking(request):
    # Lấy tất cả orders của user, sắp xếp theo thời gian gần nhất
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = get_base_context(request)
    context['orders'] = orders
    return render(request, 'store/orders.html', context)


@login_required(login_url='store:login')
def cancel_order(request, order_id):
    """Hủy đơn hàng (chỉ khi status = pending)"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status == 'pending':
        order.status = 'cancelled'
        order.save()
        messages.success(request, '✅ Đơn hàng đã được hủy')
    else:
        messages.error(request, f'❌ Không thể hủy đơn hàng với trạng thái: {order.get_status_display()}')
    
    return redirect('store:order_tracking')


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def delete_order(request, order_id):
    """Delete order (admin only)"""
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    messages.success(request, '✅ Đơn hàng đã xóa thành công')
    return redirect('store:admin_orders')


@login_required(login_url='store:login')
def order_success(request):
    # Lấy đơn hàng cuối cùng của user
    order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    
    context = get_base_context(request)
    context['order'] = order
    return render(request, 'store/order_success.html', context)


@login_required(login_url='store:login')
def order_detail(request, order_id):
    """View order details - for both users and admin"""
    # Admin can see any order, regular users can only see their own
    if request.user.is_staff:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = get_base_context(request)
    context['order'] = order
    context['order_items'] = order.items.all()
    return render(request, 'store/order_detail.html', context)


# ================== ADMIN DASHBOARD ==================
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def dashboard(request):
    from django.core.paginator import Paginator
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    # Get all data
    all_products = Product.objects.all().order_by('-created_at')
    users = User.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all().order_by('-created_at')
    
    # Today's date
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Filter orders by date
    today_orders = orders.filter(created_at__date=today)
    month_orders = orders.filter(created_at__date__gte=month_start)
    year_orders = orders.filter(created_at__year=today.year)
    
    # Calculate statistics
    total_products = all_products.count()
    total_users = users.count()
    total_categories = categories.count()
    total_orders = orders.count()
    total_revenue = sum(order.total_amount for order in orders) if orders else 0
    
    # Today revenue
    today_revenue = sum(order.total_amount for order in today_orders) if today_orders else 0
    
    # Average Order Value (AOV)
    if orders.exists():
        aov = total_revenue / total_orders
    else:
        aov = 0
    
    # Conversion Rate (dummy calculation, you can adjust)
    # This would need visitor data from analytics
    conversion_rate = 1.67
    
    # Monthly revenue calculation
    monthly_revenue = []
    for month in range(1, 13):
        month_start_date = today.replace(month=month, day=1)
        if month == 12:
            month_end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end_date = today.replace(month=month + 1, day=1)
        
        month_rev = sum(
            order.total_amount for order in orders 
            if month_start_date <= order.created_at.date() < month_end_date
        ) if orders else 0
        monthly_revenue.append(int(month_rev))
    
    # Pagination for products
    paginator = Paginator(all_products, 15)
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)
    
    # Get recent orders and products
    recent_orders = orders[:10]
    recent_products = all_products[:10]
    
    context = get_base_context(request)
    context.update({
        'products': products,
        'total_products': total_products,
        'total_users': total_users,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'total_revenue': f"{int(total_revenue):,}",
        'today_orders': today_orders.count(),
        'month_orders': month_orders.count(),
        'year_orders': year_orders.count(),
        'today_revenue': f"{int(today_revenue):,}",
        'aov': f"{int(aov):,}",
        'conversion_rate': f"{conversion_rate:.2f}",
        'recent_orders': recent_orders,
        'recent_products': recent_products,
        'monthly_revenue': monthly_revenue,
    })
    return render(request, 'admin/admin_dashboard.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Thêm sản phẩm thành công')
            return redirect('store:admin_products')
    else:
        form = ProductForm()

    context = get_base_context(request)
    context['form'] = form
    context['title'] = 'Thêm sản phẩm mới'
    return render(request, 'store/product_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def dashboard_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    specs = product.specs.all() if hasattr(product, 'specs') else []

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cập nhật sản phẩm thành công')
            return redirect('store:admin_products')
    else:
        form = ProductForm(instance=product)

    context = get_base_context(request)
    context.update({
        'form': form,
        'product': product,
        'specs': specs,
        'title': f'Chỉnh sửa sản phẩm: {product.name}'
    })
    return render(request, 'store/product_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, '🗑️ Đã xoá sản phẩm')
    return redirect('store:admin_products')


# ================== CATEGORY MANAGEMENT ==================
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def category_list(request):
    """List all categories/brands"""
    categories = Category.objects.all().order_by('name')
    context = get_base_context(request)
    context['categories'] = categories
    return render(request, 'store/category_list.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def category_create(request):
    """Create a new category/brand"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Thêm nhà sản xuất thành công')
            return redirect('store:category_list')
    else:
        form = CategoryForm()

    context = get_base_context(request)
    context['form'] = form
    context['title'] = 'Thêm nhà sản xuất mới'
    return render(request, 'store/category_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def category_edit(request, pk):
    """Edit an existing category/brand"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cập nhật nhà sản xuất thành công')
            return redirect('store:category_list')
    else:
        form = CategoryForm(instance=category)

    context = get_base_context(request)
    context['form'] = form
    context['category'] = category
    context['title'] = 'Chỉnh sửa nhà sản xuất'
    return render(request, 'store/category_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def category_delete(request, pk):
    """Delete a category/brand"""
    category = get_object_or_404(Category, pk=pk)
    
    # Check if category has products
    product_count = category.products.count()
    if product_count > 0:
        messages.error(request, f'❌ Không thể xoá. Nhà sản xuất này có {product_count} sản phẩm')
        return redirect('store:category_list')
    
    category.delete()
    messages.success(request, '🗑️ Đã xoá nhà sản xuất')
    return redirect('store:category_list')


# ================== USER MANAGEMENT ==================
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def user_list(request):
    """List all users"""
    users = User.objects.all().order_by('-date_joined')
    context = get_base_context(request)
    context['users'] = users
    return render(request, 'admin/admin_users.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def user_edit(request, pk):
    """Edit user account"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cập nhật thành viên thành công')
            return redirect('store:user_list')
    else:
        form = UserManagementForm(instance=user)

    context = get_base_context(request)
    context['form'] = form
    context['edit_user'] = user
    return render(request, 'admin/admin_user_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def user_delete(request, pk):
    """Delete a user account"""
    user = get_object_or_404(User, pk=pk)
    
    # Prevent deleting self
    if user.id == request.user.id:
        if request.method == 'POST':
            return JsonResponse({'error': 'Bạn không thể xoá tài khoản của chính mình'}, status=400)
        messages.error(request, '❌ Bạn không thể xoá tài khoản của chính mình')
        return redirect('store:user_list')
    
    # Handle POST request for deletion
    if request.method == 'POST':
        username = user.username
        user.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Đã xoá thành viên {username}'})
        messages.success(request, f'🗑️ Đã xoá thành viên {username}')
        return redirect('store:user_list')
    
    # GET request - redirect for safety
    messages.warning(request, '❌ Phương thức yêu cầu không hợp lệ')
    return redirect('store:user_list')


# ================== LOGOUT ==================
def logout_view(request):
    logout(request)
    return redirect('store:login')


# ================== BANNER MANAGEMENT ==================
def banner_list(request):
    """Get all active banners as JSON for homepage slider"""
    banners = Banner.objects.filter(is_active=True).order_by('banner_id')
    data = {
        'success': True,
        'banners': [
            {
                'banner_id': b.banner_id,
                'image_url': b.image.url if b.image else '',
                'title': b.title,
                'description': b.description,
            }
            for b in banners
        ]
    }
    return JsonResponse(data)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_admin_list(request):
    """Admin list all banners"""
    banners = Banner.objects.all().order_by('banner_id')
    context = get_base_context(request)
    context['banners'] = banners
    return render(request, 'store/banner_list.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_add(request):
    """Add a new banner"""
    if request.method == 'POST':
        from .forms import BannerForm
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': '✅ Thêm banner thành công'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_replace(request):
    """Replace/update existing banner"""
    if request.method == 'POST':
        banner_id = request.POST.get('banner_id')
        
        try:
            banner = Banner.objects.get(banner_id=banner_id)
            
            if 'image' in request.FILES:
                # Delete old image
                if banner.image:
                    banner.image.delete()
                banner.image = request.FILES['image']
            
            if 'title' in request.POST:
                banner.title = request.POST.get('title', '')
            if 'description' in request.POST:
                banner.description = request.POST.get('description', '')
            
            banner.save()
            return JsonResponse({'success': True, 'message': '✅ Cập nhật banner thành công'})
        except Banner.DoesNotExist:
            return JsonResponse({'success': False, 'message': '❌ Không tìm thấy banner'}, status=404)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_delete(request):
    """Delete a banner"""
    if request.method == 'POST':
        banner_id = request.POST.get('banner_id')
        
        try:
            banner = Banner.objects.get(banner_id=banner_id)
            if banner.image:
                banner.image.delete()
            banner.delete()
            return JsonResponse({'success': True, 'message': '✅ Xoá banner thành công'})
        except Banner.DoesNotExist:
            return JsonResponse({'success': False, 'message': '❌ Không tìm thấy banner'}, status=404)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# ================== API VIEWS ==================
def get_provinces(request):
    """API endpoint to fetch Vietnamese provinces from external API"""
    try:
        # Fetch provinces from Vietnamese provinces API
        response = requests.get('https://provinces.open-api.vn/api/p/', timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        provinces_data = response.json()
        
        # Transform data to format suitable for frontend
        provinces = []
        for province in provinces_data:
            provinces.append({
                'code': province.get('code'),
                'name': province.get('name'),
                'division_type': province.get('division_type'),
                'codename': province.get('codename'),
                'phone_code': province.get('phone_code')
            })
        
        return JsonResponse({
            'success': True,
            'provinces': provinces
        })
        
    except requests.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': f'Không thể kết nối đến API tỉnh thành: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Lỗi xử lý dữ liệu: {str(e)}'
        }, status=500)


def get_districts(request, province_code):
    """API endpoint to fetch districts by province code"""
    try:
        # Fetch districts from Vietnamese provinces API
        url = f'https://provinces.open-api.vn/api/p/{province_code}?depth=2'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        province_data = response.json()
        
        # Extract districts from the response
        districts = []
        if 'districts' in province_data:
            for district in province_data['districts']:
                districts.append({
                    'code': district.get('code'),
                    'name': district.get('name'),
                    'division_type': district.get('division_type'),
                    'codename': district.get('codename'),
                    'province_code': province_code
                })
        
        return JsonResponse({
            'success': True,
            'districts': districts
        })
        
    except requests.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': f'Không thể kết nối đến API quận/huyện: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Lỗi xử lý dữ liệu: {str(e)}'
        }, status=500)


def get_wards(request, district_code):
    """API endpoint to fetch wards by district code"""
    try:
        # Fetch wards from Vietnamese provinces API
        url = f'https://provinces.open-api.vn/api/d/{district_code}?depth=2'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        district_data = response.json()
        
        # Extract wards from the response
        wards = []
        if 'wards' in district_data:
            for ward in district_data['wards']:
                wards.append({
                    'code': ward.get('code'),
                    'name': ward.get('name'),
                    'division_type': ward.get('division_type'),
                    'codename': ward.get('codename'),
                    'district_code': district_code
                })
        
        return JsonResponse({
            'success': True,
            'wards': wards
        })
        
    except requests.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': f'Không thể kết nối đến API phường/xã: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Lỗi xử lý dữ liệu: {str(e)}'
        }, status=500)


# ================== AJAX ENDPOINTS - WISHLIST ==================
@login_required(login_url='store:login')
def toggle_wishlist_ajax(request):
    """AJAX endpoint to toggle product in wishlist"""
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            
            # Get or create wishlist
            wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
            
            # Toggle product
            is_added = wishlist.toggle_product(product)
            
            return JsonResponse({
                'success': True,
                'is_added': is_added,
                'message': '✅ Thêm vào wishlist' if is_added else '❌ Xóa khỏi wishlist',
                'wishlist_count': wishlist.products.count()
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


# ================== AJAX ENDPOINTS - CART ==================
def add_to_cart_ajax(request):
    """AJAX endpoint to add product to cart"""
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            
            product = get_object_or_404(Product, id=product_id)
            
            # Check stock
            if product.stock <= 0:
                return JsonResponse({'success': False, 'error': 'Sản phẩm hết hàng'}, status=400)
            
            # Initialize cart in session
            cart = request.session.get('cart', {})
            
            product_key = str(product_id)
            if product_key in cart:
                cart[product_key]['quantity'] += quantity
            else:
                cart[product_key] = {
                    'name': product.name,
                    'price': product.get_discounted_price(),
                    'quantity': quantity,
                    'image': product.image.url if product.image else ''
                }
            
            request.session['cart'] = cart
            
            return JsonResponse({
                'success': True,
                'message': f'✅ Thêm {quantity} sản phẩm vào giỏ hàng',
                'cart_count': sum(item['quantity'] for item in cart.values()),
                'cart_total': sum(item['price'] * item['quantity'] for item in cart.values())
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại'}, status=404)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Số lượng không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


def update_cart_quantity_ajax(request):
    """AJAX endpoint to update cart item quantity"""
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            
            cart = request.session.get('cart', {})
            product_key = str(product_id)
            
            if product_key not in cart:
                return JsonResponse({'success': False, 'error': 'Sản phẩm không trong giỏ'}, status=404)
            
            if quantity <= 0:
                del cart[product_key]
            else:
                cart[product_key]['quantity'] = quantity
            
            request.session['cart'] = cart
            
            return JsonResponse({
                'success': True,
                'message': 'Cập nhật giỏ hàng thành công',
                'cart_count': sum(item['quantity'] for item in cart.values()),
                'cart_total': sum(item['price'] * item['quantity'] for item in cart.values()),
                'item_total': cart[product_key]['price'] * quantity if product_key in cart else 0
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Số lượng không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


def remove_from_cart_ajax(request):
    """AJAX endpoint to remove product from cart"""
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            
            cart = request.session.get('cart', {})
            product_key = str(product_id)
            
            if product_key in cart:
                del cart[product_key]
                request.session['cart'] = cart
                
            return JsonResponse({
                'success': True,
                'message': '✅ Xóa khỏi giỏ hàng',
                'cart_count': sum(item['quantity'] for item in cart.values()),
                'cart_total': sum(item['price'] * item['quantity'] for item in cart.values())
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


# ================== ADMIN PRODUCTS & ORDERS ==================
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_products(request):
    """Admin products management page"""
    from django.core.paginator import Paginator
    
    products = Product.objects.all().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page', 1)
    products_page = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    context = get_base_context(request)
    context.update({
        'products': products_page,
        'categories': categories,
    })
    return render(request, 'admin/admin_products.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_orders(request):
    """Admin orders management page"""
    from django.core.paginator import Paginator
    
    # Get all orders
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    
    orders = Order.objects.all().order_by('-created_at')
    
    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        )
    
    if status_filter and status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page', 1)
    orders_page = paginator.get_page(page_number)
    
    context = get_base_context(request)
    context.update({
        'orders': orders_page,
    })
    return render(request, 'admin/admin_orders.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def update_order_status(request):
    """AJAX endpoint to update order status"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            order_id = data.get('order_id')
            new_status = data.get('status')
            
            order = get_object_or_404(Order, id=order_id)
            
            valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
            if new_status not in valid_statuses:
                return JsonResponse({'success': False, 'error': 'Trạng thái không hợp lệ'})
            
            old_status = order.status
            order.status = new_status
            order.save()
            
            return JsonResponse({
                'success': True,
                'message': f'✅ Cập nhật trạng thái từ {old_status} sang {new_status}',
                'new_status': new_status
            })
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Đơn hàng không tồn tại'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Phương thức không hợp lệ'}, status=400)


# ================== PLACEHOLDER VIEW ==================
def placeholder(request):
    """Placeholder view để tránh 404 errors"""
    if request.method == 'GET':
        return JsonResponse({'status': 'ok', 'message': 'Endpoint này sẽ được phát triển'})
    
    return JsonResponse({'status': 'ok', 'message': 'Request thành công'})
