/**
 * AJAX Cart Operations
 * Handles add to cart, update quantity, remove from cart via AJAX
 */

// Add to cart via AJAX
function addToCartAjax(productId, quantity = 1) {
    const loginUrl = window.AUTH_ENDPOINTS && window.AUTH_ENDPOINTS.login;
    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('quantity', quantity);
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
        } else if (status === 401 || data.login_required || !ok) {
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
function updateCartQuantityAjax(productId, quantity) {
    const formData = new FormData();
    formData.append('product_id', productId);
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
            const itemTotal = document.querySelector(`[data-product-id="${productId}"] .item-total`);
            if (itemTotal) {
                itemTotal.textContent = formatPrice(data.item_total)  ;
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
function removeFromCartAjax(productId) {
    if (!confirm('Bạn chắc chắn muốn xóa sản phẩm này?')) return;

    const formData = new FormData();
    formData.append('product_id', productId);
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
            const row = document.querySelector(`[data-product-id="${productId}"]`);
            if (row) {
                row.style.opacity = '0.5';
                setTimeout(() => {
                    row.remove();
                    // Reload if cart is empty
                    if (document.querySelectorAll('[data-product-id]').length === 0) {
                        location.reload();
                    }
                }, 300);
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
            const productId = this.dataset.productId;
            const quantity = parseInt(this.value) ||1;
            updateCartQuantityAjax(productId, quantity);
        });
    });

    // Remove buttons
    document.querySelectorAll('.btn-remove-cart').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            removeFromCartAjax(productId);
        });
    });
});

