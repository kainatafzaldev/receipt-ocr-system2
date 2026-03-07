// ==================== COMPLETE script.js ====================

// ==================== BACKEND URL CONFIGURATION ====================
const BACKEND_URL = 'http://localhost:5000';

// Override fetch to use backend URL
const originalFetch = window.fetch;
window.fetch = function(url, options) {
    if (typeof url === 'string' && url.startsWith('/api/')) {
        url = BACKEND_URL + url;
        console.log('🌐 Fetching from:', url);
    }
    return originalFetch.call(this, url, options);
};

console.log('🚀 Backend URL configured:', BACKEND_URL);

// ==================== GLOBAL VARIABLES ====================
let currentImageData = null;
let extractedData = null;
let previewData = null;
let zoomLevel = 100;

// Get DOM elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const previewImage = document.getElementById('previewImage');
const processBtn = document.getElementById('processBtn');
const uploadOdooBtn = document.getElementById('uploadOdooBtn');
const testOdooBtn = document.getElementById('testOdooBtn');
const resultsDiv = document.getElementById('results');
const loadingDiv = document.getElementById('loading');
const statusDiv = document.getElementById('status');
const refreshBtn = document.getElementById('refreshStatusBtn');
const clearPreview = document.getElementById('clearPreview');
const previewOverlay = document.getElementById('previewOverlay');
const browseBtn = document.getElementById('browseBtn');
const odooUrl = document.getElementById('odooUrl');
const odooDb = document.getElementById('odooDb');
const odooUsername = document.getElementById('odooUsername');
const odooPassword = document.getElementById('odooPassword');

// ==================== HEALTH CHECK ====================
async function checkBackendHealth() {
    const backendStatus = document.getElementById('backendStatus');
    const apiKeyStatus = document.getElementById('apiKeyStatus');
    
    if (!backendStatus) return;
    
    try {
        backendStatus.textContent = '⏳ Checking...';
        backendStatus.className = 'status-dot checking';
        if (apiKeyStatus) {
            apiKeyStatus.textContent = '⏳ Checking...';
            apiKeyStatus.className = 'status-dot checking';
        }
        
        const response = await fetch(`${BACKEND_URL}/api/health`);
        
        if (response.ok) {
            const data = await response.json();
            
            backendStatus.textContent = '✅ Connected';
            backendStatus.className = 'status-dot online';
            
            if (apiKeyStatus) {
                apiKeyStatus.textContent = data.api_key_configured ? '✅ Valid' : '❌ Missing';
                apiKeyStatus.className = data.api_key_configured ? 'status-dot online' : 'status-dot offline';
            }
            
            if (statusDiv) {
                statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Backend connected';
                statusDiv.style.color = '#28a745';
            }
        } else {
            throw new Error('Backend not responding');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        backendStatus.textContent = '❌ Offline';
        backendStatus.className = 'status-dot offline';
        if (apiKeyStatus) {
            apiKeyStatus.textContent = '❌ Unknown';
            apiKeyStatus.className = 'status-dot offline';
        }
    }
}

// ==================== HELPER FUNCTIONS ====================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== PARSE RECEIPT LINES - EXTRACT ALL TEXT ====================
function parseAllText(lines) {
    return lines.map((line, index) => {
        line = line.trim();
        
        const priceMatch = line.match(/(\d+[.,]?\d*)\s*$/);
        const hasPrice = priceMatch !== null;
        const price = hasPrice ? priceMatch[1] : null;
        
        return {
            id: index,
            line: line,
            hasPrice: hasPrice,
            price: price
        };
    }).filter(item => item.line !== '');
}

// ==================== CREATE ODOO PREVIEW - READY MADE ====================
function createOdooPreview(lines) {
    const items = [];
    let subtotal = 0;
    
    lines.forEach((line, index) => {
        const priceMatch = line.match(/(\d+[.,]?\d*)\s*$/);
        if (priceMatch && /[A-Za-z]/.test(line)) {
            const price = parseFloat(priceMatch[1].replace(',', ''));
            
            const qtyMatch = line.match(/^(\d+)\s+(.+)$/);
            if (qtyMatch) {
                const quantity = parseInt(qtyMatch[1]);
                let name = qtyMatch[2].replace(/\s*\d+[.,]?\d*\s*$/, '').trim();
                items.push({
                    name: name || `Line ${index + 1}`,
                    quantity: quantity,
                    unitPrice: price / quantity
                });
                subtotal += price;
            } else {
                let name = line.replace(/\s*\d+[.,]?\d*\s*$/, '').trim();
                items.push({
                    name: name || `Line ${index + 1}`,
                    quantity: 1,
                    unitPrice: price
                });
                subtotal += price;
            }
        }
    });
    
    if (items.length === 0) {
        items.push({
            name: 'Receipt Item',
            quantity: 1,
            unitPrice: 0
        });
    }
    
    return { items, subtotal };
}

// ==================== UPDATED DISPLAY FUNCTION ====================
function displaySideBySide(data) {
    if (!resultsDiv) return;
    
    const extractedText = data.text || '';
    const lines = extractedText.split('\n').filter(line => line.trim() !== '');
    
    const odooPreview = (data.items && data.items.length > 0) 
        ? { items: data.items, subtotal: data.total_amount || 0 }
        : createOdooPreview(lines);

    previewData = odooPreview;
    
    let html = `
    <div class="result-section">
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
            <h3 style="margin:0;">✅ Receipt Processed Successfully</h3>
            <p style="margin:5px 0 0;">${lines.length} lines detected</p>
        </div>
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 30px;">
            <div style="flex: 1; min-width: 300px; background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #1976d2;"><i class="fas fa-image"></i> Original Receipt</h4>
                <img src="${currentImageData}" style="width: 100%; height: auto; border: 1px solid #dee2e6; border-radius: 4px;">
            </div>
            
            <div style="flex: 1; min-width: 300px; background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #28a745;"><i class="fas fa-file-alt"></i> Raw OCR Text</h4>
                <pre style="white-space: pre-wrap; background: #f8f9fa; padding: 10px; border-radius: 4px; max-height: 400px; overflow-y: auto; font-size: 12px;">${escapeHtml(extractedText)}</pre>
            </div>
        </div>`;
    
    html += displayEditablePreview(odooPreview);
    resultsDiv.innerHTML = html;
}

// ==================== READY-MADE EDITABLE PREVIEW (UPDATED) ====================
function displayEditablePreview(data) {
    let html = `
    <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <h4 style="margin: 0; color: #17a2b8;">
                    <i class="fas fa-edit"></i> Ready-Made Odoo Preview (Edit if needed)
                </h4>
                <p style="color: #6c757d; margin: 5px 0 0;">Items automatically extracted - you can edit before uploading</p>
            </div>
            <button onclick="addNewPreviewItem()" style="background: #28a745; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                <i class="fas fa-plus"></i> Add Item
            </button>
        </div>
        
        <div style="overflow-x: auto;">
            <table style="width:100%; border-collapse: collapse; margin-bottom: 20px;" id="previewTable">
                <thead>
                    <tr style="background: #17a2b8; color: white;">
                        <th style="padding: 12px; text-align: left;">Item</th>
                        <th style="padding: 12px; width: 100px;">Quantity</th>
                        <th style="padding: 12px; width: 120px;">Unit Price</th>
                        <th style="padding: 12px; width: 120px;">Total</th>
                        <th style="padding: 12px; width: 50px;">Action</th>
                    </tr>
                </thead>
                <tbody id="previewTableBody">`;
    
    data.items.forEach((item, index) => {
        html += generateRowHtml(item, index);
    });
    
    html += `
                </tbody>
                <tfoot>
                    <tr style="background: #f8f9fa; font-weight: bold;">
                        <td colspan="3" style="padding: 12px; text-align: right;">Subtotal:</td>
                        <td id="previewSubtotalDisplay" style="padding: 12px; color: #28a745; text-align: right;">$${data.subtotal.toFixed(2)}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        
        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
            <button onclick="uploadToOdoo()" style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                <i class="fas fa-upload"></i> Upload to Odoo
            </button>
        </div>
    </div>`;
    
    return html;
}

// Helper to generate row HTML for both initial render and updates
function generateRowHtml(item, index) {
    const unitPrice = parseFloat(item.unitPrice) || 0;
    const qty = parseInt(item.quantity) || 0;
    return `
    <tr data-index="${index}" style="border-bottom: 1px solid #dee2e6;">
        <td style="padding: 10px;">
            <input type="text" value="${escapeHtml(item.name)}" 
                   style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                   onchange="updatePreviewItem(${index}, 'name', this.value)">
        </td>
        <td style="padding: 10px;">
            <input type="number" value="${qty}" min="1" step="1"
                   style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                   onchange="updatePreviewItem(${index}, 'quantity', this.value)">
        </td>
        <td style="padding: 10px;">
            <input type="number" value="${unitPrice.toFixed(2)}" min="0" step="0.01"
                   style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                   onchange="updatePreviewItem(${index}, 'unitPrice', this.value)">
        </td>
        <td style="padding: 10px; font-weight: bold; color: #28a745; text-align: right;">
            $${(qty * unitPrice).toFixed(2)}
        </td>
        <td style="padding: 10px; text-align: center;">
            <button onclick="removePreviewItem(${index})" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    </tr>`;
}

// ==================== PREVIEW EDIT FUNCTIONS ====================
window.addNewPreviewItem = function() {
    if (!previewData) return;
    previewData.items.push({
        name: "New Item",
        quantity: 1,
        unitPrice: 0.00
    });
    updatePreviewDisplay();
};

window.updatePreviewItem = function(index, field, value) {
    if (!previewData) return;
    
    if (field === 'name') {
        previewData.items[index].name = value;
    } else if (field === 'quantity') {
        previewData.items[index].quantity = parseInt(value) || 0;
    } else if (field === 'unitPrice') {
        previewData.items[index].unitPrice = parseFloat(value) || 0;
    }
    
    updatePreviewDisplay();
};

window.removePreviewItem = function(index) {
    if (!previewData) return;
    previewData.items.splice(index, 1);
    updatePreviewDisplay();
};

function updatePreviewDisplay() {
    if (!previewData) return;
    
    const tbody = document.getElementById('previewTableBody');
    const subtotalDisplay = document.getElementById('previewSubtotalDisplay');
    if (!tbody) return;
    
    // Recalculate subtotal
    previewData.subtotal = previewData.items.reduce((sum, item) => {
        return sum + (item.quantity * item.unitPrice);
    }, 0);
    
    // Re-render body
    let html = '';
    previewData.items.forEach((item, index) => {
        html += generateRowHtml(item, index);
    });
    tbody.innerHTML = html;
    
    // Update footer
    if (subtotalDisplay) {
        subtotalDisplay.textContent = `$${previewData.subtotal.toFixed(2)}`;
    }
}

// ==================== UPLOAD TO ODOO FUNCTION ====================
async function uploadToOdoo() {
    if (!previewData || previewData.items.length === 0) {
        alert('Please process a receipt first');
        return;
    }
    
    const odooPayload = {
        vendor_name: "Generic Vendor", 
        bill_date: new Date().toISOString().split('T')[0],
        invoice_lines: previewData.items.map(item => ({
            label: item.name,
            quantity: item.quantity,
            price_unit: item.unitPrice
        })),
        subtotal: previewData.subtotal,
        odoo_url: document.getElementById('odooUrl').value,
        odoo_db: document.getElementById('odooDb').value,
        odoo_username: document.getElementById('odooUsername').value,
        odoo_password: document.getElementById('odooPassword').value,
        original_image: currentImageData
    };
    
    loadingDiv.style.display = 'block';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading to Odoo...';
    
    try {
        const response = await fetch('/api/odoo/upload', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(odooPayload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Bill created in Odoo!';
            statusDiv.style.color = '#28a745';
            alert('✅ Bill successfully created in Odoo!');
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (error) {
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + error.message;
        statusDiv.style.color = '#dc3545';
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// ==================== TEST ODOO CONNECTION ====================
async function testOdooConnection() {
    const odooConfig = {
        odoo_url: odooUrl.value,
        odoo_db: odooDb.value,
        odoo_username: odooUsername.value,
        odoo_password: odooPassword.value
    };
    
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing Odoo connection...';
    statusDiv.style.color = '#17a2b8';
    
    try {
        const response = await fetch('/api/odoo/test-connection', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(odooConfig)
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Odoo connection successful!';
            statusDiv.style.color = '#28a745';
            alert('✅ Connected to Odoo successfully!');
        } else {
            throw new Error(result.error || 'Connection failed');
        }
    } catch (error) {
        console.error('❌ Odoo test error:', error);
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Odoo connection failed: ' + error.message;
        statusDiv.style.color = '#dc3545';
        alert('❌ Odoo connection failed: ' + error.message);
    }
}

// ==================== PROCESS FUNCTION ====================
async function processImage() {
    if (!currentImageData) {
        alert('Please select an image first');
        return;
    }
    
    loadingDiv.style.display = 'block';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing receipt...';
    statusDiv.style.color = '#17a2b8';
    resultsDiv.innerHTML = '';
    
    try {
        let imageData = currentImageData;
        if (imageData.includes('base64,')) {
            imageData = imageData.split('base64,')[1];
        }
        
        const response = await fetch('/api/process-receipt', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({image: imageData})
        });
        
        const data = await response.json();
        
        if (data.success) {
            extractedData = data.data;
            displaySideBySide(data.data);
            
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Receipt processed successfully!';
            statusDiv.style.color = '#28a745';
        } else {
            throw new Error(data.error || 'Processing failed');
        }
    } catch (error) {
        console.error('🔴 Process error:', error);
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error: ' + error.message;
        statusDiv.style.color = '#dc3545';
        resultsDiv.innerHTML = `<div class="error-message"><p>Error: ${escapeHtml(error.message)}</p></div>`;
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// ==================== FILE HANDLING FUNCTIONS ====================
function handleDrop(e) {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
}

function handleFileSelect(e) {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
}

async function handleFile(file) {
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading image...';
    statusDiv.style.color = '#17a2b8';
    
    try {
        const reader = new FileReader();
        reader.onload = async function(e) {
            currentImageData = e.target.result;
            previewImage.src = currentImageData;
            previewImage.style.display = 'block';
            previewOverlay.style.display = 'flex';
            processBtn.disabled = false;
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Image ready for processing';
            statusDiv.style.color = '#28a745';
        };
        reader.readAsDataURL(file);
    } catch (error) {
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Failed to load image';
        statusDiv.style.color = '#dc3545';
    }
}

function clearImagePreview() {
    previewImage.src = '';
    previewImage.style.display = 'none';
    previewOverlay.style.display = 'none';
    if (fileInput) fileInput.value = '';
    currentImageData = null;
    extractedData = null;
    previewData = null;
    processBtn.disabled = true;
    statusDiv.innerHTML = '<i class="fas fa-info-circle"></i> Ready to process receipt';
    statusDiv.style.color = '#1976d2';
    resultsDiv.innerHTML = '';
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(checkBackendHealth, 500);
    
    if (refreshBtn) refreshBtn.addEventListener('click', checkBackendHealth);
    if (testOdooBtn) testOdooBtn.addEventListener('click', testOdooConnection);
    if (dropZone) {
        dropZone.addEventListener('click', (e) => { if (!e.target.closest('#browseBtn')) fileInput.click(); });
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', handleDrop);
    }
    if (browseBtn) browseBtn.addEventListener('click', () => fileInput.click());
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);
    if (processBtn) processBtn.addEventListener('click', processImage);
    if (uploadOdooBtn) uploadOdooBtn.addEventListener('click', uploadToOdoo);
    if (clearPreview) clearPreview.addEventListener('click', clearImagePreview);
});

// Global functions
window.addNewPreviewItem = addNewPreviewItem;
window.updatePreviewItem = updatePreviewItem;
window.removePreviewItem = removePreviewItem;