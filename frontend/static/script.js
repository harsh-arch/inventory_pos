const API_URL = 'http://127.0.0.1:5000/api';
let allProductsCache = [];
let cart = [];

// --- UTILITY & CORE FUNCTIONS ---
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

function showLoader(loaderId) {
    const loader = document.getElementById(loaderId);
    if (loader) loader.style.display = 'flex';
}

function hideLoader(loaderId) {
    const loader = document.getElementById(loaderId);
    if (loader) loader.style.display = 'none';
}

function createModal(id, title, contentHTML, size = '') {
    const modalContainer = document.getElementById('modal-container');
    if (!modalContainer) return;
    const modalHTML = `
        <div id="${id}" class="modal-backdrop" onclick="closeModal('${id}')">
            <div class="modal-content ${size}" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <button class="close-modal" onclick="closeModal('${id}')">&times;</button>
                </div>
                <div class="modal-body">${contentHTML}</div>
            </div>
        </div>
    `;
    modalContainer.innerHTML = modalHTML;
}

function showConfirmModal(title, message, onConfirm, confirmText = 'Delete', confirmClass = 'delete-btn') {
    const modalId = `confirm-modal-${Date.now()}`;
    const contentHTML = `
        <p>${message}</p>
        <div class="modal-actions">
            <button class="secondary-btn" onclick="closeModal('${modalId}')">Cancel</button>
            <button id="confirm-action-btn" class="primary-btn ${confirmClass}">${confirmText}</button>
        </div>
    `;
    createModal(modalId, title, contentHTML);
    document.getElementById('confirm-action-btn').onclick = () => {
        onConfirm();
        closeModal(modalId);
    };
}

function showPromptModal(title, message, inputType, onConfirm) {
    const modalId = `prompt-modal-${Date.now()}`;
    const contentHTML = `
        <p>${message}</p>
        <input type="${inputType}" id="prompt-input" style="width: 100%; box-sizing: border-box;" />
        <div class="modal-actions">
            <button class="secondary-btn" onclick="closeModal('${modalId}')">Cancel</button>
            <button id="prompt-confirm-btn" class="primary-btn">Confirm</button>
        </div>
    `;
    createModal(modalId, title, contentHTML);
    const input = document.getElementById('prompt-input');
    input.focus();
    document.getElementById('prompt-confirm-btn').onclick = () => {
        onConfirm(input.value);
        closeModal(modalId);
    };
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.remove();
}

function renderPaginationControls(meta, containerId, loadFunc) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    if (meta.totalPages <= 1) return;

    let paginationHTML = '';
    paginationHTML += `<button class="secondary-btn" ${meta.currentPage === 1 ? 'disabled' : ''} onclick="${loadFunc}(${meta.currentPage - 1})">Previous</button>`;
    paginationHTML += `<span> Page ${meta.currentPage} of ${meta.totalPages} </span>`;
    paginationHTML += `<button class="secondary-btn" ${meta.currentPage === meta.totalPages ? 'disabled' : ''} onclick="${loadFunc}(${meta.currentPage + 1})">Next</button>`;
    container.innerHTML = paginationHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    const searchBar = document.getElementById('global-search-bar');
    if (searchBar) {
        searchBar.addEventListener('input', handleGlobalSearch);
        document.addEventListener('click', (e) => {
            if (!document.getElementById('global-search-container')?.contains(e.target)) {
                const resultsBox = document.getElementById('global-search-results');
                if(resultsBox) resultsBox.style.display = 'none';
            }
        });
    }

    const pageId = document.body.id;
    const pageInitializers = {
        'dashboard-page': initializeDashboard,
        'products-page': initializeProductsPage,
        'customers-page': initializeCustomersPage,
        'customer-dashboard-page': initializeCustomerDashboardPage,
        'suppliers-page': initializeSuppliersPage,
        'purchase-orders-page': initializePurchaseOrdersPage,
        'pos-page': initializePosPage,
        'sales-page': initializeSalesPage,
        'reports-page': initializeReportsPage,
        'expenses-page': initializeExpensesPage,
        'stock-page': initializeStockPage,
        'adjustments-page': initializeAdjustmentsPage,
    };
    if (pageInitializers[pageId]) {
        pageInitializers[pageId]();
    }
});

// --- GLOBAL SEARCH ---
let searchDebounceTimer;
function handleGlobalSearch(event) {
    clearTimeout(searchDebounceTimer);
    const query = event.target.value;
    const resultsContainer = document.getElementById('global-search-results');
    if (query.length < 2) {
        resultsContainer.style.display = 'none';
        return;
    }
    searchDebounceTimer = setTimeout(async () => {
        try {
            const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
            const results = await response.json();
            renderGlobalSearchResults(results);
        } catch (error) {
            console.error("Global search failed:", error);
        }
    }, 300);
}

function renderGlobalSearchResults(results) {
    const container = document.getElementById('global-search-results');
    container.innerHTML = '';
    if (!results.products.length && !results.customers.length && !results.sales.length && !results.suppliers.length) {
        container.innerHTML = '<div class="search-result-item">No results found</div>';
        container.style.display = 'block';
        return;
    }
    
    if (results.products.length) {
        container.innerHTML += '<div class="search-result-category">Products</div>';
        results.products.forEach(p => {
            container.innerHTML += `<div class="search-result-item" onclick="window.location.href='/products'">${p.name} <small>(${p.id})</small></div>`;
        });
    }
    if (results.customers.length) {
        container.innerHTML += '<div class="search-result-category">Customers</div>';
        results.customers.forEach(c => {
            container.innerHTML += `<div class="search-result-item" onclick="window.location.href='/customers/${c.id}'">${c.name} <small>(${c.phone})</small></div>`;
        });
    }
    if (results.sales.length) {
        container.innerHTML += '<div class="search-result-category">Sales</div>';
        results.sales.forEach(s => {
            container.innerHTML += `<div class="search-result-item" onclick="viewSaleDetails('${s.id}')">${s.id} <small>(${s.customerName})</small></div>`;
        });
    }
    if (results.suppliers.length) {
        container.innerHTML += '<div class="search-result-category">Suppliers</div>';
        results.suppliers.forEach(s => {
            container.innerHTML += `<div class="search-result-item" onclick="window.location.href='/suppliers'">${s.name}</div>`;
        });
    }

    container.style.display = 'block';
}

// --- DASHBOARD ---
function initializeDashboard() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    document.getElementById('dashboard-start-date').valueAsDate = firstDayOfMonth;
    document.getElementById('dashboard-end-date').valueAsDate = today;
    document.getElementById('dashboard-filter-btn').addEventListener('click', loadDashboardData);
    loadDashboardData();
}

function calculateChange(current, previous) {
    if (previous === 0 || previous === null || previous === undefined) {
        return current > 0 ? Infinity : (current < 0 ? -Infinity : 0);
    }
    return ((current - previous) / Math.abs(previous)) * 100;
}

function renderKpiChange(elementId, change) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (!isFinite(change) || isNaN(change)) {
        el.textContent = '...';
        el.className = 'kpi-change';
        return;
    }
    const sign = change >= 0 ? '▲' : '▼';
    el.textContent = `${sign} ${Math.abs(change).toFixed(2)}%`;
    el.className = `kpi-change ${change >= 0 ? 'positive' : 'negative'}`;
}

let salesOverviewChart = null;
async function loadDashboardData() {
    showLoader('dashboard-loader');
    document.getElementById('dashboard-content').style.display = 'none';
    const startDate = document.getElementById('dashboard-start-date').value;
    const endDate = document.getElementById('dashboard-end-date').value;

    try {
        const [kpiRes, chartRes] = await Promise.all([
            fetch(`${API_URL}/reports/dashboard-kpis?startDate=${startDate}&endDate=${endDate}`),
            fetch(`${API_URL}/reports/sales-overview?startDate=${startDate}&endDate=${endDate}`)
        ]);

        if (!kpiRes.ok) throw new Error('Failed to fetch dashboard KPIs');
        const kpis = await kpiRes.json();

        const { pnl, previous_pnl, today, topProducts, recentSales, lowStockAlerts, systemStats } = kpis;
        document.getElementById('kpi-revenue').textContent = `RS. ${(pnl.totalRevenue || 0).toFixed(2)}`;
        document.getElementById('kpi-profit').textContent = `RS. ${(pnl.netProfit || 0).toFixed(2)}`;
        document.getElementById('kpi-avg-sale').textContent = `RS. ${(pnl.avgSaleValue || 0).toFixed(2)}`;
        document.getElementById('kpi-sales-count').textContent = pnl.salesCount || 0;
        
        renderKpiChange('kpi-revenue-change', calculateChange(pnl.totalRevenue, previous_pnl.totalRevenue));
        renderKpiChange('kpi-profit-change', calculateChange(pnl.netProfit, previous_pnl.netProfit));
        renderKpiChange('kpi-avg-sale-change', calculateChange(pnl.avgSaleValue, previous_pnl.avgSaleValue));
        renderKpiChange('kpi-sales-count-change', calculateChange(pnl.salesCount, previous_pnl.salesCount));

        document.getElementById('today-sales').textContent = `RS. ${today.sales.toFixed(2)}`;
        document.getElementById('today-credit-sales').textContent = `RS. ${today.creditSales.toFixed(2)}`;
        document.getElementById('today-transactions').textContent = today.transactions;
        document.getElementById('critical-alerts').textContent = lowStockAlerts.filter(a => a.alertLevel === 'critical').length;
        
        document.getElementById('stat-total-products').textContent = systemStats.totalProducts;
        document.getElementById('stat-total-customers').textContent = systemStats.totalCustomers;
        document.getElementById('stat-inventory-value').textContent = `RS. ${systemStats.totalInventoryValue.toFixed(2)}`;

        const topProductsList = document.getElementById('top-products-list');
        topProductsList.innerHTML = topProducts.length > 0 ? topProducts.map(p => `<li><span>${p.name}</span><strong>RS. ${p.revenue.toFixed(2)}</strong></li>`).join('') : '<li>No sales in this period.</li>';
        
        const recentSalesList = document.getElementById('recent-sales-list');
        recentSalesList.innerHTML = recentSales.length > 0 ? recentSales.map(s => `<li><span onclick="viewSaleDetails('${s.id}')" class="link-like">${s.customerName} (${s.id})</span><strong>RS. ${s.totalAmount.toFixed(2)}</strong></li>`).join('') : '<li>No recent sales.</li>';
        
        const lowStockList = document.getElementById('low-stock-alerts-list');
        lowStockList.innerHTML = (lowStockAlerts || []).length > 0 ? lowStockAlerts.map(p => `<li><span>${p.productName}</span><strong style="color:var(--danger-color);">${p.currentStock} ${p.unit} left</strong></li>`).join('') : '<li>All stock levels are healthy.</li>';

        if (!chartRes.ok) throw new Error('Failed to fetch chart data');
        const chartData = await chartRes.json();
        const ctx = document.getElementById('sales-overview-chart').getContext('2d');
        if(salesOverviewChart) salesOverviewChart.destroy();
        salesOverviewChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [
                    { label: 'Revenue', data: chartData.revenueData, backgroundColor: 'rgba(13, 110, 253, 0.7)', yAxisID: 'y' },
                    { label: 'Profit', data: chartData.profitData, backgroundColor: 'rgba(25, 135, 84, 0.7)', yAxisID: 'y' }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
        });

    } catch (error) { showToast(error.message, 'error'); } 
    finally { 
        hideLoader('dashboard-loader'); 
        document.getElementById('dashboard-content').style.display = 'block';
    }
}

// --- PRODUCTS PAGE ---
function initializeProductsPage() {
    document.getElementById('product-form').addEventListener('submit', handleProductSubmit);
    document.getElementById('cancel-edit-btn').addEventListener('click', resetProductForm);
    document.getElementById('add-category-btn').addEventListener('click', handleAddCategory);
    document.getElementById('product-image').addEventListener('change', previewImage);
    document.getElementById('export-products-btn').addEventListener('click', exportData);
    
    let barcodeDebounce;
    const barcodeInput = document.getElementById('product-barcode');
    barcodeInput.addEventListener('input', () => {
        clearTimeout(barcodeDebounce);
        barcodeDebounce = setTimeout(() => checkBarcodeUniqueness(barcodeInput.value), 500);
    });
    
    loadProducts(1);
    loadCategories();
}

async function checkBarcodeUniqueness(barcode) {
    const warningEl = document.getElementById('barcode-warning');
    if (!barcode) { warningEl.style.display = 'none'; return; }
    const excludeId = document.getElementById('product-id').value;
    const response = await fetch(`${API_URL}/products/check-barcode?barcode=${barcode}&excludeId=${excludeId}`);
    const result = await response.json();
    if (result.exists) {
        warningEl.textContent = `Warning: Barcode used by "${result.productName}".`;
        warningEl.style.display = 'block';
    } else {
        warningEl.style.display = 'none';
    }
}

async function handleProductSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const productId = formData.get('id');
    const isEditing = !!productId;
    
    if (parseFloat(formData.get('price')) < parseFloat(formData.get('cost'))) {
        return showToast('Selling price cannot be less than cost price.', 'error');
    }

    const url = isEditing ? `${API_URL}/products/${productId}` : `${API_URL}/products`;
    const method = isEditing ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, { method, body: formData });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'An unknown error occurred');
        showToast(`Product ${isEditing ? 'updated' : 'added'} successfully!`);
        resetProductForm();
        loadProducts();
    } catch (error) { showToast(`Error: ${error.message}`, 'error'); }
}

function resetProductForm() {
    document.getElementById('product-form').reset();
    document.getElementById('product-id').value = '';
    document.getElementById('product-form-title').textContent = 'Add New Product';
    document.getElementById('product-submit-btn').textContent = 'Add Product';
    document.getElementById('cancel-edit-btn').style.display = 'none';
    document.getElementById('product-quantity').disabled = false;
    document.getElementById('barcode-warning').style.display = 'none';
    const preview = document.getElementById('image-preview');
    preview.src = '';
    preview.style.display = 'none';
}

async function loadProducts(page = 1) {
    showLoader('product-loader');
    const tableBody = document.getElementById('product-list-body');
    tableBody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/products?page=${page}`);
        const result = await response.json();
        result.data.forEach(product => {
            const imgSrc = product.imagePath ? `/uploads/${product.imagePath}?t=${new Date().getTime()}` : '/static/placeholder.png';
            tableBody.innerHTML += `
                <tr>
                    <td><img src="${imgSrc}" alt="${product.name}" class="table-thumb"></td>
                    <td>${product.id}</td>
                    <td>${product.name}</td>
                    <td>${product.quantity} ${product.unit}</td>
                    <td>RS. ${product.price.toFixed(2)}</td>
                    <td class="action-cell">
                        <button class="action-btn edit-btn" onclick='populateProductFormForEdit(${JSON.stringify(product)})'>Edit</button>
                        <button class="action-btn delete-btn" onclick="deleteProduct('${product.id}')">Delete</button>
                        <button class="action-btn secondary-btn" onclick="viewInventoryHistory('${product.id}', '${product.name}')">History</button>
                    </td>
                </tr>
            `;
        });
        renderPaginationControls(result, 'product-pagination', 'loadProducts');
    } catch (error) { showToast('Failed to load products.', 'error'); } 
    finally { hideLoader('product-loader'); }
}

function populateProductFormForEdit(product) {
    document.getElementById('product-id').value = product.id;
    document.getElementById('product-name').value = product.name;
    document.getElementById('product-barcode').value = product.barcode || '';
    document.getElementById('product-cost').value = product.cost;
    document.getElementById('product-price').value = product.price;
    document.getElementById('product-quantity').value = product.quantity;
    document.getElementById('product-quantity').disabled = true;
    document.getElementById('product-unit').value = product.unit;
    document.getElementById('product-category').value = product.category;
    document.getElementById('product-reorder-threshold').value = product.reorderThreshold;
    document.getElementById('product-expiry').value = product.expiryDate;
    
    const preview = document.getElementById('image-preview');
    if (product.imagePath) {
        preview.src = `/uploads/${product.imagePath}?t=${new Date().getTime()}`;
        preview.style.display = 'block';
    } else { preview.style.display = 'none'; }

    document.getElementById('product-form-title').textContent = 'Edit Product';
    document.getElementById('product-submit-btn').textContent = 'Update Product';
    document.getElementById('cancel-edit-btn').style.display = 'inline-block';
    window.scrollTo(0, 0);
}

function deleteProduct(productId) {
    showConfirmModal('Delete Product', 'Are you sure you want to delete this product? This action cannot be undone.', async () => {
        try {
            const response = await fetch(`${API_URL}/products/${productId}`, { method: 'DELETE' });
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Failed to delete product.');
            }
            showToast('Product deleted successfully!');
            loadProducts();
        } catch (error) { showToast(error.message, 'error'); }
    });
}

async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        const categories = await response.json();
        const select = document.getElementById('product-category');
        select.innerHTML = '<option value="Uncategorized">Uncategorized</option>';
        categories.forEach(cat => { select.innerHTML += `<option value="${cat}">${cat}</option>`; });
    } catch (error) { showToast('Could not load categories', 'error'); }
}

function handleAddCategory() {
    showPromptModal('New Category', 'Enter category name:', 'text', async (name) => {
        if (!name || name.trim() === '') return;
        try {
            const response = await fetch(`${API_URL}/categories`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim() })
            });
            if (!response.ok) throw new Error('Category already exists or server error.');
            showToast('Category added!');
            await loadCategories();
            document.getElementById('product-category').value = name.trim();
        } catch (error) { showToast(error.message, 'error'); }
    });
}

function previewImage(event) {
    const previewId = event.target.id === 'product-image' ? 'image-preview' : 'image-preview-customer';
    const preview = document.getElementById(previewId);
    const file = event.target.files[0];
    if (file) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = 'block';
    } else { preview.style.display = 'none'; }
}

async function viewInventoryHistory(productId, productName) {
    const modalId = `history-modal-${productId}`;
    let contentHTML = '<div id="history-loader" class="loader-container"><div class="loader"></div></div><table id="history-table" style="width:100%; display:none;"><thead><tr><th>Date</th><th>Change</th><th>Reason</th><th>Ref ID</th></tr></thead><tbody></tbody></table>';
    createModal(modalId, `Inventory History for ${productName}`, contentHTML, 'modal-lg');

    try {
        const response = await fetch(`${API_URL}/products/${productId}/history`);
        if (!response.ok) throw new Error('Failed to fetch history');
        const history = await response.json();
        const tbody = document.querySelector(`#${modalId} #history-table tbody`);
        tbody.innerHTML = '';
        if (history.length > 0) {
            history.forEach(log => {
                const change = log.changeQuantity;
                const changeClass = change > 0 ? 'positive' : 'negative';
                const sign = change > 0 ? '+' : '';
                tbody.innerHTML += `
                    <tr>
                        <td>${new Date(log.timestamp).toLocaleString()}</td>
                        <td class="${changeClass}">${sign}${change}</td>
                        <td>${log.reason}</td>
                        <td>${log.referenceId}</td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4">No history found for this product.</td></tr>';
        }
    } catch (error) {
        showToast(error.message, 'error');
        document.querySelector(`#${modalId} .modal-body`).innerHTML = `<p>${error.message}</p>`;
    } finally {
        document.getElementById('history-loader').style.display = 'none';
        document.getElementById('history-table').style.display = 'table';
    }
}

// --- SUPPLIERS PAGE ---
function initializeSuppliersPage() {
    document.getElementById('supplier-form').addEventListener('submit', handleSupplierSubmit);
    document.getElementById('cancel-edit-btn').addEventListener('click', resetSupplierForm);
    loadSuppliers(1);
}

async function loadSuppliers(page = 1) {
    showLoader('supplier-loader');
    const tableBody = document.getElementById('supplier-list-body');
    tableBody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/suppliers?page=${page}`);
        if (!response.ok) throw new Error('Failed to fetch suppliers');
        const result = await response.json();
        result.data.forEach(supplier => {
            tableBody.innerHTML += `<tr><td>${supplier.id}</td><td>${supplier.name}</td><td>${supplier.contact || 'N/A'}</td><td>${supplier.phone || 'N/A'}</td><td class="action-cell"><button class="action-btn edit-btn" onclick='populateSupplierForm(${JSON.stringify(supplier)})'>Edit</button><button class="action-btn delete-btn" onclick="deleteSupplier('${supplier.id}')">Delete</button></td></tr>`;
        });
        renderPaginationControls(result, 'supplier-pagination', 'loadSuppliers');
    } catch (error) { showToast(error.message, 'error'); } 
    finally { hideLoader('supplier-loader'); }
}

async function handleSupplierSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('supplier-id').value;
    const data = { name: document.getElementById('supplier-name').value, contact: document.getElementById('supplier-contact').value, phone: document.getElementById('supplier-phone').value, email: document.getElementById('supplier-email').value, address: document.getElementById('supplier-address').value };
    const isEditing = !!id;
    const url = isEditing ? `${API_URL}/suppliers/${id}` : `${API_URL}/suppliers`;
    const method = isEditing ? 'PUT' : 'POST';
    try {
        const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (!response.ok) throw new Error(`Failed to ${isEditing ? 'update' : 'add'} supplier.`);
        showToast(`Supplier ${isEditing ? 'updated' : 'added'} successfully!`);
        resetSupplierForm();
        loadSuppliers();
    } catch (error) { showToast(error.message, 'error'); }
}

function resetSupplierForm() {
    document.getElementById('supplier-form').reset();
    document.getElementById('supplier-id').value = '';
    document.getElementById('supplier-form-title').textContent = 'Add New Supplier';
    document.getElementById('supplier-submit-btn').textContent = 'Add Supplier';
    document.getElementById('cancel-edit-btn').style.display = 'none';
}

function populateSupplierForm(supplier) {
    document.getElementById('supplier-id').value = supplier.id;
    document.getElementById('supplier-name').value = supplier.name;
    document.getElementById('supplier-contact').value = supplier.contact || '';
    document.getElementById('supplier-phone').value = supplier.phone || '';
    document.getElementById('supplier-email').value = supplier.email || '';
    document.getElementById('supplier-address').value = supplier.address || '';
    document.getElementById('supplier-form-title').textContent = 'Edit Supplier';
    document.getElementById('supplier-submit-btn').textContent = 'Update Supplier';
    document.getElementById('cancel-edit-btn').style.display = 'inline-block';
    window.scrollTo(0, 0);
}

function deleteSupplier(id) {
    showConfirmModal('Delete Supplier', 'Are you sure you want to delete this supplier?', async () => {
        try {
            const response = await fetch(`${API_URL}/suppliers/${id}`, { method: 'DELETE' });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to delete supplier.');
            }
            showToast('Supplier deleted.');
            loadSuppliers();
        } catch (error) { showToast(error.message, 'error'); }
    });
}

// --- PURCHASE ORDERS PAGE ---
function initializePurchaseOrdersPage() {
    loadSuppliersForPO();
}

async function loadSuppliersForPO() {
    const select = document.getElementById('po-supplier-select');
    if (!select) return;
    try {
        const response = await fetch(`${API_URL}/suppliers/all`);
        if (!response.ok) throw new Error('Failed to load suppliers for PO form');
        const suppliers = await response.json();
        select.innerHTML = '<option value="">-- Select Supplier --</option>';
        suppliers.forEach(s => {
            select.innerHTML += `<option value="${s.id}">${s.name}</option>`;
        });
    } catch (error) { showToast(error.message, 'error'); }
}

// --- CUSTOMERS PAGE ---
function initializeCustomersPage() {
    document.getElementById('customer-form').addEventListener('submit', handleCustomerSubmit);
    document.getElementById('cancel-customer-edit-btn').addEventListener('click', resetCustomerForm);
    document.getElementById('customer-image').addEventListener('change', previewImage);
    document.getElementById('export-customers-btn').addEventListener('click', exportData);
    loadCustomers(1);
}

async function loadCustomers(page = 1) {
    showLoader('customer-loader');
    const tableBody = document.getElementById('customer-list-body');
    tableBody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/customers?page=${page}`);
        const result = await response.json();
        result.data.forEach(customer => {
             const imgSrc = customer.imagePath ? `/uploads/${customer.imagePath}?t=${new Date().getTime()}` : '/static/placeholder.png';
            tableBody.innerHTML += `<tr><td><img src="${imgSrc}" alt="${customer.name}" class="table-thumb"></td><td>${customer.id}</td><td>${customer.name}</td><td>RS. ${customer.credit_balance.toFixed(2)}</td><td class="action-cell"><button class="action-btn view-btn" onclick="window.location.href='/customers/${customer.id}'">View</button><button class="action-btn edit-btn" onclick='populateCustomerFormForEdit(${JSON.stringify(customer)})'>Edit</button><button class="action-btn delete-btn" onclick="deleteCustomer('${customer.id}')">Delete</button></td></tr>`;
        });
        renderPaginationControls(result, 'customer-pagination', 'loadCustomers');
    } catch (error) { showToast('Failed to load customers.', 'error'); } 
    finally { hideLoader('customer-loader'); }
}

async function handleCustomerSubmit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const customerId = formData.get('id');
    const isEditing = !!customerId;
    const url = isEditing ? `${API_URL}/customers/${customerId}` : `${API_URL}/customers`;
    const method = isEditing ? 'PUT' : 'POST';
    try {
        const response = await fetch(url, { method, body: formData });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        showToast(`Customer ${isEditing ? 'updated' : 'added'} successfully!`);
        resetCustomerForm();
        loadCustomers();
    } catch (error) { showToast(`Error: ${error.message}`, 'error'); }
}

function resetCustomerForm() {
    document.getElementById('customer-form').reset();
    document.getElementById('customer-id').value = '';
    document.getElementById('customer-form-title').textContent = 'Add New Customer';
    document.getElementById('customer-submit-btn').textContent = 'Add Customer';
    document.getElementById('cancel-customer-edit-btn').style.display = 'none';
    const preview = document.getElementById('image-preview-customer');
    preview.src = '';
    preview.style.display = 'none';
}

function populateCustomerFormForEdit(customer) {
    document.getElementById('customer-id').value = customer.id;
    document.getElementById('customer-name').value = customer.name;
    document.getElementById('customer-phone').value = customer.phone;
    document.getElementById('customer-email').value = customer.email;
    document.getElementById('customer-address').value = customer.address;
    document.getElementById('customer-notes').value = customer.notes || '';
    const preview = document.getElementById('image-preview-customer');
    if (customer.imagePath) {
        preview.src = `/uploads/${customer.imagePath}?t=${new Date().getTime()}`;
        preview.style.display = 'block';
    } else { preview.style.display = 'none'; }
    document.getElementById('customer-form-title').textContent = 'Edit Customer';
    document.getElementById('customer-submit-btn').textContent = 'Update Customer';
    document.getElementById('cancel-customer-edit-btn').style.display = 'inline-block';
    window.scrollTo(0, 0);
}

function deleteCustomer(customerId) {
    showConfirmModal('Delete Customer', 'Are you sure you want to delete this customer?', async () => {
        try {
            const response = await fetch(`${API_URL}/customers/${customerId}`, { method: 'DELETE' });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            showToast('Customer deleted successfully!');
            loadCustomers();
        } catch (error) { showToast(error.message, 'error'); }
    });
}

// --- CUSTOMER DASHBOARD ---
let currentCustomerData = {};
function initializeCustomerDashboardPage() {
    const customerId = window.location.pathname.split('/').pop();
    loadCustomerDashboardData(customerId);
    document.getElementById('make-payment-btn').addEventListener('click', () => {
        makeCreditPayment(customerId, currentCustomerData.credit_balance);
    });
}

async function loadCustomerDashboardData(customerId) {
    showLoader('customer-dashboard-loader');
    document.getElementById('customer-dashboard-content').style.display = 'none';
    try {
        const [customerRes, dataRes] = await Promise.all([ fetch(`${API_URL}/customers/${customerId}`), fetch(`${API_URL}/customers/${customerId}/dashboard-data`) ]);
        if (!customerRes.ok || !dataRes.ok) throw new Error("Failed to load customer data");
        const customer = await customerRes.json();
        currentCustomerData = customer;
        const dashboardData = await dataRes.json();
        
        document.getElementById('customer-dashboard-name').textContent = customer.name;
        document.getElementById('customer-dashboard-phone').textContent = customer.phone || 'N/A';
        document.getElementById('customer-dashboard-email').textContent = customer.email || 'N/A';
        document.getElementById('customer-dashboard-address').textContent = customer.address || 'N/A';
        document.getElementById('customer-dashboard-notes').textContent = customer.notes || 'No notes for this customer.';
        document.getElementById('customer-dashboard-img').src = customer.imagePath ? `/uploads/${customer.imagePath}?t=${new Date().getTime()}` : '/static/placeholder.png';
        document.getElementById('customer-dashboard-credit').textContent = `RS. ${customer.credit_balance.toFixed(2)}`;
        document.getElementById('customer-dashboard-spent').textContent = `RS. ${dashboardData.totalSpent.toFixed(2)}`;

        const tbody = document.getElementById('customer-history-body');
        tbody.innerHTML = '';
        dashboardData.history.forEach(item => {
            const amount = Math.abs(item.totalAmount);
            let amountDisplay;
            if (item.type === 'sale') amountDisplay = `<td style="color:var(--danger-color)">-RS. ${amount.toFixed(2)}</td>`;
            else if (item.type === 'payment') amountDisplay = `<td style="color:var(--success-color)">+RS. ${amount.toFixed(2)}</td>`;
            else if (item.type === 'return') amountDisplay = `<td style="color:var(--success-color)">+RS. ${amount.toFixed(2)} (Return)</td>`;
            else amountDisplay = `<td>RS. ${item.totalAmount.toFixed(2)}</td>`;

            tbody.innerHTML += `<tr><td>${new Date(item.timestamp).toLocaleString()}</td><td>${item.type}</td><td>${item.itemSummary || 'Credit Payment'}</td>${amountDisplay}</tr>`;
        });
        
        document.getElementById('customer-dashboard-content').style.display = 'block';
    } catch (error) { showToast(error.message, 'error'); } 
    finally { hideLoader('customer-dashboard-loader'); }
}

function makeCreditPayment(customerId, maxAmount) {
    if (maxAmount <= 0) {
        showToast("No outstanding credit to pay.", "error");
        return;
    }
    showPromptModal('Make Credit Payment', `Enter amount to pay (Max: RS. ${maxAmount.toFixed(2)}):`, 'number', async (amount) => {
        const payAmount = parseFloat(amount);
        if (isNaN(payAmount) || payAmount <= 0 || payAmount > maxAmount) { return showToast('Invalid payment amount.', 'error'); }
        try {
            const response = await fetch(`${API_URL}/customers/${customerId}/pay-credit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ amount: payAmount }) });
            if (!response.ok) throw new Error('Payment failed.');
            showToast('Payment successful!');
            loadCustomerDashboardData(customerId);
        } catch (error) { showToast(error.message, 'error'); }
    });
}

// --- STOCK MANAGEMENT PAGE ---
function initializeStockPage() {
    loadStockLevels(1);
    const searchInput = document.getElementById('stock-product-search');
    searchInput.addEventListener('input', () => searchProductsForForm('stock', searchInput.value));
    document.getElementById('add-stock-form').addEventListener('submit', handleAddStock);
    document.addEventListener('click', (e) => {
        const resultsBox = document.getElementById('stock-product-results');
        if (resultsBox && !e.target.closest('#add-stock-form')) { resultsBox.style.display = 'none'; }
    });
}

async function loadStockLevels(page = 1) {
    showLoader('stock-loader');
    const tableBody = document.getElementById('stock-list-body');
    tableBody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/products?page=${page}`);
        if (!response.ok) throw new Error('Failed to load stock levels');
        const result = await response.json();
        result.data.forEach(product => {
            const imgSrc = product.imagePath ? `/uploads/${product.imagePath}?t=${new Date().getTime()}` : '/static/placeholder.png';
            let levelClass = 'ok', levelText = 'OK';
            if (product.quantity <= 0) { levelClass = 'out'; levelText = 'Out of Stock'; } 
            else if (product.reorderThreshold > 0 && product.quantity <= product.reorderThreshold) { levelClass = 'low'; levelText = 'Low'; }
            tableBody.innerHTML += `<tr><td><img src="${imgSrc}" alt="${product.name}" class="table-thumb"></td><td>${product.id}</td><td>${product.name}</td><td>${product.quantity} ${product.unit}</td><td><span class="stock-level-indicator ${levelClass}"></span> ${levelText}</td></tr>`;
        });
        renderPaginationControls(result, 'stock-pagination', 'loadStockLevels');
    } catch (error) { showToast(error.message, 'error'); } 
    finally { hideLoader('stock-loader'); }
}

async function handleAddStock(event) {
    event.preventDefault();
    const productId = document.getElementById('stock-product-id').value;
    const quantity = parseFloat(document.getElementById('stock-quantity-add').value);
    if (!productId) return showToast('Please select a product from the search results.', 'error');
    if (isNaN(quantity) || quantity <= 0) return showToast('Please enter a valid quantity.', 'error');
    try {
        const response = await fetch(`${API_URL}/products/${productId}/add-stock`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ quantity }) });
        if (!response.ok) { const result = await response.json(); throw new Error(result.error || 'Failed to add stock'); }
        showToast('Stock added successfully!');
        event.target.reset();
        document.getElementById('stock-product-id').value = '';
        loadStockLevels();
    } catch (error) { showToast(error.message, 'error'); }
}

let productSearchDebounce;
function searchProductsForForm(formPrefix, query) {
    clearTimeout(productSearchDebounce);
    const resultsContainer = document.getElementById(`${formPrefix}-product-results`);
    if (query.length < 2) { resultsContainer.style.display = 'none'; return; }
    productSearchDebounce = setTimeout(async () => {
        try {
            const response = await fetch(`${API_URL}/products/search?q=${encodeURIComponent(query)}`);
            const products = await response.json();
            resultsContainer.innerHTML = '';
            if (products.length > 0) {
                products.forEach(p => {
                    resultsContainer.innerHTML += `<div class="search-result-item" onclick="selectProductForForm('${formPrefix}', '${p.id}', '${p.name}')"><span>${p.name}</span></div>`;
                });
                resultsContainer.style.display = 'block';
            } else { resultsContainer.style.display = 'none'; }
        } catch (error) { console.error('Product search failed:', error); }
    }, 300);
}

function selectProductForForm(formPrefix, id, name) {
    document.getElementById(`${formPrefix}-product-id`).value = id;
    document.getElementById(`${formPrefix}-product-search`).value = name;
    document.getElementById(`${formPrefix}-product-results`).style.display = 'none';
}

// --- ADJUSTMENTS PAGE ---
function initializeAdjustmentsPage() {
    loadAdjustments(1);
    const searchInput = document.getElementById('adj-product-search');
    searchInput.addEventListener('input', () => searchProductsForForm('adj', searchInput.value));
    document.getElementById('adjustment-form').addEventListener('submit', handleAdjustmentSubmit);
    document.addEventListener('click', (e) => {
        const resultsBox = document.getElementById('adj-product-results');
        if (resultsBox && !e.target.closest('#adjustment-form')) { resultsBox.style.display = 'none'; }
    });
}

async function loadAdjustments(page=1) {
    showLoader('adjustment-loader');
    const tableBody = document.getElementById('adjustment-list-body');
    tableBody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/adjustments?page=${page}`);
        const result = await response.json();
        result.data.forEach(adj => {
            const changeClass = adj.quantityChange > 0 ? 'positive' : 'negative';
            tableBody.innerHTML += `<tr><td>${new Date(adj.timestamp).toLocaleString()}</td><td>${adj.productName}</td><td class="${changeClass}">${adj.quantityChange}</td><td>${adj.reason}</td></tr>`;
        });
        renderPaginationControls(result, 'adjustment-pagination', 'loadAdjustments');
    } catch (error) { showToast('Failed to load adjustments.', 'error'); }
    finally { hideLoader('adjustment-loader'); }
}

async function handleAdjustmentSubmit(event) {
    event.preventDefault();
    const productId = document.getElementById('adj-product-id').value;
    const quantity = parseFloat(document.getElementById('adj-quantity').value);
    const reason = document.getElementById('adj-reason').value;
    const type = document.getElementById('adj-type').value;

    if (!productId) return showToast('Please select a product.', 'error');
    if (isNaN(quantity) || quantity <= 0) return showToast('Invalid quantity.', 'error');
    if (!reason) return showToast('Reason is required.', 'error');

    const data = {
        productId: productId,
        quantityChange: type === 'add' ? quantity : -quantity,
        reason: reason
    };

    try {
        const response = await fetch(`${API_URL}/adjustments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        showToast('Adjustment recorded successfully!');
        event.target.reset();
        document.getElementById('adj-product-id').value = '';
        loadAdjustments();
    } catch (error) { showToast(error.message, 'error'); }
}

// --- REPORTS PAGE ---
function initializeReportsPage() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    document.getElementById('report-start-date').valueAsDate = firstDayOfMonth;
    document.getElementById('report-end-date').valueAsDate = today;
    document.getElementById('report-filter-btn').addEventListener('click', generateReports);
    document.getElementById('backup-btn').addEventListener('click', handleBackup);
    generateReports();
}
function openReport(evt, reportName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = "none");
    document.querySelectorAll('.tab-link').forEach(link => link.className = link.className.replace(" active", ""));
    document.getElementById(reportName).style.display = "block";
    evt.currentTarget.className += " active";
}
async function generateReports() {
    showLoader('report-loader');
    document.querySelectorAll('.tab-content').forEach(tc => tc.style.visibility = 'hidden');
    await Promise.all([ loadProfitAndLossReport(), loadSalesByProductReport(), loadSalesByCategoryReport(), loadInventoryValuationReport(), loadLowStockReport() ]);
    hideLoader('report-loader');
    document.querySelectorAll('.tab-content').forEach(tc => tc.style.visibility = 'visible');
}
async function loadProfitAndLossReport() {
    const startDate = document.getElementById('report-start-date').value;
    const endDate = document.getElementById('report-end-date').value;
    try {
        const response = await fetch(`${API_URL}/reports/profit-loss?startDate=${startDate}&endDate=${endDate}`);
        const { current, previous } = await response.json();
        updatePnlTable(current, '');
        updatePnlTable(previous, '-prev');
        calculatePnlChanges(current, previous);
    } catch (error) { showToast('Failed to load P&L report', 'error'); }
}
function updatePnlTable(data, suffix) {
    for (const key in data) {
        const el = document.querySelector(`[data-metric${suffix}="${key}"]`);
        if (el) {
            const value = data[key] || 0;
            const isNegative = ['totalCogs', 'spoilageLoss', 'totalExpenses'].includes(key) && value > 0;
            el.textContent = `${isNegative ? '(' : ''}RS. ${Math.abs(value).toFixed(2)}${isNegative ? ')' : ''}`;
        }
    }
}
function calculatePnlChanges(current, previous) {
     for (const key in current) {
        const el = document.getElementById(`pnl-${key}-change`);
        if (el && previous[key] !== undefined) {
            renderKpiChange(el.id, calculateChange(current[key], previous[key]));
        }
    }
}
async function loadInventoryValuationReport() {
    const tbody = document.getElementById('inventory-valuation-body');
    tbody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/reports/inventory-valuation`);
        const result = await response.json();
        result.inventory.forEach(item => {
            tbody.innerHTML += `<tr><td>${item.id}</td><td>${item.name}</td><td>${item.quantity} ${item.unit}</td><td>RS. ${item.cost_value.toFixed(2)}</td><td>RS. ${item.retail_value.toFixed(2)}</td></tr>`;
        });
        document.getElementById('total-cost-value').innerHTML = `<strong>RS. ${result.total_cost_value.toFixed(2)}</strong>`;
        document.getElementById('total-retail-value').innerHTML = `<strong>RS. ${result.total_retail_value.toFixed(2)}</strong>`;
    } catch (error) { showToast('Failed to load inventory valuation', 'error'); }
}
async function loadSalesByCategoryReport() {
    const startDate = document.getElementById('report-start-date').value;
    const endDate = document.getElementById('report-end-date').value;
    const tbody = document.getElementById('sales-by-category-body');
    tbody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/reports/sales-by-category?startDate=${startDate}&endDate=${endDate}`);
        const data = await response.json();
        data.forEach(item => { tbody.innerHTML += `<tr><td>${item.category}</td><td>RS. ${item.revenue.toFixed(2)}</td><td>RS. ${item.profit.toFixed(2)}</td></tr>`; });
    } catch (error) { showToast('Failed to load sales by category report.', 'error'); }
}
async function loadSalesByProductReport() {
    const startDate = document.getElementById('report-start-date').value;
    const endDate = document.getElementById('report-end-date').value;
    const tbody = document.getElementById('sales-by-product-body');
    tbody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/reports/sales-by-product?startDate=${startDate}&endDate=${endDate}`);
        const data = await response.json();
        data.forEach(item => { tbody.innerHTML += `<tr><td>${item.id}</td><td>${item.name}</td><td>${item.quantity}</td><td>RS. ${item.revenue.toFixed(2)}</td><td>RS. ${item.cogs.toFixed(2)}</td><td>RS. ${item.profit.toFixed(2)}</td></tr>`; });
    } catch (error) { showToast('Failed to load sales by product report.', 'error'); }
}
async function loadLowStockReport() {
    const tbody = document.getElementById('low-stock-body');
    tbody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/reports/low-stock`);
        const data = await response.json();
        data.forEach(item => { tbody.innerHTML += `<tr><td>${item.id}</td><td>${item.name}</td><td>${item.category}</td><td>${item.quantity}</td><td>${item.reorderThreshold}</td></tr>`; });
    } catch (error) { showToast('Failed to load low stock report.', 'error'); }
}
async function handleBackup() {
    try {
        const response = await fetch(`${API_URL}/backup`);
        if (!response.ok) throw new Error('Backup failed.');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `retail_backup_${new Date().toISOString().split('T')[0]}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Backup successful!');
    } catch (error) { showToast(error.message, 'error'); }
}

// --- POS PAGE ---
function initializePosPage() {
    loadAllProductsForPos();
    loadCustomersForPos();
    document.getElementById('product-search').addEventListener('input', () => renderProductListForPos());
    document.querySelectorAll('.payment-btn').forEach(btn => btn.addEventListener('click', selectPaymentMethod));
    document.getElementById('complete-sale-btn').addEventListener('click', completeSale);
    document.getElementById('sale-discount').addEventListener('input', updateCartSummary);
    document.getElementById('clear-cart-btn').addEventListener('click', () => {
        if(cart.length > 0) {
            showConfirmModal('Clear Cart', 'Are you sure you want to remove all items from the cart?', resetPos, 'Clear', 'delete-btn');
        }
    });
}

async function loadAllProductsForPos() {
    showLoader('pos-product-loader');
    try {
        const response = await fetch(`${API_URL}/products?limit=0`);
        const result = await response.json();
        allProductsCache = result.data.filter(p => p.quantity > 0);
        renderProductListForPos();
    } catch (error) { showToast('Failed to load products for POS.', 'error'); }
    finally { hideLoader('pos-product-loader'); }
}

async function loadCustomersForPos() {
    const select = document.getElementById('customer-select');
    try {
        const response = await fetch(`${API_URL}/customers/all`);
        const customers = await response.json();
        customers.forEach(c => {
            select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
        });
    } catch (error) { showToast('Failed to load customers.', 'error'); }
}

function renderProductListForPos() {
    const query = document.getElementById('product-search').value.toLowerCase();
    const listContainer = document.getElementById('pos-product-list');
    listContainer.innerHTML = '';
    const filteredProducts = allProductsCache.filter(p => p.name.toLowerCase().includes(query) || (p.barcode && p.barcode.includes(query)));
    filteredProducts.forEach(product => {
        const imgSrc = product.imagePath ? `/uploads/${product.imagePath}` : '/static/placeholder.png';
        listContainer.innerHTML += `<div class="pos-product-item" onclick='addToCart(${JSON.stringify(product)})'><img src="${imgSrc}" alt="${product.name}"><div class="pos-product-info"><span>${product.name}</span><small>In Stock: ${product.quantity}</small></div><strong>RS. ${product.price.toFixed(2)}</strong></div>`;
    });
}

function addToCart(product) {
    const existingItem = cart.find(item => item.id === product.id);
    if (existingItem) {
        if (existingItem.quantity < product.quantity) {
            existingItem.quantity++;
        } else {
            showToast(`Maximum stock for ${product.name} reached.`, 'error');
        }
    } else {
        cart.push({ ...product, quantity: 1 });
    }
    renderCart();
}

function renderCart() {
    const cartContainer = document.getElementById('cart-items');
    if (cart.length === 0) {
        cartContainer.innerHTML = '<p class="cart-empty-message">Cart is empty</p>';
    } else {
        cartContainer.innerHTML = cart.map(item => `
            <div class="cart-item">
                <span>${item.name}</span>
                <input type="number" value="${item.quantity}" min="1" max="${allProductsCache.find(p=>p.id === item.id).quantity}" onchange="updateCartQuantity('${item.id}', this.value)">
                <span>RS. ${(item.quantity * item.price).toFixed(2)}</span>
                <button onclick="removeFromCart('${item.id}')">&times;</button>
            </div>
        `).join('');
    }
    updateCartSummary();
}

function updateCartQuantity(productId, newQuantity) {
    const item = cart.find(i => i.id === productId);
    const product = allProductsCache.find(p => p.id === productId);
    const quantity = parseInt(newQuantity);
    if (item && quantity > 0) {
        if (quantity > product.quantity) {
            showToast(`Only ${product.quantity} of ${product.name} in stock.`, 'error');
            item.quantity = product.quantity;
        } else {
            item.quantity = quantity;
        }
    } else if (item) {
        cart = cart.filter(i => i.id !== productId);
    }
    renderCart();
}

function removeFromCart(productId) {
    cart = cart.filter(item => item.id !== productId);
    renderCart();
}

function updateCartSummary() {
    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
    const discount = parseFloat(document.getElementById('sale-discount').value) || 0;
    const total = subtotal - discount;
    document.getElementById('cart-subtotal').textContent = `RS. ${subtotal.toFixed(2)}`;
    document.getElementById('cart-total-amount').textContent = `RS. ${total.toFixed(2)}`;
    document.getElementById('complete-sale-btn').disabled = cart.length === 0 || !selectedPaymentMethod;
}

let selectedPaymentMethod = '';
function selectPaymentMethod(event) {
    document.querySelectorAll('.payment-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    selectedPaymentMethod = event.target.dataset.method;
    const customerId = document.getElementById('customer-select').value;
    if (selectedPaymentMethod === 'Credit' && customerId === 'cash_customer') {
        showToast('Credit payment requires a selected customer.', 'error');
        event.target.classList.remove('active');
        selectedPaymentMethod = '';
    }
    updateCartSummary();
}

async function completeSale() {
    const saleData = {
        cart: cart.map(item => ({ id: item.id, name: item.name, quantity: item.quantity, price: item.price })),
        totalAmount: parseFloat(document.getElementById('cart-total-amount').textContent.replace('RS. ', '')),
        discount: parseFloat(document.getElementById('sale-discount').value) || 0,
        paymentMethod: selectedPaymentMethod,
        customerId: document.getElementById('customer-select').value,
        customerName: document.getElementById('customer-select').selectedOptions[0].text,
        remarks: document.getElementById('sale-remarks').value
    };
    try {
        const response = await fetch(`${API_URL}/sales`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(saleData) });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        showToast('Sale completed successfully!');
        resetPos();
        loadAllProductsForPos(); // Refresh product list to show updated stock
    } catch(e) { showToast(`Sale failed: ${e.message}`, 'error'); }
}

function resetPos() {
    cart = [];
    selectedPaymentMethod = '';
    document.getElementById('sale-discount').value = 0;
    document.getElementById('sale-remarks').value = '';
    document.getElementById('customer-select').value = 'cash_customer';
    document.querySelectorAll('.payment-btn').forEach(btn => btn.classList.remove('active'));
    renderCart();
}

// --- SALES PAGE ---
function initializeSalesPage() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    document.getElementById('sales-start-date').valueAsDate = firstDayOfMonth;
    document.getElementById('sales-end-date').valueAsDate = today;
    document.getElementById('export-sales-btn').addEventListener('click', exportData);
    document.getElementById('daily-summary-btn').addEventListener('click', showDailySummary);
    // Assuming a filter button with this id exists in sales.html
    document.getElementById('sales-filter-btn')?.addEventListener('click', () => loadSales(1));
    loadSales(1);
}

async function loadSales(page = 1) {
    showLoader('sales-loader');
    const tableBody = document.getElementById('sales-list-body');
    tableBody.innerHTML = '';
    const startDate = document.getElementById('sales-start-date').value;
    const endDate = document.getElementById('sales-end-date').value;
    try {
        const response = await fetch(`${API_URL}/sales?page=${page}&startDate=${startDate}&endDate=${endDate}`);
        if (!response.ok) throw new Error('Could not fetch sales data.');
        const result = await response.json();
        if (result.data.length === 0) { 
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No sales records found for this period.</td></tr>';
        } else {
            result.data.forEach(sale => {
                tableBody.innerHTML += `<tr><td>${sale.id}</td><td>${new Date(sale.timestamp).toLocaleString()}</td><td>${sale.customerName}</td><td>${sale.paymentMethod}</td><td>RS. ${sale.totalAmount.toFixed(2)}</td><td class="action-cell"><button class="action-btn view-btn" onclick="viewSaleDetails('${sale.id}')">View Details</button></td></tr>`;
            });
        }
        renderPaginationControls(result, 'sales-pagination', 'loadSales');
    } catch (error) {
        showToast(error.message, 'error');
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center;">Error loading sales.</td></tr>`;
    } finally { hideLoader('sales-loader'); }
}

async function showDailySummary() {
    const date = document.getElementById('sales-end-date').value;
    if (!date) return showToast('Please select a date to view the summary.', 'error');
    try {
        const response = await fetch(`${API_URL}/sales/summary/${date}`);
        if (!response.ok) throw new Error('Could not fetch summary.');
        const summary = await response.json();
        let paymentDetails = Object.entries(summary.paymentMethods).map(([method, amount]) => `<li><strong>${method}:</strong> RS. ${amount.toFixed(2)}</li>`).join('');
        if (!paymentDetails) paymentDetails = '<li>No payments recorded.</li>';
        const contentHTML = `<ul style="list-style:none; padding:0;"><li><strong>Total Sales:</strong> RS. ${summary.totalSales.toFixed(2)}</li><li><strong>Total Profit:</strong> RS. ${summary.totalProfit.toFixed(2)}</li><li><strong>Transactions:</strong> ${summary.transactionCount}</li></ul><h4>Payment Methods</h4><ul style="list-style:none; padding:0;">${paymentDetails}</ul>`;
        createModal(`summary-${date}`, `Sales Summary for ${date}`, contentHTML);
    } catch (error) { showToast(error.message, 'error'); }
}

async function viewSaleDetails(saleId) {
    try {
        const response = await fetch(`${API_URL}/sales/${saleId}`);
        if (!response.ok) throw new Error('Failed to fetch sale details.');
        const sale = await response.json();

        let itemsHTML = sale.cart.map(item => `<li>${item.quantity} x ${item.name} @ RS. ${item.price.toFixed(2)} = RS. ${(item.quantity * item.price).toFixed(2)}</li>`).join('');
        const contentHTML = `
            <p><strong>Customer:</strong> ${sale.customerName}</p>
            <p><strong>Payment:</strong> ${sale.paymentMethod}</p>
            <p><strong>Discount:</strong> RS. ${(sale.discount || 0).toFixed(2)}</p>
            <p><strong>Profit:</strong> RS. ${(sale.totalProfit || 0).toFixed(2)}</p>
            <hr>
            <h4>Items</h4>
            <ul>${itemsHTML}</ul>
            <hr>
            <h3>Total: RS. ${sale.totalAmount.toFixed(2)}</h3>
            <div class="modal-actions">
                <button class="secondary-btn" onclick='showReturnModal(${JSON.stringify(sale)})'>Return Items</button>
            </div>
        `;
        createModal(`sale-details-${sale.id}`, `Sale Details: ${sale.id}`, contentHTML, 'modal-lg');
    } catch (error) { showToast(error.message, 'error'); }
}

function showReturnModal(sale) {
    closeModal(`sale-details-${sale.id}`);
    const modalId = `return-modal-${sale.id}`;
    let itemsHTML = sale.cart.map(item => `
        <div class="return-item">
            <label>${item.name} (Sold: ${item.quantity})</label>
            <input type="number" id="return-qty-${item.id}" data-item='${JSON.stringify(item)}' min="0" max="${item.quantity}" placeholder="Qty to return" value="0">
        </div>
    `).join('');
    const contentHTML = `
        <form id="return-form">
            ${itemsHTML}
            <div class="form-group">
                <label for="refund-method-select">Refund Method:</label>
                <select id="refund-method-select">
                    <option value="Credit">Adjust Customer Credit</option>
                    <option value="Cash">Cash Refund</option>
                </select>
            </div>
            <div class="form-group">
                <label for="return-reason">Reason for Return:</label>
                <input type="text" id="return-reason" placeholder="e.g., Damaged item" required>
            </div>
        </form>
        <div class="modal-actions">
            <button class="secondary-btn" onclick="closeModal('${modalId}')">Cancel</button>
            <button class="primary-btn delete-btn" onclick="handleSaleReturn('${sale.id}')">Process Return</button>
        </div>
    `;
    createModal(modalId, `Process Return for Sale ${sale.id}`, contentHTML, 'modal-lg');
}

async function handleSaleReturn(saleId) {
    const itemsToReturn = [];
    document.querySelectorAll(`#return-modal-${saleId} input[type="number"]`).forEach(input => {
        const qty = parseInt(input.value);
        if (qty > 0) {
            const itemData = JSON.parse(input.dataset.item);
            itemsToReturn.push({ ...itemData, quantity: qty });
        }
    });
    
    const refundMethod = document.getElementById('refund-method-select').value;
    const reason = document.getElementById('return-reason').value;

    if (itemsToReturn.length === 0) return showToast('No items selected for return.', 'error');
    if (!reason) return showToast('Please provide a reason for the return.', 'error');

    showConfirmModal('Confirm Return', 'Are you sure you want to process this return?', async () => {
        try {
            const response = await fetch(`${API_URL}/sales/${saleId}/return`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: itemsToReturn, refundMethod, reason })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            showToast('Return processed successfully!');
            closeModal(`return-modal-${saleId}`);
            loadSales();
        } catch (error) { showToast(`Return failed: ${error.message}`, 'error'); }
    }, 'Process', 'primary-btn');
}

async function exportData(event) {
    const id = event.target.id;
    let url = '', defaultFilename = '';
    if (id === 'export-sales-btn') {
        const startDate = document.getElementById('sales-start-date').value;
        const endDate = document.getElementById('sales-end-date').value;
        if (!startDate || !endDate) return showToast('Please select a start and end date for the export.', 'error');
        url = `${API_URL}/sales/export?startDate=${startDate}&endDate=${endDate}`;
        defaultFilename = `sales_${startDate}_to_${endDate}.csv`;
    } else if (id === 'export-products-btn') {
        url = `${API_URL}/products/export`;
        defaultFilename = 'products.csv';
    } else if (id === 'export-customers-btn') {
        url = `${API_URL}/customers/export`;
        defaultFilename = 'customers.csv';
    }
    if (!url) return;
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to export data.');
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = defaultFilename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Data exported successfully!');
    } catch (error) { showToast(error.message, 'error'); }
}

// --- EXPENSES PAGE ---
function initializeExpensesPage() {
    document.getElementById('expense-form').addEventListener('submit', handleExpenseSubmit);
    document.getElementById('cancel-edit-btn').addEventListener('click', resetExpenseForm);
    document.getElementById('expense-date').valueAsDate = new Date();
    loadExpenses(1);
}

async function loadExpenses(page = 1) {
    showLoader('expense-loader');
    const tableBody = document.getElementById('expense-list-body');
    tableBody.innerHTML = '';
    try {
        const response = await fetch(`${API_URL}/expenses?page=${page}`);
        const result = await response.json();
        result.data.forEach(expense => {
            tableBody.innerHTML += `<tr><td>${expense.date}</td><td>${expense.description}</td><td>RS. ${expense.amount.toFixed(2)}</td><td class="action-cell"><button class="action-btn edit-btn" onclick='populateExpenseForm(${JSON.stringify(expense)})'>Edit</button><button class="action-btn delete-btn" onclick="deleteExpense('${expense.id}')">Delete</button></td></tr>`;
        });
        renderPaginationControls(result, 'expense-pagination', 'loadExpenses');
    } catch (error) { showToast('Failed to load expenses.', 'error'); }
    finally { hideLoader('expense-loader'); }
}

async function handleExpenseSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('expense-id').value;
    const data = { description: document.getElementById('expense-description').value, amount: parseFloat(document.getElementById('expense-amount').value), date: document.getElementById('expense-date').value };
    if (!data.description || !data.amount || !data.date) return showToast('All fields are required.', 'error');
    const isEditing = !!id;
    const url = isEditing ? `${API_URL}/expenses/${id}` : `${API_URL}/expenses`;
    const method = isEditing ? 'PUT' : 'POST';
    try {
        const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (!response.ok) throw new Error(`Failed to ${isEditing ? 'update' : 'add'} expense.`);
        showToast(`Expense ${isEditing ? 'updated' : 'added'} successfully!`);
        resetExpenseForm();
        loadExpenses();
    } catch (error) { showToast(error.message, 'error'); }
}

function resetExpenseForm() {
    document.getElementById('expense-form').reset();
    document.getElementById('expense-id').value = '';
    document.getElementById('expense-form-title').textContent = 'Add New Expense';
    document.getElementById('expense-submit-btn').textContent = 'Add Expense';
    document.getElementById('cancel-edit-btn').style.display = 'none';
    document.getElementById('expense-date').valueAsDate = new Date();
}

function populateExpenseForm(expense) {
    document.getElementById('expense-id').value = expense.id;
    document.getElementById('expense-description').value = expense.description;
    document.getElementById('expense-amount').value = expense.amount;
    document.getElementById('expense-date').value = expense.date;
    document.getElementById('expense-form-title').textContent = 'Edit Expense';
    document.getElementById('expense-submit-btn').textContent = 'Update Expense';
    document.getElementById('cancel-edit-btn').style.display = 'inline-block';
    window.scrollTo(0, 0);
}

function deleteExpense(id) {
    showConfirmModal('Delete Expense', 'Are you sure you want to delete this expense record?', async () => {
        try {
            const response = await fetch(`${API_URL}/expenses/${id}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to delete expense.');
            showToast('Expense deleted.');
            loadExpenses();
        } catch (error) { showToast(error.message, 'error'); }
    });
}
