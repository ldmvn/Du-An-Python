import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


def banner_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in {'.mp4', '.webm', '.ogg', '.mov', '.m4v'}:
        return f'banner/videos/{filename}'
    else:
        return f'banner/image/{filename}'


def product_media_upload_path(instance, filename):
    return f'Sanpham/{instance.product_id}/{filename}'


class UserProfile(models.Model):
    """Extended user profile for additional fields"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# Tạo UserProfile tự động khi User được tạo
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        UserProfile.objects.get_or_create(user=instance)


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    RAM_CHOICES = [
        ('4GB', '4GB'),
        ('6GB', '6GB'),
        ('8GB', '8GB'),
        ('12GB', '12GB'),
        ('16GB', '16GB'),
        ('32GB', '32GB'),
    ]
    
    ROM_CHOICES = [
        ('32GB', '32GB'),
        ('64GB', '64GB'),
        ('128GB', '128GB'),
        ('256GB', '256GB'),
        ('512GB', '512GB'),
        ('1TB', '1TB'),
    ]
    
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    name = models.CharField(max_length=255)
    price = models.IntegerField()
    discount = models.IntegerField(default=0, help_text="Giảm giá theo %")
    ram = models.CharField(max_length=10, choices=RAM_CHOICES, default='8GB', help_text="Bộ nhớ RAM")
    rom = models.CharField(max_length=10, choices=ROM_CHOICES, default='128GB', help_text="Bộ nhớ ROM")
    description = models.TextField(blank=True)
    spec_category_order = models.TextField(blank=True, default='', help_text='Danh sách thứ tự cụm thông số, phân tách bằng dấu phẩy')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    feature_image = models.ImageField(upload_to='Sanpham/features/', blank=True, null=True)
    feature_content = models.TextField(blank=True, default='')
    stock = models.IntegerField(default=0, help_text="Số lượng sản phẩm trong kho")
    pending_media = models.BooleanField(default=False, help_text="Đánh dấu sản phẩm đã chọn để thêm media")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def get_discounted_price(self):
        """Tính giá sau khi giảm"""
        if self.discount > 0:
            return int(self.price * (100 - self.discount) / 100)
        return self.price
    
    def get_avg_rating(self):
        """Lấy rating trung bình từ reviews"""
        reviews = self.review_set.all()
        if reviews.exists():
            avg = sum(r.rating for r in reviews) / reviews.count()
            return round(avg, 1)
        return 0
    
    def get_review_count(self):
        """Đếm số lượng reviews"""
        return self.review_set.count()


    def get_primary_media(self):
        primary_media = self.media_items.filter(is_primary=True).first()
        if primary_media:
            return primary_media
        return self.media_items.order_by('sort_order', 'id').first()


class ProductColor(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='colors'
    )
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='Sanpham/colors/', blank=True, null=True)
    hex = models.CharField(max_length=7, default='#d1d5db')
    price_delta = models.IntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductRamOption(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ram_options'
    )
    value = models.CharField(max_length=20)
    price_delta = models.IntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} - RAM {self.value}"


class ProductStorageOption(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='storage_options'
    )
    capacity = models.CharField(max_length=20)
    price_delta = models.IntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} - ROM {self.capacity}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ xác nhận'),
        ('awaiting_payment', 'Chờ thanh toán'),
        ('processing', 'Đã đặt hàng'),
        ('shipped', 'Đang giao'),
        ('delivered', 'Đã giao hàng'),
        ('expired', 'Hết hạn thanh toán'),
        ('cancelled', 'Hủy đơn'),
    ]

    LEGACY_STATUS_MAP = {
        'paid': 'pending',
        'approved': 'processing',
        'completed': 'delivered',
    }

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Thanh toán khi nhận hàng'),
        ('bank', 'Chuyển khoản ngân hàng'),
        ('vnpay', 'VNPAY'),
        ('vietqr', 'VIETQR'),
        ('momo', 'MoMo'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, default='')
    total_amount = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    customer_address = models.TextField(blank=True, default='')
    customer_name = models.CharField(max_length=255, blank=True, default='')
    customer_phone = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_status = models.CharField(
        max_length=20,
        default='pending',
        blank=True
    )

    @property
    def normalized_status(self):
        return self.LEGACY_STATUS_MAP.get(self.status, self.status)

    def get_status_display(self):
        status_labels = dict(self.STATUS_CHOICES)
        return status_labels.get(self.normalized_status, self.normalized_status)

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.IntegerField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_total(self):
        """Tính tổng giá của item (price * quantity)"""
        return self.price * self.quantity


class PendingQRPayment(models.Model):
    """Theo dõi thanh toán VietQR - chờ admin duyệt"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.IntegerField()
    transfer_code = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('cancelled', 'Đã hủy'),
            ('expired', 'Hết hạn'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"QR Payment {self.transfer_code} - {self.amount}đ"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.rating}⭐"
class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='specs'
    )
    category = models.CharField(max_length=100, blank=True, default='')
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.key}"


class Banner(models.Model):
    """Banner media for homepage slider"""
    banner_id = models.IntegerField(unique=True, help_text="Banner position (1, 2, 3, ...)")
    image = models.FileField(upload_to=banner_upload_path, help_text="Banner image or video")
    title = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['banner_id']

    def __str__(self):
        return f"Banner #{self.banner_id}"

    @property
    def media_extension(self):
        if not self.image:
            return ''
        return os.path.splitext(self.image.name)[1].lower()

    @property
    def is_video(self):
        return self.media_extension in {'.mp4', '.webm', '.ogg', '.mov', '.m4v'}


class Voucher(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, default='')
    discount_percent = models.PositiveSmallIntegerField(
        default=0,
        help_text='Giảm giá theo phần trăm'
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Số lần sử dụng tối đa (để trống nếu không giới hạn)'
    )
    used_count = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    @property
    def is_expired(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.end_date is not None and self.end_date < today

    def can_use(self):
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        if self.end_date and self.end_date < self.start_date:
            return False
        return self.active


class ProductMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='media_items'
    )
    file = models.FileField(upload_to=product_media_upload_path)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    title = models.CharField(max_length=255, blank=True, default='')
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} - {self.media_type}"

    @property
    def extension(self):
        if not self.file:
            return ''
        return os.path.splitext(self.file.name)[1].lower()

    @property
    def url(self):
        if self.file:
            return self.file.url
        return ''

    @property
    def is_video(self):
        return self.media_type == 'video'

    @property
    def is_image(self):
        return self.media_type == 'image'

    def save(self, *args, **kwargs):
        if self.extension in {'.mp4', '.webm', '.ogg', '.mov', '.m4v'}:
            self.media_type = 'video'
        else:
            self.media_type = 'image'

        super().save(*args, **kwargs)

        if self.is_primary:
            ProductMedia.objects.filter(product=self.product).exclude(pk=self.pk).update(is_primary=False)


class Wishlist(models.Model):
    """User wishlist for saving favorite products"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, related_name='wishlisted_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"
    
    def add_product(self, product):
        """Add a product to wishlist"""
        self.products.add(product)
    
    def remove_product(self, product):
        """Remove a product from wishlist"""
        self.products.remove(product)
    
    def toggle_product(self, product):
        """Add or remove a product from wishlist"""
        if self.products.filter(id=product.id).exists():
            self.remove_product(product)
            return False
        else:
            self.add_product(product)
            return True
    

class PasswordResetToken(models.Model):
    """Model to store password reset tokens with 2-step verification"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, blank=True, default='')  # Verification code
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)  # Track if email was verified with code
    
    def __str__(self):
        return f"Reset token for {self.user.username}"
    
    def is_valid(self):
        """Check if token is still valid"""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()
    
    def is_code_valid(self, provided_code):
        """Check if provided code matches and is not expired"""
        return self.code == provided_code and self.is_valid()


