/* ========================================================
   MOBILE STORE – Compare Page JavaScript
   ======================================================== */

/* ========== Đối tượng LDMCompare ========== */
const LDMCompare = {
    // Key lưu trữ trong localStorage
    STORAGE_KEY: 'qh_compare_items',
    MAX_ITEMS: 4,

    // Lấy danh sách sản phẩm từ localStorage
    getItems: function() {
        const data = localStorage.getItem(this.STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    },

    // Lưu danh sách sản phẩm vào localStorage
    saveItems: function(items) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(items));
        this.updateUI();
    },

    // Thêm sản phẩm vào danh sách so sánh
    addToCompare: function(id, name, image, price) {
        let items = this.getItems();

        // Kiểm tra xem sản phẩm đã tồn tại chưa
        if (items.some(item => item.id === id)) {
            if (window.LDMToast) LDMToast.show('Sản phẩm đã có trong danh sách so sánh!', 'info');
            return;
        }

        // Kiểm tra số lượng tối đa
        if (items.length >= this.MAX_ITEMS) {
            if (window.LDMToast) LDMToast.show('Tối đa ' + this.MAX_ITEMS + ' sản phẩm để so sánh!', 'error');
            return;
        }

        // Thêm sản phẩm mới
        items.push({ id: id, name: name, image: image, price: price });
        this.saveItems(items);

        if (window.LDMToast) LDMToast.show('Đã thêm vào so sánh!', 'success');
    },

    // Xóa sản phẩm khỏi danh sách
    removeFromCompare: function(id) {
        let items = this.getItems();
        items = items.filter(item => item.id !== id);
        this.saveItems(items);
    },

    // Xóa tất cả sản phẩm
    clearCompare: function() {
        this.saveItems([]);
    },

    // Cập nhật giao diện (thanh so sánh, nút, badge)
    updateUI: function() {
        const items = this.getItems();
        const count = items.length;

        // Cập nhật badge đếm
        const badge = document.getElementById('ldm-compare-fab-count');
        if (badge) badge.textContent = count;

        // Hiển/ẩn FAB dựa trên số lượng sản phẩm
        const fab = document.getElementById('ldm-compare-fab');
        if (fab) {
            if (count > 0) {
                fab.classList.add('active');
            } else {
                fab.classList.remove('active');
            }
        }

        // Cập nhật nút "So sánh ngay"
        const goBtn = document.getElementById('ldm-compare-go-btn');
        if (goBtn) goBtn.disabled = count < 2;

        // Cập nhật danh sách trong thanh so sánh
        const listContainer = document.getElementById('ldm-compare-items');
        if (listContainer) {
            if (items.length === 0) {
                listContainer.innerHTML = '<p style="text-align:center;color:#999;padding:20px;">Chưa có sản phẩm nào</p>';
            } else {
                listContainer.innerHTML = items.map(item => `
                    <div class="ldm-compare-bar-item">
                        <img src="${item.image}" alt="${item.name}">
                        <div class="ldm-compare-bar-item-info">
                            <div class="ldm-compare-bar-item-name">${item.name}</div>
                            <div class="ldm-compare-bar-item-price">${item.price}</div>
                        </div>
                        <button class="ldm-compare-bar-item-remove" onclick="LDMCompare.removeFromCompare(${item.id});LDMCompare.updateUI();">
                            <i class="ri-close-line"></i>
                        </button>
                    </div>
                `).join('');
            }
        }

        // Cập nhật trạng thái nút trên các trang
        document.querySelectorAll('.ldm-compare-btn').forEach(btn => {
            const productId = parseInt(btn.dataset.productId);
            if (items.some(item => item.id === productId)) {
                btn.classList.add('active');
                btn.innerHTML = '<i class="ri-check-line"></i> Đã thêm';
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '<i class="ri-arrow-left-right-line"></i> So sánh';
            }
        });
    },

    // Chuyển đến trang so sánh
    goToCompare: function() {
        const items = this.getItems();
        if (items.length < 2) {
            if (window.LDMToast) LDMToast.show('Cần ít nhất 2 sản phẩm để so sánh!', 'error');
            return;
        }
        const ids = items.map(item => item.id).join(',');
        window.location.href = '/compare/?ids=' + ids;
    },

    // Toggle hiển/ẩn thanh so sánh
    toggleBar: function() {
        const bar = document.getElementById('ldm-compare-bar');
        const fab = document.getElementById('ldm-compare-fab');
        if (bar && fab) {
            bar.classList.toggle('active');
            fab.classList.toggle('active');
        }
    }
};

// Khởi tạo khi trang tải xong
document.addEventListener('DOMContentLoaded', function() {
    LDMCompare.updateUI();
});

/* ========== Lọc thông số kỹ thuật ========== */
/**
 * Lọc hiển thị các thông số kỹ thuật theo mode
 * @param {string} mode - Chế độ lọc: 'all', 'same', 'diff'
 */
function filterSpecs(mode) {
    const cols = document.querySelectorAll('.ldm-compare-col');
    if (cols.length < 2) return;

    // Xây dựng lookup: label → [value, value, ...]
    const labelValues = {};
    cols.forEach(col => {
        col.querySelectorAll('.ldm-spec-row').forEach(row => {
            const label = row.dataset.label;
            const val = row.querySelector('.ldm-spec-val').innerText.trim();
            if (!labelValues[label]) labelValues[label] = [];
            labelValues[label].push(val);
        });
    });

    // Xác định label nào giống nhau vs khác nhau
    const labelStatus = {};
    for (const [label, vals] of Object.entries(labelValues)) {
        labelStatus[label] = new Set(vals).size === 1 ? 'same' : 'diff';
    }

    // Hiển thị/ẩn các hàng
    cols.forEach(col => {
        col.querySelectorAll('.ldm-spec-row').forEach(row => {
            const label = row.dataset.label;
            const status = labelStatus[label];
            if (mode === 'all') {
                row.style.display = '';
            } else {
                row.style.display = (status === mode) ? '' : 'none';
            }
        });

        // Hiển/ẩn tiêu đề nhóm
        col.querySelectorAll('.ldm-compare-spec-group').forEach(group => {
            const rows = group.querySelectorAll('.ldm-spec-row');
            const hasVisible = Array.from(rows).some(r => r.style.display !== 'none');
            const title = group.querySelector('.ldm-compare-spec-group-title');
            if (title) title.style.display = hasVisible ? '' : 'none';
            const table = group.querySelector('table');
            if (table) table.style.display = hasVisible ? '' : 'none';
        });
    });
}

/* ========== Xóa sản phẩm và tải lại trang ========== */
/**
 * Xóa sản phẩm khỏi so sánh và tải lại trang
 * @param {number} productId - ID sản phẩm cần xóa
 */
function removeAndReload(productId) {
    LDMCompare.removeFromCompare(productId);
    const items = LDMCompare.getItems();
    if (items.length < 2) {
        window.location.href = '/';
    } else {
        const ids = items.map(i => i.id).join(',');
        window.location.href = '/compare/?ids=' + ids;
    }
}

/* ========== Event Listeners for Remove Buttons ========== */
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.ldm-compare-col-remove').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            if (productId) {
                removeAndReload(productId);
            }
        });
    });
});

