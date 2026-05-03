/**
 * MOBILE STORE - Main.js
 * Core toast & confirmation utilities
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
