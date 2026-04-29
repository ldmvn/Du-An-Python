// Filter Modal Functionality
document.addEventListener('DOMContentLoaded', function() {
    const filterBtn = document.getElementById('openFilterBtn');
    const filterModal = document.getElementById('filterModal');
    const filterOverlay = document.getElementById('filterOverlay');
    const filterClose = document.getElementById('filterClose');
    const filterReset = document.getElementById('filterReset');
    const filterForm = document.getElementById('filterForm');

    // Open filter modal
    if (filterBtn) {
        filterBtn.addEventListener('click', function(e) {
            e.preventDefault();
            filterModal.classList.add('active');
        });
    }

    // Close filter modal
    const closeModal = function() {
        filterModal.classList.remove('active');
    };

    if (filterClose) {
        filterClose.addEventListener('click', closeModal);
    }

    if (filterOverlay) {
        filterOverlay.addEventListener('click', closeModal);
    }

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && filterModal.classList.contains('active')) {
            closeModal();
        }
    });

    // Close when clicking outside the modal
    document.addEventListener('click', function(e) {
        if (filterModal.classList.contains('active')) {
            if (!filterModal.contains(e.target) && !filterBtn.contains(e.target)) {
                closeModal();
            }
        }
    });

    // Price Range Slider
    const priceSliderMin = document.getElementById('priceSliderMin');
    const priceSliderMax = document.getElementById('priceSliderMax');
    const priceMin = document.getElementById('priceMin');
    const priceMax = document.getElementById('priceMax');
    const priceDisplay = document.getElementById('priceDisplay');

    if (priceSliderMin && priceSliderMax) {
        // Format price to Vietnamese format
        const formatPrice = (price) => {
            return new Intl.NumberFormat('vi-VN', {
                style: 'currency',
                currency: 'VND',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(price);
        };

        // Update display
        const updatePriceDisplay = () => {
            const min = parseInt(priceSliderMin.value);
            const max = parseInt(priceSliderMax.value);

            priceMin.value = min;
            priceMax.value = max;

            if (priceDisplay) {
                priceDisplay.textContent = `${formatPrice(min)} - ${formatPrice(max)}`;
            }

            // Update slider track
            const range = priceSliderMax.max - priceSliderMin.min;
            const minPercent = ((min - priceSliderMin.min) / range) * 100;
            const maxPercent = ((max - priceSliderMin.min) / range) * 100;

            const sliderTrack = document.querySelector('.ldm-slider-track');
            if (sliderTrack) {
                sliderTrack.style.left = minPercent + '%';
                sliderTrack.style.right = (100 - maxPercent) + '%';
            }
        };

        // Slider events
        priceSliderMin.addEventListener('input', function() {
            if (parseInt(this.value) > parseInt(priceSliderMax.value)) {
                this.value = priceSliderMax.value;
            }
            updatePriceDisplay();
        });

        priceSliderMax.addEventListener('input', function() {
            if (parseInt(this.value) < parseInt(priceSliderMin.value)) {
                this.value = priceSliderMin.value;
            }
            updatePriceDisplay();
        });

        // Input field events
        if (priceMin && priceMax) {
            priceMin.addEventListener('input', function() {
                const value = Math.max(0, parseInt(this.value) || 0);
                priceSliderMin.value = value;
                updatePriceDisplay();
            });

            priceMax.addEventListener('input', function() {
                const value = Math.min(64000000, parseInt(this.value) || 64000000);
                priceSliderMax.value = value;
                updatePriceDisplay();
            });
        }

        // Initialize display
        updatePriceDisplay();
    }

    // Reset filters
    if (filterReset) {
        filterReset.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Reset radio buttons (brand)
            const brandRadios = document.querySelectorAll('input[name="brand"]');
            brandRadios.forEach(radio => {
                if (radio.value === '') {
                    radio.checked = true;
                } else {
                    radio.checked = false;
                }
            });

            // Reset checkboxes
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
            });

            // Reset price sliders
            if (priceSliderMin && priceSliderMax) {
                priceSliderMin.value = 0;
                priceSliderMax.value = 64000000;
                updatePriceDisplay();
            }
        });
    }

    // Submit form
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            // Form will submit normally with all selected filters
            // No need to prevent default
        });
    }
});
