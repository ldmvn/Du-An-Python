from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from .models import Product, ProductSpecification
from .forms import ProductForm


# ================== UTILS ==================
def is_admin(user):
    return user.is_staff


# ================== LOGIN ==================
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
        else:
            messages.error(request, '❌ Sai tên đăng nhập hoặc mật khẩu')
            return redirect('login')

    return render(request, 'login.html')


# ================== REGISTER ==================
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if not username or not password1 or not password2:
            messages.error(request, 'Vui lòng nhập đầy đủ thông tin')
            return redirect('register')

        if password1 != password2:
            messages.error(request, 'Mật khẩu không khớp')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username đã tồn tại')
            return redirect('register')

        User.objects.create_user(username=username, password=password1)
        messages.success(request, '🎉 Đăng ký thành công! Vui lòng đăng nhập')
        return redirect('login')

    return render(request, 'register.html')


# ================== HOME ==================
@login_required
def home(request):
    q = request.GET.get('q')
    products = Product.objects.all()

    if q:
        products = products.filter(name__icontains=q)

    return render(request, 'product_list.html', {
        'products': products
    })


# ================== PRODUCT DETAIL ==================
@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'product_detail.html', {
        'product': product
    })


# ================== CART ==================
@login_required
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart

    messages.success(request, '🛒 Đã thêm vào giỏ hàng')
    return redirect('/')


@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    products = []
    total = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        product.quantity = quantity
        product.subtotal = product.price * quantity
        total += product.subtotal
        products.append(product)

    return render(request, 'cart.html', {
        'products': products,
        'total': total
    })
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session['cart'] = cart
    return redirect('/cart/')


# ================== ADMIN DASHBOARD ==================
@login_required
@user_passes_test(is_admin)
def dashboard(request):
    products = Product.objects.all()
    return render(request, 'dashboard.html', {
        'products': products
    })


@login_required
@user_passes_test(is_admin)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Thêm sản phẩm thành công')
            return redirect('dashboard')
    else:
        form = ProductForm()

    return render(request, 'product_form.html', {
        'form': form
    })

@login_required
@user_passes_test(is_admin)
def dashboard_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    specs = product.specs.all()

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()

            # ❌ xoá specs cũ
            product.specs.all().delete()

            # ✅ thêm specs mới
            keys = request.POST.getlist('spec_key[]')
            values = request.POST.getlist('spec_value[]')

            for k, v in zip(keys, values):
                if k and v:
                    ProductSpecification.objects.create(
                        product=product,
                        key=k,
                        value=v
                    )

            return redirect('dashboard')

    else:
        form = ProductForm(instance=product)

    return render(request, 'product_form.html', {
        'form': form,
        'product': product,
        'specs': specs
    })


@login_required
@user_passes_test(is_admin)
def product_delete(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    messages.success(request, '🗑️ Đã xoá sản phẩm')
    return redirect('/dashboard/')


# ================== LOGOUT ==================
def logout_view(request):
    logout(request)
    return redirect('/login/')
