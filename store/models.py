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
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField(default=0, help_text="Số lượng sản phẩm trong kho")
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


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ xử lý'),
        ('processing', 'Xử lý'),
        ('shipped', 'Đang giao'),
        ('delivered', 'Hoàn tất'),
        ('cancelled', 'Đã huỷ'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Thanh toán khi nhận hàng'),
        ('bank', 'Chuyển khoản ngân hàng'),
        ('vnpay', 'VNPAY'),
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
    created_at = models.DateTimeField(auto_now_add=True)

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
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

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
    