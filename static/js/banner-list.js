/* =====================================================
   BANNER LIST JAVASCRIPT
   Banner management modal and CRUD operations
   ===================================================== */

// Get URLs from data tag
let bannerConfig = {};

document.addEventListener('DOMContentLoaded', function() {
    const bannerUrlsTag = document.getElementById('bannerUrls');
    if (bannerUrlsTag) {
        bannerConfig = JSON.parse(bannerUrlsTag.textContent);
    }

    // Add banner button
    const addBannerBtn = document.getElementById('addBannerBtn');
    if (addBannerBtn) {
        addBannerBtn.addEventListener('click', function() {
            openBannerModal(null);
        });
    }

    const importVideoBannerBtn = document.getElementById('importVideoBannerBtn');
    if (importVideoBannerBtn) {
        importVideoBannerBtn.addEventListener('click', function() {
            importVideoBanners();
        });
    }

    // Edit banner buttons
    document.querySelectorAll('.banner-edit-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const bannerId = this.dataset.bannerId;
            openBannerModal(bannerId);
        });
    });

    // Delete banner buttons
    document.querySelectorAll('.banner-delete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const bannerId = this.dataset.bannerId;
            deleteBanner(bannerId);
        });
    });

    // Banner form submit
    const bannerForm = document.getElementById('bannerForm');
    if (bannerForm) {
        bannerForm.addEventListener('submit', handleBannerFormSubmit);
    }

    // Image preview
    const bannerImage = document.getElementById('bannerImage');
    if (bannerImage) {
        bannerImage.addEventListener('change', handleImagePreview);
    }

    // Close modal when clicking outside
    const bannerModal = document.getElementById('bannerModal');
    if (bannerModal) {
        bannerModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeBannerModal();
            }
        });
    }
});

function openBannerModal(bannerId) {
    const modal = document.getElementById('bannerModal');
    const form = document.getElementById('bannerForm');
    const title = document.getElementById('modalTitle');
    
    if (!modal || !form) return;

    form.reset();
    form.dataset.mode = bannerId ? 'edit' : 'add';
    
    resetBannerPreview();
    
    if (bannerId) {
        title.textContent = 'Chỉnh sửa banner';
        document.getElementById('bannerId').value = bannerId;
        // Load banner data via AJAX if needed
    } else {
        title.textContent = 'Thêm banner mới';
        document.getElementById('bannerId').value = '';
    }
    
    modal.style.display = 'flex';
}

function closeBannerModal() {
    const modal = document.getElementById('bannerModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function handleBannerFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitUrl = this.dataset.mode === 'edit' ? bannerConfig.replaceUrl : bannerConfig.addUrl;
    
    fetch(submitUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': bannerConfig.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('✅ ' + data.message);
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('❌ ' + (data.message || 'Lỗi'), 'error');
        }
    })
    .catch(error => {
        showToast('❌ Lỗi: ' + error, 'error');
    });
}

function deleteBanner(bannerId) {
    if (!confirm('Bạn chắc chắn muốn xóa banner này?')) {
        return;
    }

    const formData = new FormData();
    formData.append('banner_id', bannerId);
    
    fetch(bannerConfig.deleteUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': bannerConfig.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('✅ ' + data.message);
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('❌ ' + (data.message || 'Lỗi xóa'), 'error');
        }
    })
    .catch(error => {
        showToast('❌ Lỗi: ' + error, 'error');
    });
}

function importVideoBanners() {
    if (!bannerConfig.importUrl) {
        showToast('❌ Thiếu cấu hình import video', 'error');
        return;
    }

    fetch(bannerConfig.importUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': bannerConfig.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message || '✅ Đã tải video vào Videos Banner');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('❌ ' + (data.message || 'Lỗi import video'), 'error');
        }
    })
    .catch(error => {
        showToast('❌ Lỗi: ' + error, 'error');
    });
}

function handleImagePreview(e) {
    const file = e.target.files[0];
    if (file) {
        const previewImage = document.getElementById('bannerPreviewImage');
        const previewVideo = document.getElementById('bannerPreviewVideo');

        resetBannerPreview();

        if (file.type.startsWith('video/') && previewVideo) {
            previewVideo.src = URL.createObjectURL(file);
            previewVideo.style.display = 'block';
        } else if (previewImage) {
            const reader = new FileReader();
            reader.onload = function(event) {
                previewImage.src = event.target.result;
                previewImage.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }
}

function resetBannerPreview() {
    const previewImage = document.getElementById('bannerPreviewImage');
    const previewVideo = document.getElementById('bannerPreviewVideo');

    if (previewImage) {
        previewImage.src = '';
        previewImage.style.display = 'none';
    }

    if (previewVideo) {
        previewVideo.pause();
        previewVideo.removeAttribute('src');
        previewVideo.load();
        previewVideo.style.display = 'none';
    }
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast ' + (type === 'error' ? 'error' : 'success');
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
