from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db.models import Q, Count
from django.urls import reverse
import os
import requests
import hashlib
import hmac
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

from .models import Product, ProductColor, ProductMedia, ProductSpecification, ProductRamOption, ProductStorageOption, Review, UserProfile, Category, Order, OrderItem, Banner, Voucher, Wishlist
from .forms import ProductForm, UserProfileForm, UserExtendedProfileForm, ChangePasswordForm, CategoryForm, UserManagementForm, CheckoutForm, BannerForm, OrderShippingForm, VoucherForm


# ================== UTILS ==================
def is_admin(user):
    return user.is_staff


def get_user_wishlist(request):
    """Return the authenticated user's Wishlist instance, creating one if necessary."""
    if not request.user.is_authenticated:
        return None
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return wishlist


def get_wishlist_ids(request):
    """Return the wishlist product IDs for authenticated or session-based users."""
    if request.user.is_authenticated:
        wishlist = get_user_wishlist(request)
        session_wishlist = request.session.pop('wishlist', []) if request.session.get('wishlist') else []
        if session_wishlist and wishlist:
            products = Product.objects.filter(id__in=session_wishlist)
            if products.exists():
                wishlist.products.add(*products)
        return list(wishlist.products.values_list('id', flat=True))
    return request.session.get('wishlist', [])


def get_base_context(request):
    """Return common context vars needed by base.html"""
    cart = request.session.get('cart', {})
    wishlist_ids = get_wishlist_ids(request)
    order_count = 0
    
    if request.user.is_authenticated:
        order_count = Order.objects.filter(
            user=request.user
        ).exclude(status__in=['delivered', 'cancelled']).count()
    
    user_display_name = 'Khách'
    if request.user.is_authenticated:
        user_display_name = request.user.username
    
    return {
        'cart_count': len(cart),
        'wishlist_count': len(wishlist_ids),
        'wishlist_ids': wishlist_ids,
        'order_count': order_count,
        'user_display_name': user_display_name,
    }


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _build_vnpay_payment_url(request, order_number, amount):
    """Build VNPAY redirect URL for an order."""
    params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': str(int(amount) * 100),
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': order_number,
        'vnp_OrderInfo': f'Thanh toan don hang {order_number}',
        'vnp_OrderType': 'other',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': settings.VNPAY_RETURN_URL,
        'vnp_IpAddr': _get_client_ip(request),
        'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S'),
    }

    sorted_items = sorted(params.items())
    hash_data = '&'.join(f"{k}={v}" for k, v in sorted_items)
    secure_hash = hmac.new(
        settings.VNPAY_HASH_SECRET.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    params['vnp_SecureHashType'] = 'SHA512'
    params['vnp_SecureHash'] = secure_hash
    return f"{settings.VNPAY_URL}?{urlencode(params)}"


def _send_telegram_notification(message):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    logger.info(f"🔔 Telegram Notification - Token: {token[:10]}..., Chat ID: {chat_id}")
    
    if not token or not chat_id:
        logger.error("❌ Token hoặc Chat ID trống!")
        return False

    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }
        
        logger.info(f"📤 Gửi request tới: {url}")
        response = requests.post(url, data=payload, timeout=5)
        
        logger.info(f"📥 Response status: {response.status_code}")
        logger.info(f"📥 Response body: {response.text}")
        
        if response.ok:
            logger.info("✅ Telegram notification sent successfully!")
            return True
        else:
            logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout khi gọi Telegram API (5s)")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def _notify_order_pending(order):
    message = (
        f"🟡 Đơn hàng mới chờ duyệt\n"
        f"Mã đơn hàng: {order.order_number}\n"
        f"Khách hàng: {order.customer_name or 'Khách vãng lai'}\n"
        f"SĐT: {order.customer_phone or 'Không có'}\n"
        f"Tổng: {order.total_amount:,}đ\n"
        f"Phương thức: {order.get_payment_method_display()}\n"
        f"Trạng thái: {order.get_status_display()}"
    )
    _send_telegram_notification(message)


def _notify_order_success(order):
    message = (
        f"✅ Đơn hàng thành công\n"
        f"Mã đơn hàng: {order.order_number}\n"
        f"Khách hàng: {order.customer_name or 'Khách vãng lai'}\n"
        f"SĐT: {order.customer_phone or 'Không có'}\n"
        f"Tổng: {order.total_amount:,}đ\n"
        f"Phương thức: {order.get_payment_method_display()}\n"
        f"Trạng thái: {order.get_status_display()}"
    )
    _send_telegram_notification(message)


def _get_next_banner_id():
    last_banner = Banner.objects.order_by('-banner_id').first()
    return (last_banner.banner_id + 1) if last_banner else 1


def _collect_homepage_banners():
    """Collect homepage banner images from the admin-managed banner records."""
    banners = []

    for banner in Banner.objects.filter(is_active=True).order_by('banner_id'):
        if not banner.image:
            continue

        if banner.is_video:
            continue

        banners.append({
            'banner_id': banner.banner_id,
            'media_url': banner.image.url,
            'title': banner.title,
            'description': banner.description,
        })

    return banners


def _collect_homepage_videos():
    """Collect all active video banners for carousel."""
    videos = []

    for banner in Banner.objects.filter(is_active=True).order_by('banner_id'):
        if not banner.image:
            continue

        if not banner.is_video:
            continue

        videos.append({
            'banner_id': banner.banner_id,
            'media_url': banner.image.url,
            'title': banner.title,
            'description': banner.description,
        })

    return videos


def _collect_homepage_video_url():
    """Return the first active video banner URL, falling back to media/banner/videos."""
    video_banner = Banner.objects.filter(is_active=True).order_by('banner_id').first()
    if video_banner and video_banner.image and video_banner.is_video:
        return video_banner.image.url

    video_root = os.path.join(settings.MEDIA_ROOT, 'banner', 'videos')
    preferred_order = ['applv1.mp4', 'sams.mp4', 'xiao.mp4', 'ooppv1.mp4']

    for file_name in preferred_order:
        if os.path.isfile(os.path.join(video_root, file_name)):
            return f'{settings.MEDIA_URL}banner/videos/{file_name}'

    if os.path.isdir(video_root):
        for file_name in sorted(os.listdir(video_root)):
            if os.path.splitext(file_name)[1].lower() == '.mp4':
                return f'{settings.MEDIA_URL}banner/videos/{file_name}'

    return ''


def _is_video_upload(uploaded_file):
    if not uploaded_file:
        return False
    allowed_video_formats = {'.mp4', '.webm', '.ogg', '.mov', '.m4v'}
    return os.path.splitext(uploaded_file.name)[1].lower() in allowed_video_formats


def _is_image_upload(uploaded_file):
    if not uploaded_file:
        return False
    allowed_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    return os.path.splitext(uploaded_file.name)[1].lower() in allowed_image_formats


def _resolve_location_name(code, location_type):
    """Resolve a province/district/ward code to its display name."""
    if not code or not isinstance(code, str):
        return ''
    if not code.isdigit():
        return code.strip()

    api_url = None
    if location_type == 'city':
        api_url = f'https://provinces.open-api.vn/api/p/{code}'
    elif location_type == 'district':
        api_url = f'https://provinces.open-api.vn/api/d/{code}'
    elif location_type == 'ward':
        api_url = f'https://provinces.open-api.vn/api/w/{code}'
    else:
        return code.strip()

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return str(data.get('name', code)).strip()
    except Exception:
        return code.strip()


def _build_full_address(request):
    city = request.POST.get('city', '').strip()
    district = request.POST.get('district', '').strip()
    ward = request.POST.get('ward', '').strip()
    city_name = request.POST.get('city_name', '').strip()
    district_name = request.POST.get('district_name', '').strip()
    ward_name = request.POST.get('ward_name', '').strip()

    if not city_name:
        city_name = _resolve_location_name(city, 'city')
    if not district_name:
        district_name = _resolve_location_name(district, 'district')
    if not ward_name:
        ward_name = _resolve_location_name(ward, 'ward')

    detail_address = request.POST.get('address', '').strip()
    return f"{detail_address}, {ward_name}, {district_name}, {city_name}"


def _sync_product_media(product, request):
    delete_media_ids = request.POST.getlist('delete_media')
    if delete_media_ids:
        for media in product.media_items.filter(id__in=delete_media_ids):
            if media.file:
                media.file.delete(save=False)
            media.delete()

    primary_media_id = request.POST.get('primary_media')
    if primary_media_id:
        product.media_items.update(is_primary=False)
        product.media_items.filter(id=primary_media_id).update(is_primary=True)

    # Handle separate video and image uploads
    current_max_sort = product.media_items.order_by('-sort_order').values_list('sort_order', flat=True).first() or 0
    has_primary = product.media_items.filter(is_primary=True).exists()
    
    # Process video files
    video_files = request.FILES.getlist('video_files')
    if video_files:
        for index, uploaded_file in enumerate(video_files, start=1):
            media = ProductMedia.objects.create(
                product=product,
                file=uploaded_file,
                media_type='video',
                is_primary=not has_primary and index == 1,
                sort_order=current_max_sort + index
            )
            if media.is_primary:
                has_primary = True
            current_max_sort += 1
    
    # Process image files
    image_files = request.FILES.getlist('image_files')
    if image_files:
        for index, uploaded_file in enumerate(image_files, start=1):
            media = ProductMedia.objects.create(
                product=product,
                file=uploaded_file,
                media_type='image',
                is_primary=not has_primary and index == 1,
                sort_order=current_max_sort + index
            )
            if media.is_primary:
                has_primary = True
            current_max_sort += 1
    
    # Legacy support: handle old media_files field for backward compatibility
    uploaded_files = request.FILES.getlist('media_files')
    if uploaded_files:
        for index, uploaded_file in enumerate(uploaded_files, start=1):
            media = ProductMedia.objects.create(
                product=product,
                file=uploaded_file,
                media_type='image',
                is_primary=not has_primary and index == 1,
                sort_order=current_max_sort + index
            )
            if media.is_primary:
                has_primary = True
            current_max_sort += 1

    feature_content = request.POST.get('feature_content', '').strip()
    delete_feature_image = request.POST.get('delete_feature_image')
    feature_image = request.FILES.get('feature_image')
    feature_fields = []

    if delete_feature_image == '1' and product.feature_image:
        product.feature_image.delete(save=False)
        product.feature_image = None
        feature_fields.append('feature_image')

    if feature_image:
        if product.feature_image:
            product.feature_image.delete(save=False)
        product.feature_image = feature_image
        feature_fields.append('feature_image')

    if feature_content != (product.feature_content or ''):
        product.feature_content = feature_content
        feature_fields.append('feature_content')

    if feature_fields:
        product.save(update_fields=list(dict.fromkeys(feature_fields)))

    if product.media_items.exists() and not product.media_items.filter(is_primary=True).exists():
        first_media = product.media_items.order_by('sort_order', 'id').first()
        if first_media:
            first_media.is_primary = True
            first_media.save()


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _validate_voucher_code(code):
    code = (code or '').strip()
    if not code:
        return None, 'Vui lòng nhập mã voucher.'

    try:
        voucher = Voucher.objects.get(code__iexact=code)
    except Voucher.DoesNotExist:
        return None, 'Mã voucher không hợp lệ.'

    today = timezone.now().date()
    if not voucher.active:
        return None, 'Voucher hiện không hoạt động.'
    if voucher.start_date and voucher.start_date > today:
        return None, 'Voucher chưa đến thời hạn sử dụng.'
    if voucher.end_date and voucher.end_date < today:
        return None, 'Voucher đã hết hạn.'
    if voucher.usage_limit is not None and voucher.used_count >= voucher.usage_limit:
        return None, 'Voucher đã đạt số lần sử dụng tối đa.'

    return voucher, None


def _calculate_voucher_discount(subtotal, voucher):
    if not voucher or subtotal <= 0:
        return 0
    return int(subtotal * voucher.discount_percent / 100)


def _sync_product_colors(product, request):
    """
    Sync colors submitted from custom admin product form.
    Supports:
    - Add new color
    - Update existing color
    - Delete color
    - Upload/replace/clear color image
    """
    row_keys = request.POST.getlist('color_row_keys')
    if not row_keys:
        return

    color_qs = product.colors.all()
    color_map = {str(c.id): c for c in color_qs}
    sort_order = 0

    for row_key in row_keys:
        color_id = (request.POST.get(f'color_id__{row_key}', '') or '').strip()
        is_deleted = request.POST.get(f'color_delete__{row_key}') == '1'
        name = (request.POST.get(f'color_name__{row_key}', '') or '').strip()
        hex_value = (request.POST.get(f'color_hex__{row_key}', '') or '#d1d5db').strip() or '#d1d5db'
        price_delta = _safe_int(request.POST.get(f'color_price__{row_key}'), 0)
        image_file = request.FILES.get(f'color_image__{row_key}')
        clear_image = request.POST.get(f'color_clear_image__{row_key}') == '1'

        if color_id and color_id in color_map:
            color_obj = color_map[color_id]
        else:
            color_obj = None

        if is_deleted:
            if color_obj:
                if color_obj.image:
                    color_obj.image.delete(save=False)
                color_obj.delete()
            continue

        # Ignore empty new rows
        if not color_obj and not name:
            continue

        if not color_obj:
            color_obj = ProductColor(product=product)

        color_obj.name = name or color_obj.name
        color_obj.hex = hex_value
        color_obj.price_delta = price_delta
        color_obj.sort_order = sort_order
        sort_order += 1

        if clear_image and color_obj.image:
            color_obj.image.delete(save=False)
            color_obj.image = None
        if image_file:
            color_obj.image = image_file

        color_obj.save()


def _sync_product_ram_options(product, request):
    row_keys = request.POST.getlist('ram_row_keys')
    if not row_keys:
        return

    ram_qs = product.ram_options.all()
    ram_map = {str(r.id): r for r in ram_qs}
    sort_order = 0

    for row_key in row_keys:
        ram_id = (request.POST.get(f'ram_id__{row_key}', '') or '').strip()
        is_deleted = request.POST.get(f'ram_delete__{row_key}') == '1'
        value = (request.POST.get(f'ram_value__{row_key}', '') or '').strip()
        price_delta = _safe_int(request.POST.get(f'ram_price__{row_key}'), 0)

        if ram_id and ram_id in ram_map:
            ram_obj = ram_map[ram_id]
        else:
            ram_obj = None

        if is_deleted:
            if ram_obj:
                ram_obj.delete()
            continue

        if not ram_obj and not value:
            continue

        if not ram_obj:
            ram_obj = ProductRamOption(product=product)

        ram_obj.value = value or ram_obj.value
        ram_obj.price_delta = price_delta
        ram_obj.sort_order = sort_order
        sort_order += 1
        ram_obj.save()


def _sync_product_storage_options(product, request):
    row_keys = request.POST.getlist('storage_row_keys')
    if not row_keys:
        return

    storage_qs = product.storage_options.all()
    storage_map = {str(s.id): s for s in storage_qs}
    sort_order = 0

    for row_key in row_keys:
        storage_id = (request.POST.get(f'storage_id__{row_key}', '') or '').strip()
        is_deleted = request.POST.get(f'storage_delete__{row_key}') == '1'
        capacity = (request.POST.get(f'storage_capacity__{row_key}', '') or '').strip()
        price_delta = _safe_int(request.POST.get(f'storage_price__{row_key}'), 0)

        if storage_id and storage_id in storage_map:
            storage_obj = storage_map[storage_id]
        else:
            storage_obj = None

        if is_deleted:
            if storage_obj:
                storage_obj.delete()
            continue

        if not storage_obj and not capacity:
            continue

        if not storage_obj:
            storage_obj = ProductStorageOption(product=product)

        storage_obj.capacity = capacity or storage_obj.capacity
        storage_obj.price_delta = price_delta
        storage_obj.sort_order = sort_order
        sort_order += 1
        storage_obj.save()


def _sync_product_specifications(product, request):
    row_keys = request.POST.getlist('spec_row_keys')
    if not row_keys:
        row_keys = []

    spec_qs = product.specs.all()
    spec_map = {str(s.id): s for s in spec_qs}

    for row_key in row_keys:
        spec_id = (request.POST.get(f'spec_id__{row_key}', '') or '').strip()
        is_deleted = request.POST.get(f'spec_delete__{row_key}') == '1'
        category = (request.POST.get(f'spec_category__{row_key}', '') or '').strip()
        key = (request.POST.get(f'spec_key__{row_key}', '') or '').strip()
        value = (request.POST.get(f'spec_value__{row_key}', '') or '').strip()
        visible = request.POST.get(f'spec_visible__{row_key}') == '1'

        if spec_id and spec_id in spec_map:
            spec_obj = spec_map[spec_id]
        else:
            spec_obj = None

        if is_deleted:
            if spec_obj:
                spec_obj.delete()
            continue

        # Skip empty new rows.
        if not spec_obj and not key and not value:
            continue

        if not spec_obj:
            spec_obj = ProductSpecification(product=product)

        spec_obj.category = category
        spec_obj.key = key or spec_obj.key
        spec_obj.value = value or spec_obj.value
        spec_obj.visible = visible
        spec_obj.save()

    raw_order = request.POST.get('spec_category_order', '') or ''
    ordered_categories = []
    for category in raw_order.split(','):
        category = category.strip()
        if category and category not in ordered_categories:
            ordered_categories.append(category)
    product.spec_category_order = ','.join(ordered_categories)
    product.save(update_fields=['spec_category_order'])


def _build_product_media_gallery(product):
    media_items = list(product.media_items.all())
    gallery = []

    for media in media_items:
        gallery.append({
            'id': media.id,
            'url': media.file.url,
            'thumb_url': media.file.url,
            'title': media.title or product.name,
            'media_type': media.media_type,
            'is_primary': media.is_primary,
        })

    if not gallery and product.image:
        gallery.append({
            'id': f'fallback-{product.id}',
            'url': product.image.url,
            'thumb_url': product.image.url,
            'title': product.name,
            'media_type': 'image',
            'is_primary': True,
        })

    if gallery and not any(item['is_primary'] for item in gallery):
        gallery[0]['is_primary'] = True

    return gallery


def _banner_media_type_filter(media_type):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    video_extensions = ['.mp4', '.webm', '.ogg', '.mov', '.m4v']
    query = Q()

    extensions = image_extensions if media_type == 'image' else video_extensions
    for extension in extensions:
        query |= Q(image__iendswith=extension)

    return query


def _get_static_video_files():
    video_root = os.path.join(settings.MEDIA_ROOT, 'banner', 'videos')
    if not os.path.isdir(video_root):
        return []

    preferred_order = ['applv1.mp4', 'sams.mp4', 'xiao.mp4', 'ooppv1.mp4']
    found_files = []
    seen_files = set()

    for file_name in preferred_order:
        file_path = os.path.join(video_root, file_name)
        if os.path.isfile(file_path):
            found_files.append(file_name)
            seen_files.add(file_name)

    for file_name in sorted(os.listdir(video_root)):
        if file_name in seen_files:
            continue
        if os.path.splitext(file_name)[1].lower() in {'.mp4', '.webm', '.ogg', '.mov', '.m4v'}:
            found_files.append(file_name)

    return found_files


def _get_static_banner_image_files():
    banner_root = os.path.join(settings.MEDIA_ROOT, 'banner', 'image')
    if not os.path.isdir(banner_root):
        return []

    found_files = []
    for root, _, files in os.walk(banner_root):
        for file_name in sorted(files):
            extension = os.path.splitext(file_name)[1].lower()
            if extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
                relative_path = os.path.relpath(os.path.join(root, file_name), settings.MEDIA_ROOT).replace('\\', '/')
                found_files.append(relative_path)

    return found_files


def _import_static_videos_to_banner():
    video_root = os.path.join(settings.MEDIA_ROOT, 'banner', 'videos')
    imported = 0
    skipped = 0

    for file_name in _get_static_video_files():
        relative_name = f'banner/videos/{file_name}'
        exists = Banner.objects.filter(image=relative_name).exists()
        if exists:
            skipped += 1
            continue

        file_path = os.path.join(video_root, file_name)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, 'rb') as source_file:
            banner = Banner(
                banner_id=_get_next_banner_id(),
                title=os.path.splitext(file_name)[0].replace('_', ' ').replace('-', ' ').title(),
                description='Imported from media/banner/videos',
                is_active=True,
            )
            banner.image.save(f'videos/{file_name}', ContentFile(source_file.read()), save=False)
            banner.save()
            imported += 1

        # Clean up source file after import
        try:
            os.remove(file_path)
        except OSError:
            pass  # Ignore if file already removed or permission issue

    return imported, skipped


def _import_static_images_to_banner():
    imported = 0
    skipped = 0

    for relative_name in _get_static_banner_image_files():
        exists = Banner.objects.filter(image=relative_name).exists()
        if exists:
            skipped += 1
            continue

        file_path = os.path.join(settings.MEDIA_ROOT, relative_name.replace('/', os.sep))
        if not os.path.isfile(file_path):
            continue

        file_name = os.path.basename(relative_name)
        with open(file_path, 'rb') as source_file:
            banner = Banner(
                banner_id=_get_next_banner_id(),
                title=os.path.splitext(file_name)[0].replace('_', ' ').replace('-', ' ').title(),
                description='Imported from media/banner/image',
                is_active=True,
            )
            # Save to image/ subfolder
            sub_path = relative_name.split('/', 2)[-1]  # e.g., '2026/02/file.jpg'
            banner.image.save(f'image/{sub_path}', ContentFile(source_file.read()), save=False)
            banner.save()
            imported += 1

        # Clean up source file after import
        try:
            os.remove(file_path)
        except OSError:
            pass  # Ignore if file already removed or permission issue

    return imported, skipped


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
def home(request):
    q = request.GET.get('q')
    brand = request.GET.get('brand', '').strip()
    price_range = request.GET.get('price_range', '')
    sort_by = request.GET.get('sort_by', '')
    
    # Advanced filters
    price_min = request.GET.get('price_min', '0')
    price_max = request.GET.get('price_max', '64000000')
    rams = request.GET.getlist('ram')
    storages = request.GET.getlist('storage')
    
    try:
        price_min = int(price_min) if price_min else 0
        price_max = int(price_max) if price_max else 64000000
    except (ValueError, TypeError):
        price_min = 0
        price_max = 64000000
    
    products = Product.objects.all()

    if q:
        products = products.filter(name__icontains=q)

    # Filter by brand (category) if provided
    if brand and brand.lower() != 'all':
        products = products.filter(category__name__iexact=brand)

    # Filter by price range (legacy)
    if price_range:
        if price_range == 'under_5m':
            products = products.filter(price__lt=5000000)
        elif price_range == '5m_10m':
            products = products.filter(price__gte=5000000, price__lt=10000000)
        elif price_range == '10m_20m':
            products = products.filter(price__gte=10000000, price__lt=20000000)
        elif price_range == 'over_20m':
            products = products.filter(price__gte=20000000)
    
    # Filter by price min/max (new)
    if price_min or price_max:
        if price_min:
            products = products.filter(price__gte=price_min)
        if price_max:
            products = products.filter(price__lte=price_max)
    
    # Filter by RAM
    if rams:
        ram_filter = Q()
        for ram in rams:
            ram_filter |= Q(ram=ram) | Q(ram_options__value=ram)
        if ram_filter:
            products = products.filter(ram_filter).distinct()
    
    # Filter by storage
    if storages:
        storage_filter = Q()
        for storage in storages:
            storage_filter |= Q(rom=storage) | Q(storage_options__capacity=storage)
        if storage_filter:
            products = products.filter(storage_filter).distinct()
    
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
    wishlist_ids = get_wishlist_ids(request)
    wishlist_products = Product.objects.filter(id__in=wishlist_ids)

    # Home page media: top video banner carousel, bottom image banners
    hero_banners = _collect_homepage_banners()
    hero_videos = _collect_homepage_videos()

    # pull all categories (used as "brands"/manufacturers on the homepage)
    categories = Category.objects.all()

    # Prepare filter options
    ram_options = sorted(list(set([p.ram for p in Product.objects.all() if p.ram] + list(ProductRamOption.objects.values_list('value', flat=True)))))
    storage_options = sorted(list(set([p.rom for p in Product.objects.all() if p.rom] + list(ProductStorageOption.objects.values_list('capacity', flat=True)))))

    context = get_base_context(request)
    context.update({
        'products': products,
        'categories': categories,
        'selected_brand': brand or 'all',
        'search_query': q,
        'price_range': price_range,
        'price_min': price_min,
        'price_max': price_max,
        'sort_by': sort_by,
        'wishlist_products': wishlist_products,
        'hero_banners': hero_banners,
        'hero_videos': hero_videos,
        'selected_rams': rams,
        'selected_storages': storages,
        'ram_options': ram_options,
        'storages': storage_options,
    })
    return render(request, 'store/home.html', context)


# ================== PRODUCT DETAIL ==================
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Vui lòng đăng nhập để gửi đánh giá.')
            login_url = f"{resolve_url('store:login')}?next={reverse('store:product_detail', args=[id])}#pd-reviews"
            return redirect(login_url)

        rating = int(request.POST.get('rating', '0') or 0)
        comment = (request.POST.get('comment') or '').strip()
        if rating < 1 or rating > 5:
            messages.error(request, 'Vui lòng chọn số sao từ 1 đến 5.')
            return redirect('store:product_detail', id=id)

        review, created = Review.objects.get_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating, 'comment': comment}
        )
        if not created:
            review.rating = rating
            review.comment = comment
            review.save()

        messages.success(request, 'Đánh giá của bạn đã được lưu.')
        return redirect('store:product_detail', id=id)

    media_gallery = _build_product_media_gallery(product)
    primary_media = next((item for item in media_gallery if item['is_primary']), media_gallery[0] if media_gallery else None)
    first_video = next((item for item in media_gallery if item.get('media_type') == 'video'), None)
    feature_image_url = product.feature_image.url if product.feature_image else ''
    raw_feature_content = (product.feature_content or '').strip()
    feature_points = []
    if raw_feature_content:
        for line in raw_feature_content.splitlines():
            cleaned_line = line.strip().lstrip('-').lstrip('•').strip()
            if cleaned_line:
                feature_points.append(cleaned_line)
        if not feature_points:
            feature_points = [raw_feature_content]
    reviews = product.review_set.select_related('user').order_by('-created_at')

    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:8]

    base_price = product.get_discounted_price()
    db_storage_options = list(product.storage_options.all())
    if db_storage_options:
        storage_options = []
        for index, option in enumerate(db_storage_options):
            if index == 0:
                label = 'Tiêu chuẩn'
            elif index == 1:
                label = 'Phổ biến'
            else:
                label = 'Tùy chọn'
            storage_options.append({
                'capacity': option.capacity,
                'price': base_price + (option.price_delta or 0),
                'price_delta': option.price_delta or 0,
                'label': label,
            })
    else:
        storage_options = []

    db_ram_options = list(product.ram_options.all())
    if db_ram_options:
        ram_options = []
        for index, option in enumerate(db_ram_options):
            if index == 0:
                label = 'Tiêu chuẩn'
            elif index == 1:
                label = 'Phổ biến'
            else:
                label = 'Tùy chọn'
            ram_options.append({
                'value': option.value,
                'price_delta': option.price_delta or 0,
                'label': label,
            })
        default_ram = ram_options[0]['value'] if ram_options else (product.ram or '8GB')
    else:
        ram_options = []
        default_ram = ''
    db_colors = list(product.colors.all())
    if db_colors:
        color_options = [
            {
                'name': color.name,
                'hex': color.hex or '#d1d5db',
                'price_delta': color.price_delta or 0,
                'image_url': color.image.url if color.image else '',
            }
            for color in db_colors
        ]
    else:
        color_options = []
    promotions = [
        {'icon': 'gift', 'text': 'Giảm thêm 500.000đ khi thanh toán qua VNPAY.'},
        {'icon': 'shield', 'text': 'Tặng gói bảo hành rơi vỡ 6 tháng đầu.'},
        {'icon': 'truck', 'text': 'Giao nhanh 2 giờ nội thành cho đơn đủ điều kiện.'},
        {'icon': 'credit-card', 'text': 'Trả góp 0% qua thẻ tín dụng hoặc công ty tài chính.'},
    ]
    visible_specs = list(product.specs.filter(visible=True).all())
    all_specs = list(product.specs.all())
    spec_items = []
    for spec in visible_specs:
        spec_items.append({'category': spec.category, 'key': spec.key, 'value': spec.value})

    all_spec_items = []
    for spec in all_specs:
        all_spec_items.append({'category': spec.category, 'key': spec.key, 'value': spec.value})

    spec_category_order = []
    if product.spec_category_order:
        spec_category_order = [c.strip() for c in product.spec_category_order.split(',') if c.strip()]

    description_blocks = [
        {
            'title': 'Thiết kế cao cấp',
            'body': product.description or 'Khung viền hoàn thiện cao cấp, cảm giác cầm chắc tay và hướng tới trải nghiệm flagship đúng nghĩa.'
        },
        {
            'title': 'Hiệu năng và camera',
            'body': 'Máy hướng tới nhóm người dùng cần hiệu năng mạnh, camera ổn định và thời lượng pin đủ cho cường độ sử dụng cao trong ngày.'
        },
    ]
    review_summary = {
        'avg': product.get_avg_rating(),
        'count': product.get_review_count(),
        'stars': [5, 4, 3, 2, 1],
    }

    context = get_base_context(request)
    context.update({
        'product': product,
        'related_products': related_products,
        'media_gallery': media_gallery,
        'primary_media': primary_media,
        'first_video': first_video,
        'feature_image_url': feature_image_url,
        'feature_points': feature_points,
        'storage_options': storage_options,
        'ram_options': ram_options,
        'default_ram': default_ram,
        'color_options': color_options,
        'promotions': promotions,
        'base_price': base_price,
        'specifications': spec_items,
        'all_specifications': all_spec_items,
        'spec_category_order': spec_category_order,
        'description_blocks': description_blocks,
        'reviews': reviews,
        'review_summary': review_summary,
        'selected_review': reviews.filter(user=request.user).first() if request.user.is_authenticated else None,
    })
    return render(request, 'store/product_detail.html', context)


def _fetch_vietqr_banks():
    """Fetch bank list from VietQR API, with fallback to hardcoded list."""
    try:
        response = requests.get('https://api.vietqr.io/v2/banks', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00' and data.get('data'):
                banks = []
                for bank in data['data']:
                    banks.append({
                        'id': bank.get('code', ''),
                        'name': bank.get('name', ''),
                        'bin': bank.get('bin', ''),
                    })
                return banks
    except Exception:
        pass
    
    # Fallback hardcoded list
    return [
        {'id': 'NCB', 'name': 'Ngân hàng Quốc Dân', 'bin': '970415'},
        {'id': 'BIDV', 'name': 'Ngân hàng Đầu tư và Phát triển Việt Nam', 'bin': '970436'},
        {'id': 'TECH', 'name': 'Techcombank', 'bin': '970407'},
        {'id': 'VCB', 'name': 'Ngân hàng Ngoại thương Việt Nam', 'bin': '970403'},
        {'id': 'VIB', 'name': 'Ngân hàng Quốc Tế Việt Nam', 'bin': '970441'},
        {'id': 'ACB', 'name': 'Ngân hàng Á Châu', 'bin': '970425'},
        {'id': 'TPB', 'name': 'Ngân hàng Tiên Phong', 'bin': '970423'},
        {'id': 'VPB', 'name': 'Ngân hàng Việt Nam Thương Tín', 'bin': '970432'},
    ]


@login_required(login_url='store:login')
def bank_select(request):
    """Show bank options for pending bank-transfer orders."""
    pending = request.session.get('pending_order')
    if not pending or pending.get('payment_method') != 'bank':
        messages.error(request, 'Không có đơn hàng đang chờ thanh toán chuyển khoản.')
        return redirect('store:cart_detail')

    # Fetch banks from VietQR API
    banks = _fetch_vietqr_banks()

    # Handle POST - save selected bank and redirect to form
    if request.method == 'POST':
        bank_id = request.POST.get('bank_id')
        if bank_id:
            pending['bank_id'] = bank_id
            # Find and save the bank name
            for bank in banks:
                if bank['id'] == bank_id:
                    pending['bank_name'] = bank['name']
                    break
            request.session['pending_order'] = pending
            return redirect('store:bank_pay')

    # GET - show bank selection dropdown
    context = get_base_context(request)
    context.update({'banks': banks, 'pending': pending, 'pay_section': 'bank_select'})
    return render(request, 'store/pay.html', context)


@login_required(login_url='store:login')
def bank_pay(request):
    """Display bank payment form after bank selection and handle submission to OTP step."""
    pending = request.session.get('pending_order')
    if not pending or pending.get('payment_method') != 'bank':
        messages.error(request, 'Không có đơn hàng đang chờ thanh toán chuyển khoản.')
        return redirect('store:cart_detail')

    if request.method == 'POST':
        # Process bank form submission
        account_no = request.POST.get('account_no', '').strip()
        account_name = request.POST.get('account_name', '').strip()
        expiry = request.POST.get('expiry', '').strip()

        # Validate form inputs
        if not account_no or not account_name:
            messages.error(request, 'Vui lòng nhập số tài khoản và tên chủ thẻ.')
            return redirect('store:bank_pay')

        # Save bank form data to session
        pending['bank_account_no'] = account_no
        pending['bank_account_name'] = account_name
        pending['bank_expiry'] = expiry
        request.session['pending_order'] = pending

        # Generate OTP
        import secrets
        from django.utils import timezone
        otp = secrets.token_hex(3).upper()  # Generate 6-character hex OTP
        request.session['pending_order_otp'] = otp
        request.session['pending_order_otp_expires'] = (timezone.now() + timezone.timedelta(minutes=15)).isoformat()

        # In real system, send OTP via SMS/Email. Here we flash it for testing
        messages.info(request, f'Mã xác nhận (demo): {otp}')
        return redirect('store:bank_otp')

    # GET - show bank payment form
    context = get_base_context(request)
    context.update({'pending': pending, 'pay_section': 'bank_pay'})
    return render(request, 'store/pay.html', context)


@login_required(login_url='store:login')
def bank_otp(request):
    """Verify OTP and create the final order."""
    pending = request.session.get('pending_order')
    otp_expected = request.session.get('pending_order_otp')
    if not pending or pending.get('payment_method') != 'bank' or not otp_expected:
        messages.error(request, 'Không có giao dịch đang chờ xác nhận.')
        return redirect('store:cart_detail')

    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        if code != otp_expected:
            messages.error(request, 'Mã xác nhận không đúng. Vui lòng thử lại.')
            return redirect('store:bank_otp')

        # Create Order from pending data
        from datetime import datetime
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            if pending.get('type') == 'single':
                product = Product.objects.get(id=int(pending['product_id']))
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    total_amount=pending['total_amount'],
                    status='pending',
                    payment_method='bank',
                    customer_name=pending['fullname'],
                    customer_phone=pending['phone'],
                    customer_address=pending['address']
                )
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=pending['quantity'],
                    price=product.get_discounted_price()
                )
            else:
                # cart type
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    total_amount=pending['total_amount'],
                    status='pending',
                    payment_method='bank',
                    customer_name=pending['fullname'],
                    customer_phone=pending['phone'],
                    customer_address=pending['address']
                )
                for item in pending.get('cart_items', []):
                    try:
                        prod = Product.objects.get(id=int(item.get('product_id')))
                    except Product.DoesNotExist:
                        continue
                    OrderItem.objects.create(
                        order=order,
                        product=prod,
                        quantity=item.get('quantity', 1),
                        price=item.get('price', 0)
                    )

            # Clear session pending keys and cart
            request.session.pop('pending_order', None)
            request.session.pop('pending_order_otp', None)
            request.session['cart'] = {}

            _notify_order_pending(order)
            messages.success(request, f'✅ Đơn hàng được tạo! Mã đơn hàng: {order_number}. Đơn hàng đang chờ xác nhận thanh toán chuyển khoản.')
            return redirect('store:order_success')
        except Exception as e:
            messages.error(request, f'❌ Lỗi xử lý đơn hàng: {e}')
            return redirect('store:cart_detail')

    # GET - show OTP input
    context = get_base_context(request)
    context.update({'pending': pending, 'pay_section': 'bank_otp'})
    return render(request, 'store/pay.html', context)


@login_required(login_url='store:login')
def vietqr_page(request):
    pending = request.session.get('pending_order')
    if not pending or pending.get('payment_method') != 'vietqr':
        messages.error(request, 'Không có đơn hàng VietQR đang chờ thanh toán.')
        return redirect('store:cart_detail')

    order = None
    if pending.get('order_id'):
        order = Order.objects.filter(id=pending.get('order_id')).first()

    timeout_seconds = getattr(settings, 'VIETQR_TIMEOUT_SECONDS', 900)
    remaining_seconds = timeout_seconds
    if order and order.payment_method == 'vietqr':
        if order.status == 'pending':
            elapsed = (timezone.now() - order.created_at).total_seconds()
            if elapsed >= timeout_seconds:
                order.status = 'expired'
                order.save()
            else:
                remaining_seconds = int(timeout_seconds - elapsed)
        elif order.status == 'expired':
            remaining_seconds = 0

    context = get_base_context(request)
    context.update({
        'pending': pending,
        'pay_section': 'vietqr',
        'bank_id': getattr(settings, 'VIETQR_BANK_ID', 'MB'),
        'bank_name': getattr(settings, 'VIETQR_BANK_NAME', 'MB Bank'),
        'bank_account_no': getattr(settings, 'VIETQR_BANK_ACCOUNT_NO', '0386220065'),
        'bank_account_name': getattr(settings, 'VIETQR_BANK_ACCOUNT_NAME', 'LUU DUC MANH'),
        'order': {
            'order_id': pending.get('order_id') or (order.id if order else None),
            'order_code': pending.get('order_code', ''),
            'total_amount': pending.get('total_amount', 0),
        },
        'transfer_code': pending.get('transfer_code', ''),
        'timeout_seconds': remaining_seconds,
    })
    return render(request, 'store/pay.html', context)


@login_required(login_url='store:login')
def vietqr_page_status(request):
    pending = request.session.get('pending_order')
    if not pending or pending.get('payment_method') != 'vietqr':
        return JsonResponse({'success': False, 'error': 'Pending VietQR order không tồn tại.'})

    order = None
    if pending.get('order_id'):
        order = Order.objects.filter(id=pending.get('order_id')).first()

    if order and order.payment_method == 'vietqr':
        timeout_seconds = getattr(settings, 'VIETQR_TIMEOUT_SECONDS', 900)
        if order.status == 'pending':
            elapsed = (timezone.now() - order.created_at).total_seconds()
            if elapsed >= timeout_seconds:
                order.status = 'expired'
                order.save()
                return JsonResponse({'success': True, 'status': 'expired'})
            return JsonResponse({'success': True, 'status': 'pending'})
        if order.status in ['processing', 'shipped', 'delivered']:
            return JsonResponse({'success': True, 'status': 'approved'})
        return JsonResponse({'success': True, 'status': order.status})

    return JsonResponse({'success': False, 'error': 'Pending VietQR order không tồn tại.'})


@login_required(login_url='store:login')
def vietqr_page_expire(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Phải dùng phương thức POST.'})

    pending = request.session.get('pending_order')
    order = None
    if pending and pending.get('payment_method') == 'vietqr':
        if pending.get('order_id'):
            order = Order.objects.filter(id=pending.get('order_id')).first()
        elif request.body:
            try:
                import json
                data = json.loads(request.body)
                order_code = data.get('order_code')
                order = Order.objects.filter(order_number=order_code, payment_method='vietqr').first()
            except Exception:
                order = None

        if order and order.status == 'pending':
            order.status = 'expired'
            order.save()
        request.session.pop('pending_order', None)
    return JsonResponse({'success': True})


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
    if not request.user.is_authenticated:
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")

    product_id = str(product_id)
    
    try:
        product = Product.objects.get(id=int(product_id))
        cart = request.session.get('cart', {})
        
        if product_id in cart:
            # Item already in cart - increase quantity
            if isinstance(cart[product_id], dict):
                cart_item = cart[product_id]
                cart_item['quantity'] = cart_item.get('quantity', 0) + 1
                cart[product_id] = cart_item
            else:
                # Old format - convert to new format and keep existing quantity
                old_qty = cart[product_id]
                default_color = product.colors.order_by('sort_order', 'id').first()
                default_color_name = default_color.name if default_color else ''
                default_color_price = default_color.price_delta if default_color else 0
                default_color_image = default_color.image.url if default_color and default_color.image else ''
                default_ram = product.ram or ''
                default_storage = product.rom or ''
                base_price = product.get_discounted_price()
                cart[product_id] = {
                    'name': product.name,
                    'price': base_price + default_color_price,
                    'quantity': old_qty + 1,
                    'image': default_color_image or (product.image.url if product.image else ''),
                    'color': default_color_name,
                    'color_price_delta': default_color_price,
                    'color_image': default_color_image,
                    'ram': default_ram,
                    'ram_price_delta': 0,
                    'storage': default_storage,
                    'storage_price_delta': 0,
                }
        else:
            default_color = product.colors.order_by('sort_order', 'id').first()
            default_color_name = default_color.name if default_color else ''
            default_color_price = default_color.price_delta if default_color else 0
            default_color_image = default_color.image.url if default_color and default_color.image else ''
            default_ram = product.ram or ''
            default_storage = product.rom or ''
            base_price = product.get_discounted_price()
            cart[product_id] = {
                'name': product.name,
                'price': base_price + default_color_price,
                'quantity': 1,
                'image': default_color_image or (product.image.url if product.image else ''),
                'color': default_color_name,
                'color_price_delta': default_color_price,
                'color_image': default_color_image,
                'ram': default_ram,
                'ram_price_delta': 0,
                'storage': default_storage,
                'storage_price_delta': 0,
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
    cart_changed = False

    for product_id, cart_item in list(cart.items()):
        try:
            product = Product.objects.get(id=int(product_id))
            normalized_item = _normalize_cart_item(product, cart_item)
            if cart_item != normalized_item:
                cart[product_id] = normalized_item
                cart_changed = True

            product.quantity = normalized_item.get('quantity', 1)
            product.price = normalized_item.get('price', product.get_discounted_price())
            product.subtotal = product.price * product.quantity
            product.selected_color = normalized_item.get('color', '')
            product.default_color = product.colors.order_by('sort_order', 'id').first().name if product.colors.exists() else ''
            product.selected_ram = normalized_item.get('ram', '')
            product.selected_storage = normalized_item.get('storage', '')
            product.selected_color_image = normalized_item.get('color_image', '')
            product.selected_color_price_delta = normalized_item.get('color_price_delta', 0)
            product.selected_ram_price_delta = normalized_item.get('ram_price_delta', 0)
            product.selected_storage_price_delta = normalized_item.get('storage_price_delta', 0)

            total += product.subtotal
            products.append(product)
        except (Product.DoesNotExist, ValueError):
            pass

    if cart_changed:
        request.session['cart'] = cart

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


def _calculate_cart_item_price(product, cart_item):
    price = product.get_discounted_price()

    color_name = cart_item.get('color')
    if color_name:
        color_obj = product.colors.filter(name=color_name).first()
        if color_obj:
            price += color_obj.price_delta or 0

    ram_value = cart_item.get('ram')
    if ram_value:
        ram_obj = product.ram_options.filter(value=ram_value).first()
        if ram_obj:
            price += ram_obj.price_delta or 0

    storage_value = cart_item.get('storage')
    if storage_value:
        storage_obj = product.storage_options.filter(capacity=storage_value).first()
        if storage_obj:
            price += storage_obj.price_delta or 0

    return price


def _normalize_cart_item(product, cart_item):
    if not isinstance(cart_item, dict):
        cart_item = {'quantity': cart_item}

    default_color = product.colors.order_by('sort_order', 'id').first()
    color_name = cart_item.get('color') or (default_color.name if default_color else '')
    color_obj = product.colors.filter(name=color_name).first() if color_name else None
    ram_value = cart_item.get('ram') or product.ram or ''
    storage_value = cart_item.get('storage') or product.rom or ''

    cart_item['color'] = color_name
    cart_item['color_price_delta'] = color_obj.price_delta if color_obj else 0
    cart_item['color_image'] = color_obj.image.url if color_obj and color_obj.image else cart_item.get('color_image', '')
    cart_item['ram'] = ram_value
    cart_item['ram_price_delta'] = cart_item.get('ram_price_delta', 0)
    cart_item['storage'] = storage_value
    cart_item['storage_price_delta'] = cart_item.get('storage_price_delta', 0)
    cart_item['price'] = _calculate_cart_item_price(product, cart_item)
    return cart_item


def update_cart_option_ajax(request):
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            option_type = request.POST.get('option_type')
            option_value = request.POST.get('option_value')

            cart = request.session.get('cart', {})
            product_key = str(product_id)

            if product_key not in cart:
                return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại trong giỏ'}, status=404)

            product = get_object_or_404(Product, id=int(product_id))
            cart_item = cart[product_key] if isinstance(cart[product_key], dict) else {'quantity': cart[product_key]}

            if option_type == 'color':
                color_obj = product.colors.filter(name=option_value).first()
                if not color_obj:
                    return JsonResponse({'success': False, 'error': 'Màu sắc không hợp lệ'}, status=400)
                cart_item['color'] = color_obj.name
                cart_item['color_price_delta'] = color_obj.price_delta or 0
                cart_item['color_image'] = color_obj.image.url if color_obj.image else cart_item.get('color_image', '')
            elif option_type == 'ram':
                ram_obj = product.ram_options.filter(value=option_value).first()
                if not ram_obj and option_value != product.ram:
                    return JsonResponse({'success': False, 'error': 'RAM không hợp lệ'}, status=400)
                cart_item['ram'] = option_value
                cart_item['ram_price_delta'] = ram_obj.price_delta if ram_obj else 0
            elif option_type == 'storage':
                storage_obj = product.storage_options.filter(capacity=option_value).first()
                if not storage_obj and option_value != product.rom:
                    return JsonResponse({'success': False, 'error': 'Dung lượng không hợp lệ'}, status=400)
                cart_item['storage'] = option_value
                cart_item['storage_price_delta'] = storage_obj.price_delta if storage_obj else 0
            else:
                return JsonResponse({'success': False, 'error': 'Tùy chọn không hợp lệ'}, status=400)

            cart_item['price'] = _calculate_cart_item_price(product, cart_item)
            cart[product_key] = cart_item
            request.session['cart'] = cart

            total_price = sum((item['price'] * item['quantity']) if isinstance(item, dict) else 0 for item in cart.values())
            original_price = 0
            if product.discount > 0:
                original_price = product.price + cart_item.get('color_price_delta', 0) + cart_item.get('ram_price_delta', 0) + cart_item.get('storage_price_delta', 0)

            return JsonResponse({
                'success': True,
                'message': 'Cập nhật tùy chọn thành công',
                'cart_count': sum(item['quantity'] for item in cart.values() if isinstance(item, dict)) if cart else 0,
                'cart_total': total_price,
                'total_price': total_price,
                'item_price': cart_item['price'],
                'item_price_formatted': f"{cart_item['price']:,.0f}₫",
                'new_thumbnail': cart_item.get('color_image', ''),
                'new_color': cart_item.get('color', ''),
                'new_ram': cart_item.get('ram', ''),
                'new_storage': cart_item.get('storage', ''),
                'original_price': original_price,
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required(login_url='store:login')
def clear_cart(request):
    """Clear all items from cart"""
    request.session['cart'] = {}
    messages.success(request, '🗑️ Đã xóa toàn bộ giỏ hàng')
    return redirect('store:cart_detail')


def _remove_products_from_cart(request, product_ids):
    cart = request.session.get('cart', {})
    for product_id in product_ids:
        cart.pop(str(product_id), None)
    request.session['cart'] = cart


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
        
        # Initialize variables that may be used in both if and else branches
        voucher_code = request.POST.get('voucher_code', '').strip().upper()
        voucher = None
        discount_amount = 0
        voucher_error = ''
        
        if form.is_valid():
            fullname = form.cleaned_data['fullname']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            address = form.cleaned_data['address']
            city = form.cleaned_data['city']
            district = form.cleaned_data['district']
            ward = form.cleaned_data['ward']
            payment_method = form.cleaned_data['payment_method']
            if voucher_code:
                voucher, voucher_error = _validate_voucher_code(voucher_code)
                if voucher_error:
                    subtotal = product.get_discounted_price() * quantity
                    total_amount = max(subtotal + 30000, 0)
                    context = get_base_context(request)
                    context.update({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': subtotal,
                        'shipping_cost': 30000,
                        'total_amount': total_amount,
                        'discount_amount': 0,
                        'voucher_code': voucher_code,
                        'voucher_error': voucher_error,
                        'form': form,
                    })
                    return render(request, 'store/checkout.html', context)

            # Combine address with district and ward for full address
            full_address = _build_full_address(request)
            
            try:
                # Handle bank transfer flow separately
                if payment_method == 'bank':
                    # Save pending order in session and redirect to bank selection
                    pending = {
                        'type': 'single',
                        'product_id': product.id,
                        'quantity': quantity,
                        'fullname': fullname,
                        'email': email,
                        'phone': phone,
                        'address': full_address,
                        'voucher_code': voucher_code,
                        'discount_amount': discount_amount,
                        'total_amount': max(product.get_discounted_price() * quantity + 30000 - discount_amount, 0),
                        'payment_method': payment_method,
                    }
                    request.session['pending_order'] = pending
                    _remove_products_from_cart(request, [product.id])
                    return redirect('store:bank_select')

                if payment_method == 'vietqr':
                    import random
                    order_code = f"ldm{random.randint(10000, 99999)}"
                    transfer_code = f"ldm{random.randint(10000, 99999)}"
                    subtotal = product.get_discounted_price() * quantity
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    total_amount = max(subtotal + 30000 - discount_amount, 0)
                    order = Order.objects.create(
                        user=request.user,
                        order_number=order_code,
                        total_amount=total_amount,
                        status='pending',
                        payment_method='vietqr',
                        customer_name=fullname,
                        customer_phone=phone,
                        customer_address=full_address,
                    )
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.get_discounted_price()
                    )
                    _notify_order_pending(order)
                    pending = {
                        'type': 'single',
                        'product_id': product.id,
                        'quantity': quantity,
                        'fullname': fullname,
                        'email': email,
                        'phone': phone,
                        'address': full_address,
                        'voucher_code': voucher_code,
                        'discount_amount': discount_amount,
                        'order_code': order_code,
                        'transfer_code': transfer_code,
                        'order_id': order.id,
                        'total_amount': total_amount,
                        'payment_method': payment_method,
                    }
                    request.session['pending_order'] = pending
                    _remove_products_from_cart(request, [product.id])
                    return redirect('store:vietqr_page')

                if payment_method == 'vnpay':
                    from datetime import datetime
                    order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    subtotal = product.get_discounted_price() * quantity
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    total_amount = max(subtotal + 30000 - discount_amount, 0)
                    order = Order.objects.create(
                        user=request.user,
                        order_number=order_number,
                        total_amount=total_amount,
                        status='pending',
                        payment_method='vnpay',
                        customer_name=fullname,
                        customer_phone=phone,
                        customer_address=full_address,
                    )
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.get_discounted_price()
                    )
                    _notify_order_pending(order)
                    _remove_products_from_cart(request, [product.id])
                    return redirect(_build_vnpay_payment_url(request, order_number, total_amount))

                if payment_method == 'cash':
                    # Handle Cash On Delivery (COD) payment
                    from datetime import datetime
                    order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    subtotal = product.get_discounted_price() * quantity
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    total_amount = max(subtotal + 30000 - discount_amount, 0)
                    order = Order.objects.create(
                        user=request.user,
                        order_number=order_number,
                        total_amount=total_amount,
                        status='processing',
                        payment_method='cash',
                        customer_name=fullname,
                        customer_phone=phone,
                        customer_address=full_address,
                    )
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.get_discounted_price()
                    )
                    # Send success notification for COD orders
                    _notify_order_success(order)
                    _remove_products_from_cart(request, [product.id])
                    
                    # Get or create user profile
                    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                    user_profile.phone = phone
                    user_profile.address = full_address
                    user_profile.save()
                    
                    # Update user's name/email
                    parts = fullname.split(' ', 1)
                    request.user.first_name = parts[0] if len(parts) > 0 else ''
                    request.user.last_name = parts[1] if len(parts) > 1 else ''
                    request.user.email = email
                    request.user.save()
                    
                    messages.success(request, f'✅ Đặt hàng thành công! Mã đơn hàng: {order_number}. Chúng tôi sẽ liên hệ sớm để xác nhận.')
                    return redirect('store:order_success')

                # Create Order
                from datetime import datetime
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                subtotal = product.get_discounted_price() * quantity
                discount_amount = _calculate_voucher_discount(subtotal, voucher)
                total_amount = max(subtotal + 30000 - discount_amount, 0)
            
                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    total_amount=total_amount,
                    status='pending',
                    payment_method=payment_method,
                    customer_name=fullname,
                    customer_phone=phone,
                    customer_address=full_address
                )
            
                # Create OrderItem
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.get_discounted_price()
                )

                _notify_order_pending(order)
                _remove_products_from_cart(request, [product.id])
            
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
                subtotal = product.get_discounted_price() * quantity
                total_amount = max(subtotal + 30000 - discount_amount, 0)
                context = get_base_context(request)
                context.update({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'shipping_cost': 30000,
                    'total_amount': total_amount,
                    'discount_amount': discount_amount,
                    'voucher_code': voucher_code,
                    'voucher_error': voucher_error,
                    'form': form,
                })
                return render(request, 'store/checkout.html', context)
        else:
            # Form validation failed - display errors
            subtotal = product.get_discounted_price() * quantity
            total_amount = max(subtotal + 30000 - discount_amount, 0)
            context = get_base_context(request)
            context.update({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal,
                'shipping_cost': 30000,
                'total_amount': total_amount,
                'discount_amount': discount_amount,
                'voucher_code': voucher_code,
                'voucher_error': voucher_error,
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
    subtotal = product.get_discounted_price() * quantity
    total_amount = subtotal + 30000
    context.update({
        'product': product,
        'quantity': quantity,
        'subtotal': subtotal,
        'shipping_cost': 30000,
        'total_amount': total_amount,
        'discount_amount': 0,
        'voucher_code': '',
        'voucher_error': '',
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
    
    # Get list of selected product IDs from query parameter or POST payload
    selected_items_str = request.POST.get('items', '') if request.method == 'POST' else request.GET.get('items', '')
    selected_ids = set()
    if selected_items_str:
        selected_ids = set(int(id_str.strip()) for id_str in selected_items_str.split(',') if id_str.strip())
    
    # Get cart items - only selected ones
    cart_items = []
    total_amount = 0
    
    for product_id, cart_item in cart.items():
        # If items were specified, only include selected ones
        if selected_ids and int(product_id) not in selected_ids:
            continue
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
        voucher_code = ''
        voucher = None
        discount_amount = 0
        voucher_error = ''
        
        if form.is_valid():
            fullname = form.cleaned_data['fullname']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            address = form.cleaned_data['address']
            city = form.cleaned_data['city']
            district = form.cleaned_data['district']
            ward = form.cleaned_data['ward']
            payment_method = form.cleaned_data['payment_method']
            voucher_code = request.POST.get('voucher_code', '').strip().upper()
            if voucher_code:
                voucher, voucher_error = _validate_voucher_code(voucher_code)
                if voucher_error:
                    subtotal = total_amount
                    final_total = max(subtotal + 30000, 0)
                    context = get_base_context(request)
                    context.update({
                        'cart_items': cart_items,
                        'subtotal': subtotal,
                        'shipping_cost': 30000,
                        'total_amount': final_total,
                        'discount_amount': 0,
                        'voucher_code': voucher_code,
                        'voucher_error': voucher_error,
                        'form': form,
                        'selected_items': selected_items_str,
                    })
                    return render(request, 'store/checkout.html', context)

            # Combine address with district and ward for full address
            full_address = _build_full_address(request)
            
            try:
                # Handle bank transfer flow separately
                if payment_method == 'bank':
                    # Save pending order in session and redirect to bank selection
                    # Serialize cart_items into JSON-serializable dicts
                    serializable_items = []
                    for it in cart_items:
                        serializable_items.append({
                            'product_id': it['product'].id,
                            'quantity': it['quantity'],
                            'price': it['price'],
                        })

                    subtotal = total_amount
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    pending = {
                        'type': 'cart',
                        'cart_items': serializable_items,
                        'voucher_code': voucher_code,
                        'discount_amount': discount_amount,
                        'total_amount': max(subtotal + 30000 - discount_amount, 0),
                        'fullname': fullname,
                        'email': email,
                        'phone': phone,
                        'address': full_address,
                        'payment_method': payment_method,
                    }
                    request.session['pending_order'] = pending
                    _remove_products_from_cart(request, [it['product'].id for it in cart_items])
                    return redirect('store:bank_select')

                if payment_method == 'vietqr':
                    import random
                    order_code = f"ldm{random.randint(10000, 99999)}"
                    transfer_code = f"ldm{random.randint(10000, 99999)}"
                    subtotal = total_amount
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    total_amount = max(subtotal + 30000 - discount_amount, 0)
                    order = Order.objects.create(
                        user=request.user,
                        order_number=order_code,
                        total_amount=total_amount,
                        status='pending',
                        payment_method='vietqr',
                        customer_name=fullname,
                        customer_phone=phone,
                        customer_address=full_address,
                    )
                    for it in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=it['product'],
                            quantity=it['quantity'],
                            price=it['price'],
                        )
                    _notify_order_pending(order)
                    serializable_items = []
                    for it in cart_items:
                        serializable_items.append({
                            'product_id': it['product'].id,
                            'quantity': it['quantity'],
                            'price': it['price'],
                        })
                    pending = {
                        'type': 'cart',
                        'cart_items': serializable_items,
                        'voucher_code': voucher_code,
                        'discount_amount': discount_amount,
                        'order_code': order_code,
                        'transfer_code': transfer_code,
                        'order_id': order.id,
                        'total_amount': total_amount,
                        'fullname': fullname,
                        'email': email,
                        'phone': phone,
                        'address': full_address,
                        'payment_method': payment_method,
                    }
                    request.session['pending_order'] = pending
                    _remove_products_from_cart(request, [it['product'].id for it in cart_items])
                    return redirect('store:vietqr_page')

                if payment_method == 'vnpay':
                    subtotal = total_amount
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    total_amount = max(subtotal + 30000 - discount_amount, 0)
                    order_number = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                    order = Order.objects.create(
                        user=request.user,
                        order_number=order_number,
                        total_amount=total_amount,
                        status='pending',
                        payment_method='vnpay',
                        customer_name=fullname,
                        customer_phone=phone,
                        customer_address=full_address,
                    )
                    for it in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=it['product'],
                            quantity=it['quantity'],
                            price=it['price'],
                        )
                    _notify_order_pending(order)
                    _remove_products_from_cart(request, [it['product'].id for it in cart_items])
                    return redirect(_build_vnpay_payment_url(request, order_number, total_amount))

                if payment_method == 'cash':
                    # Handle Cash On Delivery (COD) payment for cart checkout
                    from datetime import datetime
                    order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    subtotal = total_amount
                    discount_amount = _calculate_voucher_discount(subtotal, voucher)
                    final_total = max(subtotal + 30000 - discount_amount, 0)
                    
                    order = Order.objects.create(
                        user=request.user,
                        order_number=order_number,
                        total_amount=final_total,
                        status='processing',
                        payment_method='cash',
                        customer_name=fullname,
                        customer_phone=phone,
                        customer_address=full_address
                    )

                    # Create OrderItems for all cart items
                    for item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=item['product'],
                            quantity=item['quantity'],
                            price=item['price']
                        )

                    # Send success notification for COD orders
                    _notify_order_success(order)
                    _remove_products_from_cart(request, [it['product'].id for it in cart_items])

                    # Get or create user profile
                    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                    user_profile.phone = phone
                    user_profile.address = full_address
                    user_profile.save()

                    # Update user's name/email
                    parts = fullname.split(' ', 1)
                    request.user.first_name = parts[0] if len(parts) > 0 else ''
                    request.user.last_name = parts[1] if len(parts) > 1 else ''
                    request.user.email = email
                    request.user.save()

                    messages.success(request, f'✅ Đặt hàng thành công! Mã đơn hàng: {order_number}. Chúng tôi sẽ liên hệ sớm để xác nhận.')
                    return redirect('store:order_success')

                # Create Order
                from datetime import datetime
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                subtotal = total_amount
                discount_amount = _calculate_voucher_discount(subtotal, voucher)
                final_total = max(subtotal + 30000 - discount_amount, 0)

                order = Order.objects.create(
                    user=request.user,
                    order_number=order_number,
                    total_amount=final_total,
                    status='pending',
                    payment_method=payment_method,
                    customer_name=fullname,
                    customer_phone=phone,
                    customer_address=full_address
                )

                # Create OrderItems for all cart items
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        quantity=item['quantity'],
                        price=item['price']
                    )

                _notify_order_pending(order)
                _remove_products_from_cart(request, [it['product'].id for it in cart_items])

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
                subtotal = total_amount
                final_total = max(subtotal + 30000 - discount_amount, 0)
                context = get_base_context(request)
                context.update({
                    'cart_items': cart_items,
                    'subtotal': subtotal,
                    'shipping_cost': 30000,
                    'total_amount': final_total,
                    'discount_amount': discount_amount,
                    'voucher_code': voucher_code,
                    'voucher_error': voucher_error,
                    'form': form,
                    'selected_items': selected_items_str,
                })
                return render(request, 'store/checkout.html', context)
        else:
            # Form validation failed - display errors
            subtotal = total_amount
            final_total = max(subtotal + 30000 - discount_amount, 0)
            context = get_base_context(request)
            context.update({
                'cart_items': cart_items,
                'subtotal': subtotal,
                'shipping_cost': 30000,
                'total_amount': final_total,
                'discount_amount': discount_amount,
                'voucher_code': voucher_code,
                'voucher_error': voucher_error,
                'form': form,
                'selected_items': selected_items_str,
            })
            return render(request, 'store/checkout.html', context)
    else:
        # GET request - initialize form with pre-filled data
        initial_data = {
            'email': request.user.email if request.user.is_authenticated else '',
        }
        form = CheckoutForm(initial=initial_data)
    
    subtotal = total_amount
    final_total = subtotal + 30000
    context = get_base_context(request)
    context.update({
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': 30000,
        'total_amount': final_total,
        'discount_amount': 0,
        'voucher_code': '',
        'voucher_error': '',
        'form': form,
        'selected_items': selected_items_str,
    })
    return render(request, 'store/checkout.html', context)


@login_required(login_url='store:login')
@require_GET
def validate_voucher(request):
    code = request.GET.get('code', '').strip()
    voucher, error = _validate_voucher_code(code)
    if error:
        return JsonResponse({'success': False, 'error': error})

    return JsonResponse({
        'success': True,
        'code': voucher.code,
        'discount_percent': voucher.discount_percent,
        'message': f'Voucher {voucher.code} áp dụng giảm {voucher.discount_percent}%'
    })


# ================== WISHLIST ==================
@login_required(login_url='store:login')
def wishlist(request):
    wishlist_obj, _ = Wishlist.objects.get_or_create(user=request.user)
    products = wishlist_obj.products.all()
    
    context = get_base_context(request)
    context['products'] = products
    return render(request, 'store/wishlist.html', context)


@login_required(login_url='store:login')
def wishlist_toggle(request):
    product_id = request.GET.get('product_id')
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        wishlist_obj, _ = Wishlist.objects.get_or_create(user=request.user)
        if wishlist_obj.products.filter(id=product.id).exists():
            wishlist_obj.products.remove(product)
            status = 'removed'
        else:
            wishlist_obj.products.add(product)
            status = 'added'
        
        return JsonResponse({
            'status': status,
            'wishlist_count': wishlist_obj.products.count()
        })
    
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
    context.update({
        'orders': orders,
        'page_type': 'list',
        'page_title': 'Tra cứu đơn hàng',
    })
    return render(request, 'store/orders.html', context)


@login_required(login_url='store:login')
def cancel_order(request, order_id):
    """Hủy đơn hàng (chỉ khi status = pending)"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.normalized_status == 'pending':
        order.status = 'cancelled'
        order.save()
        if request.session.get('pending_order', {}).get('order_id') == order.id:
            request.session.pop('pending_order', None)
        messages.success(request, '✅ Đơn hàng đã được hủy')
    else:
        messages.error(request, f'❌ Không thể hủy đơn hàng với trạng thái: {order.get_status_display()}')

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('store:order_tracking')


@login_required(login_url='store:login')
def confirm_received_order(request, order_id):
    """Xác nhận đã nhận hàng khi đơn đang ở trạng thái shipped."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status == 'shipped':
        order.status = 'delivered'
        order.save()
        messages.success(request, '✅ Cảm ơn bạn đã xác nhận đã nhận hàng.')
    else:
        messages.error(request, f'❌ Không thể xác nhận đơn với trạng thái: {order.get_status_display()}')
    
    return redirect('store:order_tracking')


@login_required(login_url='store:login')
def buy_again_order(request, order_id):
    """Thêm lại sản phẩm của đơn vào giỏ hàng để mua lại."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['delivered', 'cancelled']:
        messages.error(request, '❌ Chỉ có thể mua lại đơn đã hoàn thành hoặc đã hủy.')
        return redirect('store:order_tracking')

    cart = request.session.get('cart', {})
    for item in order.items.all():
        product_id = str(item.product.id)
        if product_id in cart and isinstance(cart[product_id], dict):
            cart[product_id]['quantity'] += item.quantity
        else:
            cart[product_id] = {
                'name': item.product.name,
                'price': item.price,
                'quantity': item.quantity,
                'image': item.product.image.url if item.product.image else ''
            }
    request.session['cart'] = cart
    messages.success(request, '🛒 Đã thêm sản phẩm của đơn vào giỏ hàng.')
    return redirect('store:cart_detail')


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


def vnpay_return(request):
    """Handle return from VNPAY after payment completion."""
    txn_ref = request.GET.get('vnp_TxnRef') or request.GET.get('vnp_TransactionNo')
    response_code = request.GET.get('vnp_ResponseCode')

    if response_code == '00':
        messages.success(request, '✅ Thanh toán VNPAY đã thành công. Cảm ơn bạn!')
        if txn_ref:
            order = Order.objects.filter(order_number=txn_ref).first()
            if order and order.status == 'pending':
                order.status = 'processing'
                order.save()
                _notify_order_success(order)
    else:
        messages.error(request, '❌ Thanh toán VNPAY chưa thành công hoặc đã bị hủy. Vui lòng kiểm tra lại.')

    return redirect('store:order_success')


def vnpay_ipn(request):
    """Placeholder endpoint for VNPAY IPN notifications."""
    return JsonResponse({'message': 'VNPAY IPN nhận thành công'})


@login_required(login_url='store:login')
def order_detail(request, order_id):
    """View order details - for both users and admin"""
    # Admin can see any order, regular users can only see their own
    if request.user.is_staff:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if shipping info can be edited
    can_edit_shipping = order.normalized_status in ['pending', 'processing']
    
    show_edit_form = can_edit_shipping and request.GET.get('edit') == '1'
    
    shipping_form = None
    if show_edit_form:
        if request.method == 'POST' and 'update_shipping' in request.POST:
            shipping_form = OrderShippingForm(request.POST, instance=order)
            if shipping_form.is_valid():
                shipping_form.save()
                messages.success(request, 'Thông tin giao hàng đã được cập nhật thành công!')
                return redirect(reverse('store:order_detail', args=[order.id]))
        else:
            shipping_form = OrderShippingForm(instance=order)
    
    context = get_base_context(request)
    context['order'] = order
    context['order_items'] = order.items.all()
    context['can_edit_shipping'] = can_edit_shipping
    context['show_edit_form'] = show_edit_form
    context['shipping_form'] = shipping_form
    context['page_type'] = 'detail'
    return render(request, 'store/orders.html', context)


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
    
    # Delivered orders are considered completed sales for revenue reporting
    delivered_orders = orders.filter(status='delivered')
    delivered_today = delivered_orders.filter(created_at__date=today)
    delivered_month = delivered_orders.filter(created_at__date__gte=month_start)
    delivered_year = delivered_orders.filter(created_at__year=today.year)

    # Calculate statistics
    total_products = all_products.count()
    total_users = users.count()
    total_categories = categories.count()
    total_orders = orders.count()
    total_revenue = sum(order.total_amount for order in delivered_orders) if delivered_orders else 0
    
    # Today revenue
    today_revenue = sum(order.total_amount for order in delivered_today) if delivered_today else 0
    
    # Average Order Value (AOV)
    if orders.exists():
        aov = total_revenue / total_orders
    else:
        aov = 0
    
    # Conversion Rate (dummy calculation, you can adjust)
    # This would need visitor data from analytics
    conversion_rate = 1.67
    
    # Monthly revenue calculation (only confirmed delivered orders)
    monthly_revenue = []
    for month in range(1, 13):
        month_start_date = today.replace(month=month, day=1)
        if month == 12:
            month_end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end_date = today.replace(month=month + 1, day=1)
        
        month_rev = sum(
            order.total_amount for order in delivered_orders 
            if month_start_date <= order.created_at.date() < month_end_date
        ) if delivered_orders else 0
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
            product = form.save()
            _sync_product_media(product, request)
            _sync_product_colors(product, request)
            _sync_product_ram_options(product, request)
            _sync_product_storage_options(product, request)
            _sync_product_specifications(product, request)
            messages.success(request, '✅ Thêm sản phẩm thành công')
            return redirect('store:admin_products')
    else:
        form = ProductForm()

    context = get_base_context(request)
    context['form'] = form
    context['title'] = 'Thêm sản phẩm mới'
    context['product_media'] = []
    context['product_colors'] = []
    context['product_ram_options'] = []
    context['product_storage_options'] = []
    context['product_specs'] = []
    context['spec_category_order'] = ''
    return render(request, 'store/product_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def dashboard_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    specs = product.specs.all() if hasattr(product, 'specs') else []

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            _sync_product_media(product, request)
            _sync_product_colors(product, request)
            _sync_product_ram_options(product, request)
            _sync_product_storage_options(product, request)
            _sync_product_specifications(product, request)
            messages.success(request, '✅ Cập nhật sản phẩm thành công')
            return redirect('store:admin_products')
    else:
        form = ProductForm(instance=product)

    context = get_base_context(request)
    context.update({
        'form': form,
        'product': product,
        'product_media': product.media_items.all(),
        'product_colors': product.colors.all(),
        'product_ram_options': product.ram_options.all(),
        'product_storage_options': product.storage_options.all(),
        'product_specs': product.specs.all(),
        'specs': specs,
        'title': f'Chỉnh sửa sản phẩm: {product.name}',
        'spec_category_order': product.spec_category_order or ''
    })
    return render(request, 'store/product_form.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def dashboard_edit_product_media(request, pk):
    product = get_object_or_404(Product, pk=pk)
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('store:admin_media_library')

    if request.method == 'POST':
        _sync_product_media(product, request)
        messages.success(request, '✅ Cập nhật Media sản phẩm thành công')

        if product.media_items.exists() and product.pending_media:
            product.pending_media = False
            product.save(update_fields=['pending_media'])

        return redirect(resolve_url(next_url))

    context = get_base_context(request)
    context.update({
        'product': product,
        'product_media': product.media_items.all(),
        'title': f'Thư viện Media: {product.name}',
        'back_url': resolve_url(next_url),
    })
    return render(request, 'admin/admin_media.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def dashboard_edit_product_specs(request, pk):
    product = get_object_or_404(Product, pk=pk)
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('store:admin_specifications')

    if request.method == 'POST':
        _sync_product_specifications(product, request)
        messages.success(request, '✅ Cập nhật Thông số kỹ thuật thành công')
        return redirect(resolve_url(next_url))

    context = get_base_context(request)
    context.update({
        'product': product,
        'product_specs': product.specs.all(),
        'spec_category_order': product.spec_category_order or '',
        'title': f'Thông số kỹ thuật: {product.name}',
        'back_url': resolve_url(next_url),
    })
    return render(request, 'admin/admin_specification.html', context)


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
def user_list(request):
    """List all users and handle user create/edit"""
    users = User.objects.all().order_by('-date_joined')
    context = get_base_context(request)
    context['users'] = users
    
    # Check if we need to show form
    show_form = request.GET.get('add') == 'true' or request.GET.get('edit')
    edit_user = None
    form = None
    
    if request.method == 'POST':
        edit_user_id = request.POST.get('edit_user_id')
        
        if edit_user_id:
            # Edit existing user
            edit_user = get_object_or_404(User, pk=edit_user_id)
            form = UserManagementForm(request.POST, instance=edit_user)
        else:
            # Create new user
            form = UserManagementForm(request.POST)
            # Validate password is not empty for new users
            if not request.POST.get('password'):
                form.add_error('password', '❌ Mật khẩu không được để trống khi tạo tài khoản mới')
        
        if form.is_valid():
            form.save()
            if edit_user_id:
                messages.success(request, '✅ Cập nhật thành viên thành công')
            else:
                messages.success(request, '✅ Tạo thành viên thành công')
            return redirect('store:user_list')
        else:
            show_form = True
    
    elif show_form and request.GET.get('edit'):
        # Load user for edit
        edit_user = get_object_or_404(User, pk=request.GET.get('edit'))
        form = UserManagementForm(instance=edit_user)
    elif show_form:
        # Create new user form
        form = UserManagementForm()
    
    context['show_form'] = show_form
    context['form'] = form
    context['edit_user'] = edit_user
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

    users = User.objects.all().order_by('-date_joined')
    context = get_base_context(request)
    context.update({
        'users': users,
        'show_form': True,
        'form': form,
        'edit_user': user,
    })
    return render(request, 'admin/admin_users.html', context)


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
                'media_type': 'video' if b.is_video else 'image',
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
    banners = Banner.objects.filter(_banner_media_type_filter('image')).order_by('banner_id')
    context = get_base_context(request)
    context['banner_mode'] = 'image'
    context['page_title_text'] = 'Quản Lý Image Banner'
    context['page_subtitle_text'] = 'Danh sách image banner'
    context['banners'] = banners
    context['next_banner_id'] = _get_next_banner_id()
    return render(request, 'store/banner_list.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def video_banner_admin_list(request):
    """Admin list all video banners"""
    banners = Banner.objects.filter(_banner_media_type_filter('video')).order_by('banner_id')
    context = get_base_context(request)
    context['banner_mode'] = 'video'
    context['page_title_text'] = 'Quản Lý Videos Banner'
    context['page_subtitle_text'] = 'Danh sách video banner'
    context['banners'] = banners
    context['next_banner_id'] = _get_next_banner_id()
    return render(request, 'store/banner_list.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_add(request):
    """Add a new banner"""
    if request.method == 'POST':
        post_data = request.POST.copy()
        if not post_data.get('banner_id'):
            post_data['banner_id'] = str(_get_next_banner_id())

        form = BannerForm(post_data, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data.get('image')
            if uploaded_file and not _is_image_upload(uploaded_file):
                return JsonResponse({'success': False, 'errors': {'image': ['❌ Chỉ chấp nhận ảnh cho Banner']}})

            form.save()
            return JsonResponse({'success': True, 'message': '✅ Thêm banner thành công'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_import(request):
    """Import static banner images into the banner database"""
    if request.method == 'POST':
        imported, skipped = _import_static_images_to_banner()
        return JsonResponse({
            'success': True,
            'message': f'✅ Đã tải {imported} ảnh vào Banner, bỏ qua {skipped} file đã tồn tại.'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def video_banner_add(request):
    """Add a new video banner"""
    if request.method == 'POST':
        post_data = request.POST.copy()
        if not post_data.get('banner_id'):
            post_data['banner_id'] = str(_get_next_banner_id())

        form = BannerForm(post_data, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data.get('image')
            if uploaded_file and not _is_video_upload(uploaded_file):
                return JsonResponse({'success': False, 'errors': {'image': ['❌ Chỉ chấp nhận video cho Videos Banner']}})

            form.save()
            return JsonResponse({'success': True, 'message': '✅ Thêm video banner thành công'})

        return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def video_banner_import(request):
    """Import static videos into the banner database for management"""
    if request.method == 'POST':
        imported, skipped = _import_static_videos_to_banner()
        return JsonResponse({
            'success': True,
            'message': f'✅ Đã tải {imported} video vào Videos Banner, bỏ qua {skipped} file đã tồn tại.'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def banner_replace(request):
    """Replace/update existing banner"""
    if request.method == 'POST':
        banner_id = request.POST.get('banner_id')
        
        try:
            banner = Banner.objects.get(banner_id=banner_id)

            form = BannerForm(request.POST, request.FILES, instance=banner)
            form.fields['image'].required = False

            if form.is_valid():
                new_media = form.cleaned_data.get('image')
                if new_media and not _is_image_upload(new_media):
                    return JsonResponse({'success': False, 'errors': {'image': ['❌ Chỉ chấp nhận ảnh cho Banner']}})

                banner.banner_id = form.cleaned_data['banner_id']
                banner.is_active = form.cleaned_data['is_active']

                if new_media:
                    if banner.image:
                        banner.image.delete(save=False)
                    banner.image = new_media

                banner.save()
                return JsonResponse({'success': True, 'message': '✅ Cập nhật banner thành công'})

            return JsonResponse({'success': False, 'errors': form.errors})
        except Banner.DoesNotExist:
            return JsonResponse({'success': False, 'message': '❌ Không tìm thấy banner'}, status=404)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def video_banner_replace(request):
    """Replace/update existing video banner"""
    if request.method == 'POST':
        banner_id = request.POST.get('banner_id')

        try:
            banner = Banner.objects.get(banner_id=banner_id)

            form = BannerForm(request.POST, request.FILES, instance=banner)
            form.fields['image'].required = False

            if form.is_valid():
                new_media = form.cleaned_data.get('image')
                if new_media and not _is_video_upload(new_media):
                    return JsonResponse({'success': False, 'errors': {'image': ['❌ Chỉ chấp nhận video cho Videos Banner']}})

                banner.banner_id = form.cleaned_data['banner_id']
                banner.is_active = form.cleaned_data['is_active']

                if new_media:
                    if banner.image:
                        banner.image.delete(save=False)
                    banner.image = new_media

                banner.save()
                return JsonResponse({'success': True, 'message': '✅ Cập nhật video banner thành công'})

            return JsonResponse({'success': False, 'errors': form.errors})
        except Banner.DoesNotExist:
            return JsonResponse({'success': False, 'message': '❌ Không tìm thấy video banner'}, status=404)

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
                banner.image.delete(save=False)
            banner.delete()
            return JsonResponse({'success': True, 'message': '✅ Xoá banner thành công'})
        except Banner.DoesNotExist:
            return JsonResponse({'success': False, 'message': '❌ Không tìm thấy banner'}, status=404)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def video_banner_delete(request):
    """Delete a video banner"""
    if request.method == 'POST':
        banner_id = request.POST.get('banner_id')

        try:
            banner = Banner.objects.get(banner_id=banner_id)
            if banner.image:
                banner.image.delete(save=False)
            banner.delete()
            return JsonResponse({'success': True, 'message': '✅ Xoá video banner thành công'})
        except Banner.DoesNotExist:
            return JsonResponse({'success': False, 'message': '❌ Không tìm thấy video banner'}, status=404)

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
def toggle_wishlist_ajax(request):
    """AJAX endpoint to toggle product in wishlist"""
    if not request.user.is_authenticated:
        referer = request.META.get('HTTP_REFERER', '/')
        return JsonResponse({
            'success': False,
            'error': 'Vui lòng đăng nhập để thêm vào wishlist',
            'login_required': True,
            'login_url': f"{settings.LOGIN_URL}?next={referer}"
        }, status=401)

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
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng',
            'login_required': True,
            'login_url': f"{settings.LOGIN_URL}?next=/cart/"
        }, status=401)

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
                if isinstance(cart[product_key], dict):
                    cart[product_key]['quantity'] += quantity
                else:
                    cart[product_key] = {
                        'name': product.name,
                        'price': product.get_discounted_price(),
                        'quantity': cart[product_key] + quantity,
                        'image': product.image.url if product.image else ''
                    }
            else:
                default_color = product.colors.order_by('sort_order', 'id').first()
                default_color_name = default_color.name if default_color else ''
                default_color_price = default_color.price_delta if default_color else 0
                default_color_image = default_color.image.url if default_color and default_color.image else ''
                default_ram = product.ram or ''
                default_storage = product.rom or ''
                base_price = product.get_discounted_price()
                cart[product_key] = {
                    'name': product.name,
                    'price': base_price + default_color_price,
                    'quantity': quantity,
                    'image': default_color_image or (product.image.url if product.image else ''),
                    'color': default_color_name,
                    'color_price_delta': default_color_price,
                    'color_image': default_color_image,
                    'ram': default_ram,
                    'ram_price_delta': 0,
                    'storage': default_storage,
                    'storage_price_delta': 0,
                }
            request.session['cart'] = cart
            
            return JsonResponse({
                'success': True,
                'message': f'✅ Thêm {quantity} sản phẩm vào giỏ hàng',
                'cart_count': sum(item['quantity'] for item in cart.values() if isinstance(item, dict)),
                'cart_total': sum((item['price'] * item['quantity']) for item in cart.values() if isinstance(item, dict))
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
        'is_paginated': orders_page.has_other_pages(),
        'page_obj': orders_page,
    })
    return render(request, 'admin/admin_orders.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_vouchers(request):
    from django.core.paginator import Paginator

    vouchers = Voucher.objects.all().order_by('-created_at')
    paginator = Paginator(vouchers, 20)
    page_number = request.GET.get('page', 1)
    vouchers_page = paginator.get_page(page_number)

    context = get_base_context(request)
    context.update({
        'vouchers': vouchers_page,
        'is_paginated': vouchers_page.has_other_pages(),
        'page_obj': vouchers_page,
        'show_form': False,
    })
    return render(request, 'admin/admin_vouchers.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def voucher_create(request):
    if request.method == 'POST':
        form = VoucherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Thêm voucher thành công')
            return redirect('store:admin_vouchers')
    else:
        form = VoucherForm()

    context = get_base_context(request)
    context.update({
        'form': form,
        'title': 'Thêm voucher mới',
        'show_form': True,
        'form_action': 'store:voucher_create',
        'submit_label': 'Tạo voucher'
    })
    return render(request, 'admin/admin_vouchers.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def voucher_edit(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    if request.method == 'POST':
        form = VoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cập nhật voucher thành công')
            return redirect('store:admin_vouchers')
    else:
        form = VoucherForm(instance=voucher)

    context = get_base_context(request)
    context.update({
        'form': form,
        'voucher': voucher,
        'title': f'Chỉnh sửa voucher: {voucher.code}',
        'show_form': True,
        'form_action': 'store:voucher_edit',
        'submit_label': 'Cập nhật voucher'
    })
    return render(request, 'admin/admin_vouchers.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def voucher_delete(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    voucher.delete()
    messages.success(request, '🗑️ Đã xoá voucher')
    return redirect('store:admin_vouchers')


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_media_library(request):
    products = Product.objects.annotate(
        media_count=Count('media_items'),
        image_count=Count('media_items', filter=Q(media_items__media_type='image')),
        video_count=Count('media_items', filter=Q(media_items__media_type='video'))
    ).order_by('-created_at')

    context = get_base_context(request)
    context.update({
        'products': products,
    })
    return render(request, 'admin/admin_media.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_media_add(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        if product_id and product_id.isdigit():
            product = get_object_or_404(Product, pk=int(product_id))
            if not product.pending_media and not product.media_items.exists():
                product.pending_media = True
                product.save(update_fields=['pending_media'])
        return redirect('store:admin_media_library')

    products_without_media = Product.objects.annotate(media_count=Count('media_items')).filter(media_count=0).order_by('created_at')

    context = get_base_context(request)
    context.update({
        'products_without_media': products_without_media,
        'back_url': reverse('store:admin_media_library'),
    })
    return render(request, 'admin/admin_media.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_specifications(request):
    products = Product.objects.annotate(spec_count=Count('specs')).order_by('-created_at')

    context = get_base_context(request)
    context.update({
        'products': products,
    })
    return render(request, 'admin/admin_specification.html', context)


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def admin_spec_add(request):
    if request.method == 'POST':
        messages.info(request, 'Chức năng thêm Thông số kỹ thuật sẽ sớm có.')
    return redirect('store:admin_specifications')


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
            
            valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'expired', 'cancelled']
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


@login_required(login_url='store:login')
@user_passes_test(is_admin, login_url='store:login')
def approve_order(request):
    """Approve a pending VietQR order and mark it completed."""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            order_id = data.get('order_id')
            order = get_object_or_404(Order, id=order_id)

            if order.status != 'pending':
                return JsonResponse({'success': False, 'error': 'Đơn hàng không ở trạng thái chờ xác nhận.'})

            order.status = 'processing'
            order.save()
            _notify_order_success(order)
            return JsonResponse({'success': True, 'message': 'Đơn hàng đã được duyệt và chuyển sang trạng thái Đã đặt hàng.'})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Đơn hàng không tồn tại'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Phương thức không hợp lệ'}, status=400)


# ================== PASSWORD RESET ==================
def forgot_password_view(request):
    """Handle forgot password requests"""
    from .models import PasswordResetToken
    import secrets
    from django.utils import timezone
    from datetime import timedelta

    context = get_base_context(request)
    context['auth_type'] = 'forgot_password'
    context['show_code_step'] = False
    context['email'] = ''
    context['email_error'] = ''
    context['code_error'] = ''
    context['success_message'] = ''
    context['token'] = ''

    if request.method == 'POST':
        action = request.POST.get('action', 'send_email')

        if action == 'send_email':
            email = request.POST.get('email', '').strip()
            context['email'] = email

            if not email:
                context['email_error'] = '❌ Vui lòng nhập email'
                return render(request, 'store/auth.html', context)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                context['email_error'] = '❌ Email không hợp lệ'
                return render(request, 'store/auth.html', context)

            token = secrets.token_urlsafe(32)
            code = ''.join(secrets.choice('0123456789') for _ in range(6))
            expires_at = timezone.now() + timedelta(hours=24)

            PasswordResetToken.objects.create(
                user=user,
                token=token,
                code=code,
                expires_at=expires_at
            )

            from django.core.mail import send_mail
            subject = '🔐 Mã xác nhận đặt lại mật khẩu - Mobile Store'
            message = f'''
Xin chào {user.first_name or user.username},

Bạn vừa yêu cầu đặt lại mật khẩu.

Mã xác nhận của bạn là: {code}

Nhập mã này vào trang quên mật khẩu để tiếp tục đặt lại mật khẩu.

Nếu bạn không yêu cầu, hãy bỏ qua email này.

---
Mobile Store Team
            '''

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            context['show_code_step'] = True
            context['success_message'] = '✅ Mã xác nhận đã được gửi đến email của bạn. Vui lòng kiểm tra và nhập mã.'
            context['token'] = token
            return render(request, 'store/auth.html', context)

        if action == 'verify_code':
            token = request.POST.get('token', '').strip()
            code = request.POST.get('code', '').strip()
            context['show_code_step'] = True
            context['token'] = token
            context['email'] = request.POST.get('email', '').strip()

            if not code:
                context['code_error'] = '❌ Vui lòng nhập mã xác nhận'
                return render(request, 'store/auth.html', context)

            try:
                reset_token = PasswordResetToken.objects.get(token=token)
            except PasswordResetToken.DoesNotExist:
                context['code_error'] = '❌ Mã không hợp lệ'
                return render(request, 'store/auth.html', context)

            if not reset_token.is_valid():
                context['code_error'] = '❌ Mã đã hết hạn hoặc không hợp lệ'
                return render(request, 'store/auth.html', context)

            if not reset_token.is_code_valid(code):
                context['code_error'] = '❌ Mã không hợp lệ'
                return render(request, 'store/auth.html', context)

            reset_token.is_email_verified = True
            reset_token.save()
            return redirect('store:reset_password', token=token)

    return render(request, 'store/auth.html', context)


def reset_password_view(request, token):
    """Handle password reset with token"""
    from .models import PasswordResetToken
    
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        
        if not reset_token.is_valid() or not reset_token.is_email_verified:
            messages.error(request, '❌ Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn')
            return redirect('store:login')
        
        if request.method == 'POST':
            password1 = request.POST.get('password1', '').strip()
            password2 = request.POST.get('password2', '').strip()
            
            if not password1 or not password2:
                messages.error(request, '❌ Vui lòng nhập mật khẩu')
                return redirect('store:reset_password', token=token)
            
            if password1 != password2:
                messages.error(request, '❌ Mật khẩu không khớp')
                return redirect('store:reset_password', token=token)
            
            if len(password1) < 8:
                messages.error(request, '❌ Mật khẩu phải có ít nhất 8 ký tự')
                return redirect('store:reset_password', token=token)
            
            # Set new password
            user = reset_token.user
            user.set_password(password1)
            user.save()
            
            # Mark token as used
            reset_token.is_used = True
            reset_token.save()
            
            messages.success(request, '✅ Mật khẩu đã được đặt lại thành công! Vui lòng đăng nhập.')
            return redirect('store:login')
        
        context = get_base_context(request)
        context['auth_type'] = 'reset_password'
        context['token'] = token
        return render(request, 'store/auth.html', context)
        
    except PasswordResetToken.DoesNotExist:
        messages.error(request, '❌ Link đặt lại mật khẩu không hợp lệ')
        return redirect('store:login')

