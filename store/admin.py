from django.contrib import admin
from .models import (
    Category,
    Product,
    ProductSpecification,
    Order,
    OrderItem,
    Review
)

# ================== PRODUCT ==================

class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name',)
    list_editable = ('price',)
    inlines = [ProductSpecificationInline]

# ================== CATEGORY ==================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# ================== ORDER ==================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    list_editable = ('status',)
    inlines = [OrderItemInline]

# ================== REVIEW ==================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username')

# ================== SPEC (OPTIONAL) ==================
admin.site.register(ProductSpecification)
