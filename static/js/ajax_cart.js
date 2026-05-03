/**
 * AJAX Cart Operations
 * Handles add to cart, update quantity, remove from cart via AJAX
 */

// Add to cart via AJAX
function addToCartAjax(productId, quantity = 1, params) {
    params = params || {};
    const loginUrl = window.AUTH_ENDPOINTS && window.AUTH_ENDPOINTS.login;
    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('quantity', quantity);
    if (params.storage) formData.append('storage', params.storage);
    if (params.ram) formData.append('ram', params.ram);
    if (params.color) formData.append('color', params.color);
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch(window.API_ENDPOINTS.addToCart, {
        method: 'POST',
        body: formData,
    })
    .then(async response => ({ ok: response.ok, status: response.status, data: await response.json() }))
    .then(({ ok, status, data }) => {
        if (data.success) {
            showToast(data.message, 'success');
            updateCartUI(data.cart_count, data.cart_total);
        } else if (status === 401 || data.login_required) {
            showToast(data.error || 'Vui lòng đăng nhập để thêm vào giỏ hàng', 'error');
            if (loginUrl) {
                window.location.href = data.login_url || loginUrl;
            }
        } else {
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Lỗi khi thêm vào giỏ hàng', 'error');
    });
}

// Update cart quantity via AJAX
function updateCartQuantityAjax(cartKey, quantity) {
    const formData = new FormData();
    formData.append('cart_key', cartKey);
    formData.append('quantity', quantity);
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch(window.API_ENDPOINTS.updateCartQuantity, {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            updateCartUI(data.cart_count, data.cart_total);
            // Update row total if in cart page
            const itemTotal = document.querySelector(`[data-cart-key="${cartKey}"] .item-total`);
            if (itemTotal) {
                itemTotal.textContent = formatPrice(data.item_total);
            }
        } else {
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Lỗi khi cập nhật giỏ hàng', 'error');
    });
}

// Remove from cart via AJAX
function removeFromCartAjax(cartKey) {
    if (!confirm('Bạn chắc chắn muốn xóa sản phẩm này?')) return;

    const formData = new FormData();
    formData.append('cart_key', cartKey);
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch(window.API_ENDPOINTS.removeFromCart, {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            updateCartUI(data.cart_count, data.cart_total);
            // Remove row from cart page
            const row = document.querySelector(`[data-cart-key="${cartKey}"]`);
            if (row) {
                row.style.opacity = '0.5';
                setTimeout(() => { row.remove(); }, 300);
            }
        } else {
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Lỗi khi xóa khỏi giỏ hàng', 'error');
    });
}

// Update cart UI (header badges, totals)
function updateCartUI(cartCount, cartTotal) {
    // Update cart count in header
    const cartBadge = document.querySelector('.ldm-header-cart-badge');
    if (cartBadge) {
        cartBadge.textContent = cartCount;
        cartBadge.style.display = cartCount > 0 ? 'inline-block' : 'none';
    }

    // Update cart total
    const totalDisplay = document.querySelector('.cart-total-amount');
    if (totalDisplay) {
        totalDisplay.textContent = formatPrice(cartTotal);
    }
}

// Helper: Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper: Format price
function formatPrice(price) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        minimumFractionDigits: 0,
    }).format(price);
}

// Show toast notification (requires toast.js)
function showToast(message, type = 'info') {
    if (window.LDMToast && typeof window.LDMToast.show === 'function') {
        window.LDMToast.show(message, type);
    } else {
        alert(message);
    }
}

// Initialize event listeners on page load
document.addEventListener('DOMContentLoaded', function() {
    // Quantity input change
    document.querySelectorAll('.cart-quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const cartKey = this.dataset.cartKey;
            const quantity = parseInt(this.value) || 1;
            updateCartQuantityAjax(cartKey, quantity);
        });
    });

    // Remove buttons
    document.querySelectorAll('.btn-remove-cart').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const cartKey = this.dataset.cartKey;
            removeFromCartAjax(cartKey);
        });
    });
});

