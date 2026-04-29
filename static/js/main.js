/**
 * MOBILE STORE - Main.js
 * Core utilities and helper functions for the application
 */

// ====== TOAST NOTIFICATIONS ======
const LDMToast = {
    show: function(message, type = 'success') {
        let container = document.querySelector('.ldm-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'ldm-toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `ldm-toast ldm-toast-${type}`;
        
        const icon = type === 'success' 
            ? '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
            : '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        
        toast.innerHTML = `
            <span class="ldm-toast-icon">${icon}</span>
            <span class="ldm-toast-text">${message}</span>
        `;

        container.appendChild(toast);
        toast.offsetHeight;
        toast.classList.add('ldm-toast-show');

        setTimeout(() => {
            toast.classList.remove('ldm-toast-show');
            toast.classList.add('ldm-toast-hide');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    success: function(message) {
        this.show(message, 'success');
    },

    error: function(message) {
        this.show(message, 'error');
    }
};

window.LDMToast = LDMToast;
window.ldmToast = LDMToast;

// ====== CONFIRMATION DIALOGS ======
const LDMConfirm = {
    show: function(message, onConfirm, onCancel = null) {
        const modal = document.createElement('div');
        modal.className = 'ldm-modal active';
        modal.innerHTML = `
            <div class="ldm-modal-content">
                <h3 class="ldm-modal-title">Xác nhận</h3>
                <p class="ldm-modal-text">${message}</p>
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button class="ldm-btn ldm-btn-cancel" style="background: #E0E0E0; color: #333;">Hủy</button>
                    <button class="ldm-btn ldm-btn-primary">Xác nhận</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const confirmBtn = modal.querySelector('.ldm-btn-primary');
        const cancelBtn = modal.querySelector('.ldm-btn-cancel');

        confirmBtn.addEventListener('click', () => {
            modal.remove();
            if (onConfirm) onConfirm();
        });

        cancelBtn.addEventListener('click', () => {
            modal.remove();
            if (onCancel) onCancel();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                if (onCancel) onCancel();
            }
        });
    }
};

window.LDMConfirm = LDMConfirm;

// ====== UTILITY FUNCTIONS ======

/**
 * Format number as Vietnamese currency
 */
function formatPrice(price) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        minimumFractionDigits: 0,
    }).format(price);
}

/**
 * Get CSRF token from cookies
 */
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

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Make AJAX request
 */
function ajaxRequest(method, url, data = null, onSuccess = null, onError = null) {
    const options = {
        method: method,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    if (method === 'POST' && data) {
        if (data instanceof FormData) {
            options.body = data;
        } else {
            options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
            options.body = new URLSearchParams(data);
        }
    }

    fetch(url, options)
        .then(response => response.json())
        .then(result => {
            if (onSuccess) onSuccess(result);
        })
        .catch(error => {
            console.error('Error:', error);
            if (onError) onError(error);
        });
}

/**
 * Format date as Vietnamese format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Show loading indicator
 */
function showLoading(selector) {
    const element = document.querySelector(selector);
    if (element) {
        element.innerHTML = '<span class="spinner"></span>';
    }
}

/**
 * Hide loading indicator
 */
function hideLoading(selector) {
    const element = document.querySelector(selector);
    if (element) {
        element.innerHTML = '';
    }
}

/**
 * Scroll to element
 */
function scrollToElement(selector, offset = 0) {
    const element = document.querySelector(selector);
    if (element) {
        const elementPosition = element.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({
            top: elementPosition,
            behavior: 'smooth'
        });
    }
}

/**
 * Animate element
 */
function animateElement(element, animationClass, duration = 300) {
    element.classList.add(animationClass);
    setTimeout(() => {
        element.classList.remove(animationClass);
    }, duration);
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Lazy load images
 */
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize lazy loading
    lazyLoadImages();

    // Add event delegation for common interactions
    document.addEventListener('click', function(e) {
        // Handle toggle buttons
        if (e.target.closest('[data-toggle]')) {
            const target = e.target.closest('[data-toggle]');
            const selector = target.dataset.toggle;
            const element = document.querySelector(selector);
            if (element) {
                element.classList.toggle('active');
            }
        }
    });
});

// ====== CART UI FUNCTIONS ======

/**
 * Update cart UI with new information
 */
function updateCartUI(cartCount, cartTotal) {
    // Update cart count in header
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
        cartCountElement.textContent = cartCount;
        // Show/hide the count badge
        if (cartCount > 0) {
            cartCountElement.style.display = 'inline-flex';
        } else {
            cartCountElement.style.display = 'none';
        }
    }
    
    // Update cart total in sidebar/header if it exists
    const cartTotalElement = document.getElementById('cart-total');
    if (cartTotalElement) {
        cartTotalElement.textContent = formatPrice(cartTotal);
    }
}

// Export functions
window.formatPrice = formatPrice;
window.getCookie = getCookie;
window.debounce = debounce;
window.ajaxRequest = ajaxRequest;
window.formatDate = formatDate;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.scrollToElement = scrollToElement;
window.animateElement = animateElement;
window.isInViewport = isInViewport;
window.lazyLoadImages = lazyLoadImages;
window.updateCartUI = updateCartUI;

