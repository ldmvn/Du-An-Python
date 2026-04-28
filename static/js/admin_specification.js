document.addEventListener('DOMContentLoaded', function () {
    const specTable = document.getElementById('productSpecTable');
    const addSpecBtn = document.getElementById('btnAddSpec');
    const specTabs = document.getElementById('productSpecTabs');
    const addSpecClusterBtn = document.getElementById('btnAddSpecCluster');
    const deleteSpecClusterBtn = document.getElementById('btnDeleteSpecCluster');
    const newSpecClusterInput = document.getElementById('newSpecClusterInput');
    const specCategoryOrderInput = document.getElementById('specCategoryOrderInput');
    let specCategoryOrder = [];
    let activeSpecCategory = 'Thông số khác';

    function parseSpecCategoryOrder() {
        if (!specCategoryOrderInput) return [];
        const raw = String(specCategoryOrderInput.value || '').trim();
        if (!raw) return [];
        return raw.split(',').map(function (item) { return item.trim(); }).filter(Boolean);
    }

    function syncSpecCategoryOrderInput() {
        if (!specCategoryOrderInput) return;
        specCategoryOrderInput.value = specCategoryOrder.join(',');
    }

    function getSpecCategories() {
        if (!specCategoryOrder.length) {
            specCategoryOrder = ['Thông số khác'];
            syncSpecCategoryOrderInput();
        }
        return specCategoryOrder.slice();
    }

    function addSpecCategory(name) {
        const value = String(name || '').trim();
        if (!value) return false;
        if (!specCategoryOrder.includes(value)) {
            specCategoryOrder.push(value);
            syncSpecCategoryOrderInput();
        }
        return true;
    }

    function renderSpecTabs() {
        if (!specTabs) return;
        const categories = getSpecCategories();
        if (!categories.includes(activeSpecCategory)) {
            activeSpecCategory = categories[0];
        }
        specTabs.innerHTML = categories.map(function (category) {
            const activeClass = category === activeSpecCategory ? 'is-active' : '';
            return '<button type="button" class="product-spec-tab ' + activeClass + '" data-spec-category="' + category + '">' + category + '</button>';
        }).join('');

        specTabs.querySelectorAll('.product-spec-tab').forEach(function (button) {
            button.addEventListener('click', function () {
                activeSpecCategory = button.dataset.specCategory;
                applySpecFilter();
            });
        });
    }

    function bindSpecKeyCategoryTracking(row) {
        const categoryInput = row.querySelector('.spec-category-input');
        if (!categoryInput) return;
        categoryInput.addEventListener('change', function () {
            addSpecCategory(categoryInput.value);
            applySpecFilter();
        });
        const keyInput = row.querySelector('input[name^="spec_key__"]');
        if (keyInput) {
            keyInput.addEventListener('input', function () {
                if (categoryInput && !categoryInput.value.trim()) {
                    categoryInput.value = activeSpecCategory;
                }
                applySpecFilter();
            });
        }
    }

    function renderSpecCategoryOptions(select, selectedValue) {
        if (!select) return;
        const categories = getSpecCategories();
        const safeValue = selectedValue && selectedValue.trim() ? selectedValue.trim() : activeSpecCategory;
        if (safeValue && !categories.includes(safeValue)) {
            categories.push(safeValue);
            addSpecCategory(safeValue);
        }
        select.innerHTML = categories.map(function (category) {
            const selected = category === safeValue ? ' selected' : '';
            return '<option value="' + category + '"' + selected + '>' + category + '</option>';
        }).join('');
        select.value = safeValue;
    }

    function syncAllRowCategoryOptions() {
        if (!specTable) return;
        specTable.querySelectorAll('.spec-category-input').forEach(function (select) {
            renderSpecCategoryOptions(select, select.value);
        });
    }

    function getRowCategory(row) {
        const categoryInput = row.querySelector('.spec-category-input');
        const category = categoryInput ? String(categoryInput.value || '').trim() : '';
        return category || 'Thông số khác';
    }

    function setRowCategory(row, category) {
        const categoryInput = row.querySelector('.spec-category-input');
        if (!categoryInput) return;
        addSpecCategory(category);
        renderSpecCategoryOptions(categoryInput, category);
    }

    function moveVisibleRowsToCategory(targetCategory) {
        if (!specTable || !targetCategory) return;
        specTable.querySelectorAll('.product-spec-row').forEach(function (row) {
            if (row.style.display === 'none') return;
            const deleted = row.querySelector('.spec-delete-flag');
            if (deleted && deleted.value === '1') return;
            setRowCategory(row, targetCategory);
        });
    }

    function moveRowsByCategory(fromCategory, toCategory) {
        if (!specTable || !fromCategory || !toCategory) return;
        specTable.querySelectorAll('.product-spec-row').forEach(function (row) {
            const deleted = row.querySelector('.spec-delete-flag');
            if (deleted && deleted.value === '1') return;
            if (getRowCategory(row) === fromCategory) {
                setRowCategory(row, toCategory);
            }
        });
    }

    function applySpecFilter() {
        if (!specTable) return;
        specTable.querySelectorAll('.product-spec-row').forEach(function (row) {
            if (row.style.display === 'none' && row.querySelector('.spec-delete-flag') && row.querySelector('.spec-delete-flag').value === '1') {
                return;
            }
            const categoryInput = row.querySelector('.spec-category-input');
            if (categoryInput) {
                addSpecCategory(categoryInput.value);
            }
            const rowCategory = getRowCategory(row);
            row.dataset.specCategory = rowCategory;
            row.style.display = rowCategory === activeSpecCategory ? '' : 'none';
        });
        syncAllRowCategoryOptions();
        updateSpecRowNumbers();
        renderSpecTabs();
    }

    function bindRemoveSpecButton(row) {
        const btn = row.querySelector('.btn-remove-spec');
        if (!btn) return;
        bindSpecKeyCategoryTracking(row);
        btn.addEventListener('click', function () {
            const deleteFlag = row.querySelector('.spec-delete-flag');
            const isExisting = String(row.dataset.rowKey || '').startsWith('existing-spec-');
            if (isExisting && deleteFlag) {
                deleteFlag.value = '1';
                row.style.display = 'none';
            } else {
                row.remove();
            }
            updateSpecRowNumbers();
        });
    }

    function buildSpecRow(key) {
        const row = document.createElement('tr');
        row.className = 'product-spec-row';
        row.dataset.rowKey = key;
        row.dataset.specCategory = activeSpecCategory;
        row.innerHTML = `
            <td class="product-spec-index"></td>
            <td class="product-spec-cell-input">
                <span class="product-spec-mobile-label">Thông số</span>
                <input type="hidden" name="spec_row_keys" value="${key}">
                <input type="hidden" name="spec_id__${key}" value="">
                <input type="hidden" name="spec_delete__${key}" value="0" class="spec-delete-flag">
                <select name="spec_category__${key}" class="spec-category-input"></select>
                <input type="text" name="spec_key__${key}" placeholder="Tên thông số (vd: Màn hình)">
            </td>
            <td class="product-spec-cell-input">
                <span class="product-spec-mobile-label">Giá trị</span>
                <input type="text" name="spec_value__${key}" placeholder="Giá trị (vd: 6.7 inch OLED)">
            </td>
            <td class="product-spec-cell-input product-spec-visible">
                <span class="product-spec-mobile-label">Hiển thị</span>
                <input type="hidden" name="spec_visible__${key}" value="0">
                <label><input type="checkbox" name="spec_visible__${key}" value="1" checked> Hiển thị</label>
            </td>
            <td class="product-spec-action">
                <button type="button" class="ldm-button ldm-button-secondary btn-remove-spec">Xóa</button>
            </td>
        `;
        setRowCategory(row, activeSpecCategory);
        bindRemoveSpecButton(row);
        return row;
    }

    function updateSpecRowNumbers() {
        if (!specTable) return;
        let counter = 1;
        specTable.querySelectorAll('.product-spec-row').forEach(function (row) {
            if (row.style.display === 'none') return;
            const indexCell = row.querySelector('.product-spec-index');
            if (indexCell) indexCell.textContent = counter;
            counter += 1;
        });
    }

    if (specTable) {
        specCategoryOrder = parseSpecCategoryOrder();
        specTable.querySelectorAll('.product-spec-row').forEach(function (row) {
            const categoryInput = row.querySelector('.spec-category-input');
            const currentValue = categoryInput ? (categoryInput.getAttribute('data-current-value') || categoryInput.value || '') : '';
            const rowCategory = currentValue.trim() || getRowCategory(row);
            addSpecCategory(rowCategory);
            if (categoryInput) {
                renderSpecCategoryOptions(categoryInput, rowCategory);
            }
        });
        specTable.querySelectorAll('.product-spec-row').forEach(bindRemoveSpecButton);
        applySpecFilter();
    }

    if (addSpecBtn) {
        addSpecBtn.addEventListener('click', function () {
            const key = 'new-spec-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
            specTable.appendChild(buildSpecRow(key));
            applySpecFilter();
        });
    }

    if (addSpecClusterBtn && newSpecClusterInput) {
        addSpecClusterBtn.addEventListener('click', function () {
            const clusterName = (newSpecClusterInput.value || '').trim();
            if (!clusterName) return;
            addSpecCategory(clusterName);
            activeSpecCategory = clusterName;
            moveVisibleRowsToCategory(clusterName);
            applySpecFilter();
            newSpecClusterInput.value = '';
        });

        newSpecClusterInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                addSpecClusterBtn.click();
            }
        });
    }

    const moveSpecClusterLeftBtn = document.getElementById('btnMoveSpecClusterLeft');
    const moveSpecClusterRightBtn = document.getElementById('btnMoveSpecClusterRight');

    function moveActiveSpecCategory(direction) {
        const index = specCategoryOrder.indexOf(activeSpecCategory);
        if (index === -1) return;
        const targetIndex = direction === 'left' ? index - 1 : index + 1;
        if (targetIndex < 0 || targetIndex >= specCategoryOrder.length) return;
        const temp = specCategoryOrder[targetIndex];
        specCategoryOrder[targetIndex] = specCategoryOrder[index];
        specCategoryOrder[index] = temp;
        syncSpecCategoryOrderInput();
        renderSpecTabs();
    }

    if (moveSpecClusterLeftBtn) {
        moveSpecClusterLeftBtn.addEventListener('click', function () {
            moveActiveSpecCategory('left');
        });
    }
    if (moveSpecClusterRightBtn) {
        moveSpecClusterRightBtn.addEventListener('click', function () {
            moveActiveSpecCategory('right');
        });
    }

    if (deleteSpecClusterBtn) {
        deleteSpecClusterBtn.addEventListener('click', function () {
            const current = String(activeSpecCategory || '').trim();
            if (!current) return;
            const categories = getSpecCategories();
            if (categories.length === 1 && categories[0] === 'Thông số khác') {
                return;
            }
            if (current === 'Thông số khác') {
                return;
            }
            const fallback = 'Thông số khác';
            addSpecCategory(fallback);
            moveRowsByCategory(current, fallback);
            const index = specCategoryOrder.indexOf(current);
            if (index !== -1) {
                specCategoryOrder.splice(index, 1);
                syncSpecCategoryOrderInput();
            }
            activeSpecCategory = fallback;
            applySpecFilter();
        });
    }
});
