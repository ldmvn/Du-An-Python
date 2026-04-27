from django.contrib import admin
from django.template.response import TemplateResponse
from .models import (
    Category,
    Product,
    ProductColor,
    ProductMedia,
    ProductSpecification,
    Order,
    OrderItem,
    Review,
    Banner,
    Wishlist
)

# ================= CUSTOM ADMIN SITE OVERRIDE =================

# Store original index method
_original_index = admin.site.index

def custom_index(self, request, extra_context=None):
    """Custom admin index with grouped models"""
    app_list = self.get_app_list(request)
    
    # Group models
    grouped_apps = {}
    
    for app in app_list:
        for model in app.get('models', []):
            model_name = model['object_name'].lower()
            
            # Group product-related models
            if model_name in ['category', 'product', 'order', 'productspecification']:
                group_name = 'Bán Tài Khoản'
                if group_name not in grouped_apps:
                    grouped_apps[group_name] = {'name': group_name, 'models': []}
                
                # Rename display names
                display_names = {
                    'category': 'Danh mục',
                    'product': 'Sản phẩm',
                    'order': 'Đơn hàng',
                    'productspecification': 'Thông số kỹ thuật',
                }
                
                model['name'] = display_names.get(model_name, model['name'])
                grouped_apps[group_name]['models'].append(model)
            else:
                # Other models
                group_name = 'Khác'
                if group_name not in grouped_apps:
                    grouped_apps[group_name] = {'name': group_name, 'models': []}
                grouped_apps[group_name]['models'].append(model)
    
    # Convert to list and maintain order
    custom_app_list = []
    for key in ['Bán Tài Khoản', 'Khác']:
        if key in grouped_apps:
            custom_app_list.append(grouped_apps[key])
    
    if extra_context is None:
        extra_context = {}
    
    extra_context['app_list'] = custom_app_list
    extra_context['title'] = self.index_title
    
    return TemplateResponse(request, self.index_template or 'admin/index.html', extra_context)

# Bind custom index method to admin.site
admin.site.index = custom_index.__get__(admin.site, type(admin.site))
admin.site.site_header = "Quản lý Cửa hàng"
admin.site.index_title = "Bảng điều khiển quản lý"

# ================== PRODUCT ==================

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ('file', 'title', 'is_primary', 'sort_order')


class ProductColorInline(admin.TabularInline):
    model = ProductColor
    extra = 1
    fields = ('name', 'image', 'hex', 'price_delta', 'sort_order')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # show discount and allow inline editing of price and discount for quick adjustments
    list_display = ('id', 'name', 'category', 'ram', 'rom', 'price', 'discount', 'stock', 'created_at')
    list_filter = ('category', 'ram', 'rom', 'created_at')
    search_fields = ('name',)
    list_editable = ('ram', 'rom', 'price', 'discount', 'stock')
    inlines = [ProductMediaInline, ProductColorInline]

# ================== CATEGORY ==================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# ================== PRODUCT SPECIFICATION ==================

@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'category', 'key', 'value', 'visible')
    list_filter = ('category', 'visible', 'product')
    search_fields = ('product__name', 'key', 'value')
    list_editable = ('visible',)
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('product', 'category', 'key', 'value')
        }),
        ('Cấu hình', {
            'fields': ('visible',),
        }),
    )

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

# ================== BANNER ==================

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('banner_id', 'title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    list_editable = ('is_active',)

# ================== WISHLIST ==================

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_product_count', 'created_at')
    search_fields = ('user__username',)
    filter_horizontal = ('products',)
    
    def get_product_count(self, obj):
        return obj.products.count()
    get_product_count.short_description = 'Products'
