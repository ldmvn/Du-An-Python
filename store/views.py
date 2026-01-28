from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Product
from .forms import ProductForm

def is_admin(user):
    return user.is_staff

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
    return render(request, 'login.html')

@login_required
def home(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    products = Product.objects.all()
    return render(request, 'dashboard.html', {'products': products})

@login_required
@user_passes_test(is_admin)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('/dashboard/')
    return render(request, 'product_form.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if form.is_valid():
        form.save()
        return redirect('/dashboard/')
    return render(request, 'product_form.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('/dashboard/')

def logout_view(request):
    logout(request)
    return redirect('/login/')
