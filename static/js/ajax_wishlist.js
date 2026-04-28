/**
 * AJAX Wishlist Operations
 * Handles add/remove from wishlist via AJAX
 */

// Toggle wishlist  via AJAX
function toggleWishlistAjax(productId, button = null) {
    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch('/ajax/wishlist/toggle/', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            updateWishlistUI(productId, data.is_added, button, data.wishlist_count);
        } else {
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Lỗi khi thay đổi wishlist', 'error');
    });
}

// Update wishlist UI
function updateWishlistUI(productId, isAdded, button, wishlistCount) {
    // If button not provided, find it by data-product-id
    if (!button) {
        button = document.querySelector(`button[data-product-id="${productId}"]`);
    }

    if (button) {
        const svg = button.querySelector('svg');
        if (isAdded) {
            // Added to wishlist - change to RED
            button.classList.add('active');
            button.style.color = '#ef4444';
            
            // Fill SVG with red
            if (svg) {
                svg.style.fill = '#ef4444';
                svg.style.stroke = '#ef4444';
            }
        } else {
            // Removed from wishlist - change back to BLUE
            button.classList.remove('active');
            button.style.color = '#667eea';
            
            // Outline SVG in blue
            if (svg) {
                svg.style.fill = 'none';
                svg.style.stroke = '#667eea';
            }
        }
    }

    // Update wishlist count in header
    const wishlistBadge = document.querySelector('.ldm-header-wishlist-badge');
    if (wishlistBadge) {
        wishlistBadge.textContent = wishlistCount;
        wishlistBadge.style.display = wishlistCount > 0 ? 'inline-block' : 'none';
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

// Show toast notification
function showToast(message, type = 'info') {
    if (window.LDMToast && typeof window.LDMToast.show === 'function') {
        window.LDMToast.show(message, type);
    } else {
        alert(message);
    }
}

// Initialize event listeners on page load
document.addEventListener('DOMContentLoaded', function() {
    // Wishlist buttons - home page style
    document.querySelectorAll('.wishlist-btn-inline').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            toggleWishlistAjax(productId, this);
        });
    });
    
    // Wishlist buttons - other pages style
    document.querySelectorAll('.btn-wishlist').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            toggleWishlistAjax(productId, this);
        });
    });
});

