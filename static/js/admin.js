/**
 * ADMIN PANEL - Admin.js
 * Professional admin functionality including charts, tables, and modals
 */

// ====== CHART.JS INITIALIZATION ======
const LDMCharts = {
    initRevenueChart: function(canvasId, data = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const chartData = {
            labels: data.labels || ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'],
            datasets: [
                {
                    label: 'Doanh thu (₫)',
                    data: data.values || [2000000, 2500000, 1800000, 3200000, 2700000, 3500000, 2200000],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                }
            ]
        };

        new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        labels: { font: { family: "'Signika', sans-serif" } }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => (v / 1000000).toFixed(1) + 'tr' }
                    }
                }
            }
        });
    }
};

window.LDMCharts = LDMCharts;

// ====== TABLE SEARCH & FILTER ======
const LDMTable = {
    // Search in table
    search: function(inputId, tableBodyId) {
        const input = document.getElementById(inputId);
        if (!input) return;

        input.addEventListener('keyup', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll(`#${tableBodyId} tr`);
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    },

    // Filter by status
    filterByStatus: function(filterBtnClass, rowAttr, tableBodyId) {
        const buttons = document.querySelectorAll(`.${filterBtnClass}`);
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const status = btn.dataset.status;
                const rows = document.querySelectorAll(`#${tableBodyId} tr`);
                
                // Update button styles
                buttons.forEach(b => {
                    b.style.background = 'white';
                    b.style.color = '#64748b';
                });
                btn.style.background = '#3b82f6';
                btn.style.color = 'white';
                
                // Filter rows
                rows.forEach(row => {
                    if (status === 'all') {
                        row.style.display = '';
                    } else {
                        row.style.display = row.dataset[rowAttr] === status ? '' : 'none';
                    }
                });
            });
        });
    },

    // Pagination
    renderPagination: function(currentPage, totalPages, urlPattern) {
        const container = document.querySelector('.ldm-pagination');
        if (!container) return;

        let html = '';
        if (currentPage > 1) {
            html += `<a href="${urlPattern.replace('{page}', '1')}">« Đầu</a>`;
            html += `<a href="${urlPattern.replace('{page}', currentPage - 1)}">‹ Trước</a>`;
        }

        for (let i = 1; i <= totalPages; i++) {
            if (i === currentPage) {
                html += `<span class="active">${i}</span>`;
            } else {
                html += `<a href="${urlPattern.replace('{page}', i)}">${i}</a>`;
            }
        }

        if (currentPage < totalPages) {
            html += `<a href="${urlPattern.replace('{page}', currentPage + 1)}">Tiếp ›</a>`;
            html += `<a href="${urlPattern.replace('{page}', totalPages)}">Cuối »</a>`;
        }

        container.innerHTML = html;
    }
};

window.LDMTable = LDMTable;

// ====== MODAL DIALOGS ======
const LDMModal = {
    show: function(title, content, actions = {}) {
        const modal = document.createElement('div');
        modal.className = 'ldm-modal active';
        
        let actionHtml = '';
        if (actions.confirm) {
            actionHtml += `<button class="ldm-button ldm-button-primary" data-action="confirm">${actions.confirm}</button>`;
        }
        if (actions.cancel) {
            actionHtml += `<button class="ldm-button ldm-button-secondary" data-action="cancel">${actions.cancel}</button>`;
        }

        modal.innerHTML = `
            <div class="ldm-modal-content" style="background:white;border-radius:12px;padding:24px;max-width:500px;box-shadow:0 20px 60px rgba(0,0,0,0.15);">
                <h3 style="margin:0 0 16px;font-size:20px;font-weight:600;color:#1e293b;">${title}</h3>
                <div style="margin:0 0 24px;color:#64748b;line-height:1.6;">${content}</div>
                <div style="display:flex;gap:12px;justify-content:flex-end;">
                    ${actionHtml}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const confirmBtn = modal.querySelector('[data-action="confirm"]');
        const cancelBtn = modal.querySelector('[data-action="cancel"]');

        const close = () => modal.remove();

        if (confirmBtn) confirmBtn.addEventListener('click', () => {
            if (actions.onConfirm) actions.onConfirm();
            close();
        });

        if (cancelBtn) cancelBtn.addEventListener('click', () => {
            if (actions.onCancel) actions.onCancel();
            close();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) close();
        });

        return modal;
    },

    alert: function(message) {
        this.show('Thông báo', message, {
            confirm: 'Đóng',
            onConfirm: () => {}
        });
    },

    confirm: function(message, onConfirm, onCancel) {
        this.show('Xác nhận', message, {
            confirm: 'Xác nhận',
            cancel: 'Hủy',
            onConfirm: onConfirm,
            onCancel: onCancel
        });
    }
};

window.LDMModal = LDMModal;

// ====== EXCEL EXPORT ======
const LDMExport = {
    exportToExcel: function(tableSelector, filename = 'data.xlsx') {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const workbook = XLSX.utils.table_to_book(table);
        XLSX.writeFile(workbook, filename);
    },

    exportTableData: function(headers, rows, filename = 'data.xlsx') {
        const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
        XLSX.writeFile(wb, filename);
    }
};

window.LDMExport = LDMExport;

// ====== PRODUCT MANAGEMENT ======
const LDMProducts = {
    deleteProduct: function(productId, productName) {
        LDMModal.confirm(
            `Bạn có chắc chắn muốn xóa sản phẩm "${productName}"?`,
            () => {
                window.location = `/dashboard/delete/${productId}/`;
            }
        );
    },

    editProduct: function(productId) {
        window.location = `/dashboard/edit/${productId}/`;
    },

    bulkDelete: function(selectedIds) {
        if (selectedIds.length === 0) {
            LDMModal.alert('Vui lòng chọn ít nhất một sản phẩm');
            return;
        }

        LDMModal.confirm(
            `Bạn có chắc chắn muốn xóa ${selectedIds.length} sản phẩm?`,
            () => {
                fetch('/api/products/bulk-delete/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({ ids: selectedIds })
                }).then(() => location.reload());
            }
        );
    }
};

window.LDMProducts = LDMProducts;

// ====== ORDER MANAGEMENT ======
const LDMOrders = {
    viewOrder: function(orderId) {
        window.location = `/order/${orderId}/`;
    },

    updateStatus: function(orderId, newStatus) {
        LDMModal.confirm(
            `Cập nhật trạng thái đơn hàng thành "${newStatus}"?`,
            () => {
                fetch(`/api/orders/${orderId}/status/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({ status: newStatus })
                }).then(() => location.reload());
            }
        );
    },

    deleteOrder: function(orderId) {
        LDMModal.confirm(
            'Bạn có chắc chắn muốn xóa đơn hàng này?',
            () => {
                window.location = `/order/delete/${orderId}/`;
            }
        );
    },

    exportOrders: function() {
        const table = document.querySelector('.ldm-table');
        if (table) {
            LDMExport.exportToExcel('.ldm-table', 'don-hang.xlsx');
            LDMToast.success('✅ Xuất Excel thành công!');
        }
    }
};

window.LDMOrders = LDMOrders;

// ====== AUTO-INITIALIZE ON PAGE LOAD ======
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search for products and orders
    if (document.getElementById('productSearch')) {
        LDMTable.search('productSearch', 'productsTableBody');
    }
    
    if (document.getElementById('orderSearch')) {
        LDMTable.search('orderSearch', 'ordersTableBody');
    }

    // Initialize status filters for orders
    const filterBtns = document.querySelectorAll('.ldm-filter-btn');
    if (filterBtns.length > 0) {
        LDMTable.filterByStatus('ldm-filter-btn', 'status', 'ordersTableBody');
    }

    // Initialize charts
    if (document.getElementById('revenueChart')) {
        LDMCharts.initRevenueChart('revenueChart');
    }
});
