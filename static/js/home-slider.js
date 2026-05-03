/* =====================================================
   HOME PAGE JAVASCRIPT
   Video Carousel & Wishlist functionality
   ===================================================== */

// Video Carousel Autoplay
(function() {
    const carousel = document.getElementById('videoCarousel');
    if (!carousel) return;

    const videos = Array.from(carousel.querySelectorAll('.ldm-video-item'));
    if (videos.length <= 1) return;

    const prevBtn = document.getElementById('videoPrevBtn');
    const nextBtn = document.getElementById('videoNextBtn');

    let currentVideoIndex = 0;
    let autoplayTimer = null;
    const autoplayInterval = 8000; // 8 seconds per video

    function showVideo(index) {
        videos.forEach((video, i) => {
            video.classList.toggle('active', i === index);
            if (i === index) {
                video.style.display = 'block';
                video.play().catch(() => {});
            } else {
                video.style.display = 'none';
                video.pause();
            }
        });
        currentVideoIndex = index;
    }

    function nextVideo() {
        const nextIndex = (currentVideoIndex + 1) % videos.length;
        showVideo(nextIndex);
    }

    function previousVideo() {
        const prevIndex = (currentVideoIndex - 1 + videos.length) % videos.length;
        showVideo(prevIndex);
    }

    function startAutoplay() {
        stopAutoplay();
        showVideo(currentVideoIndex);
        autoplayTimer = setInterval(nextVideo, autoplayInterval);
    }

    function stopAutoplay() {
        if (autoplayTimer) {
            clearInterval(autoplayTimer);
            autoplayTimer = null;
        }
    }

    function resetAutoplay() {
        startAutoplay();
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            previousVideo();
            resetAutoplay();
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            nextVideo();
            resetAutoplay();
        });
    }

    // Handle visibility changes
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopAutoplay();
            videos.forEach(v => v.pause());
        } else {
            startAutoplay();
        }
    });

    // Initialize
    startAutoplay();
})();

// Banner carousel controls
(function() {
    const carousel = document.getElementById('bannerCarousel');
    const scrollArea = document.getElementById('bannerScroll');
    if (!carousel || !scrollArea) return;

    const prevBtn = document.getElementById('bannerPrevBtn');
    const nextBtn = document.getElementById('bannerNextBtn');
    const cards = Array.from(scrollArea.querySelectorAll('.ldm-home-banner-card'));
    if (cards.length <= 1) return;

    let currentBannerIndex = 0;
    let autoplayTimer = null;
    const autoplayInterval = 6000;

    function showBanner(index) {
        const nextIndex = (index + cards.length) % cards.length;
        currentBannerIndex = nextIndex;
        const targetCard = cards[nextIndex];
        if (targetCard) {
            scrollArea.scrollTo({
                left: targetCard.offsetLeft,
                behavior: 'smooth'
            });
        }
    }

    function scrollPrev() {
        showBanner(currentBannerIndex - 1);
    }

    function scrollNext() {
        showBanner(currentBannerIndex + 1);
    }

    function stopAutoplay() {
        if (autoplayTimer) {
            clearInterval(autoplayTimer);
            autoplayTimer = null;
        }
    }

    function startAutoplay() {
        stopAutoplay();
        autoplayTimer = setInterval(() => {
            showBanner(currentBannerIndex + 1);
        }, autoplayInterval);
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            scrollPrev();
            startAutoplay();
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            scrollNext();
            startAutoplay();
        });
    }

    carousel.addEventListener('mouseenter', stopAutoplay);
    carousel.addEventListener('mouseleave', startAutoplay);

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopAutoplay();
        } else {
            startAutoplay();
        }
    });

    startAutoplay();
})();

// Initialize wishlist icons on page load
document.addEventListener('DOMContentLoaded', function() {
    const wishlist = JSON.parse(localStorage.getItem('wishlist') || '[]');
    wishlist.forEach(id => {
        const icon = document.getElementById('wishlist-' + id);
        if (icon) icon.style.color = '#dc3545';
    });

    // Wishlist button handler
    document.querySelectorAll('.wishlist-btn-inline').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const productId = this.dataset.productId;
            if (productId) {
                toggleWishlistAjax(productId, this);
            }
        });
    });
});
