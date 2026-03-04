from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse

from .models import Product, ProductSpecification, UserProfile
from .forms import ProductForm, UserProfileForm, UserExtendedProfileForm, ChangePasswordForm


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
    return render(request, 'store/login.html', context)


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
    return render(request, 'store/register.html', context)


# ================== HOME ==================
@login_required(login_url='store:login')
def home(request):
    q = request.GET.get('q')
    products = Product.objects.all()

    if q:
        products = products.filter(name__icontains=q)

    context = get_base_context(request)
    context.update({
        'products': products
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
    
    context = get_base_context(request)
    context.update({
        'product': product,
        'related_products': related_products
    })
    return render(request, 'store/product_detail.html', context)


# ================== PRODUCT SEARCH ==================
@login_required(login_url='store:login')
def product_search(request):
    q = request.GET.get('q', '')
    brand = request.GET.get('brand', '')
    
    products = Product.objects.all()
    
    if q:
        products = products.filter(name__icontains=q)
    
    context = get_base_context(request)
    context.update({
        'products': products,
        'search_query': q
    })
    return render(request, 'store/search.html', context)


# ================== CART ==================
@login_required(login_url='store:login')
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart

    messages.success(request, '🛒 Đã thêm vào giỏ hàng')
    return redirect('store:home')


@login_required(login_url='store:login')
def cart_view(request):
    cart = request.session.get('cart', {})
    products = []
    total = 0

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=int(product_id))
            product.quantity = quantity
            product.subtotal = product.price * quantity
            total += product.subtotal
            products.append(product)
        except Product.DoesNotExist:
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
        # Process checkout form
        fullname = request.POST.get('fullname', '')
        email = request.POST.get('email', request.user.email)
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        payment_method = request.POST.get('payment_method', 'cash')
        
        if not fullname or not phone or not address or not city:
            messages.error(request, '❌ Vui lòng nhập đầy đủ thông tin')
            context = get_base_context(request)
            context.update({
                'product': product,
                'quantity': quantity,
                'total_price': product.get_discounted_price() * quantity,
            })
            return render(request, 'store/checkout.html', context)
        
        # Create Order
        from datetime import datetime
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        total_amount = product.get_discounted_price() * quantity
        
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            total_amount=total_amount,
            status='pending'
        )
        
        # Create OrderItem
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.get_discounted_price()
        )
        
        # Update user profile with shipping info
        request.user.profile.phone = phone
        request.user.profile.address = address
        request.user.profile.save()
        
        # Update user's name/email
        parts = fullname.split(' ', 1)
        request.user.first_name = parts[0] if len(parts) > 0 else ''
        request.user.last_name = parts[1] if len(parts) > 1 else ''
        request.user.email = email
        request.user.save()
        
        messages.success(request, f'✅ Đặt hàng thành công! Mã đơn hàng: {order_number}')
        return redirect('store:order_success')
    
    context = get_base_context(request)
    context.update({
        'product': product,
        'quantity': quantity,
        'total_price': product.get_discounted_price() * quantity,
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
    return render(request, 'store/profile.html', context)


@login_required(login_url='store:login')
def order_tracking(request):
    context = get_base_context(request)
    return render(request, 'store/order_tracking.html', context)


@login_required(login_url='store:login')
def order_success(request):
    context = get_base_context(request)
    return render(request, 'store/order_success.html', context)


# ================== ADMIN DASHBOARD ==================
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def dashboard(request):
    products = Product.objects.all()
    context = get_base_context(request)
    context['products'] = products
    return render(request, 'store/dashboard.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Thêm sản phẩm thành công')
            return redirect('store:dashboard')
    else:
        form = ProductForm()

    context = get_base_context(request)
    context['form'] = form
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
            return redirect('store:dashboard')
    else:
        form = ProductForm(instance=product)

    context = get_base_context(request)
    context.update({
        'form': form,
        'product': product,
        'specs': specs
    })
    return render(request, 'store/product_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, '🗑️ Đã xoá sản phẩm')
    return redirect('store:dashboard')


# ================== LOGOUT ==================
def logout_view(request):
    logout(request)
    return redirect('store:login')


# ================== PLACEHOLDER VIEW ==================
def placeholder(request):
    """Placeholder view để tránh 404 errors"""
    if request.method == 'GET':
        return JsonResponse({'status': 'ok', 'message': 'Endpoint này sẽ được phát triển'})
    
    return JsonResponse({'status': 'ok', 'message': 'Request thành công'})
