/* ==================== Wishlist Functions ==================== */

/* ==================== Badge wishlist ==================== */
function updateWishlistBadge(count) {
    var badge = document.getElementById('qh-wishlist-count');
    if (badge) badge.textContent = count;
}

/* ==================== Toggle wishlist ==================== */
function toggleWishlist(productId, buttonElement) {
    const url = `/wishlist/toggle/?product_id=${productId}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'added') {
                buttonElement.classList.add('active');
                buttonElement.innerHTML = '❤️';
                showToast('Đã thêm vào danh sách yêu thích', 'success');
                // Reload page to show wishlist section
                setTimeout(() => {
                    location.reload();
                }, 800);
            } else {
                buttonElement.classList.remove('active');
                buttonElement.innerHTML = '🤍';
                showToast('Đã bỏ khỏi danh sách yêu thích', 'info');
                // Reload page to update wishlist section
                setTimeout(() => {
                    location.reload();
                }, 800);
            }

            // Update badge
            updateWishlistBadge(data.wishlist_count);
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Lỗi khi cập nhật danh sách yêu thích', 'error');
        });
}

/* ==================== Remove from wishlist ==================== */
function removeFromWishlist(event, productId) {
    event.preventDefault();
    const url = `/wishlist/toggle/?product_id=${productId}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Reload page to update wishlist
            location.reload();
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Lỗi khi cập nhật danh sách yêu thích', 'error');
        });
}