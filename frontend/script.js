// ==================== COMPLETE script.js ====================

// ==================== FIX BACKEND CONNECTION ====================
const BACKEND_URL = 'http://192.168.1.11:5000';

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
let previewData = null;  // Store editable preview data
let zoomLevel = 100;

// Get DOM elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const previewImage = document.getElementById('previewImage');
const processBtn = document.getElementById('processBtn');
const uploadOdooBtn = document.getElementById('uploadOdooBtn');
const resultsDiv = document.getElementById('results');
const loadingDiv = document.getElementById('loading');
const statusDiv = document.getElementById('status');
const refreshBtn = document.getElementById('refreshStatusBtn');
const clearPreview = document.getElementById('clearPreview');
const previewOverlay = document.getElementById('previewOverlay');
const browseBtn = document.querySelector('.btn-secondary');

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

// ==================== PARSE RECEIPT LINES INTO TABLE ====================
function parseReceiptToTable(lines) {
    const tableData = [];
    
    lines.forEach((line, index) => {
        line = line.trim();
        if (!line) return;
        
        // Detect line type
        let type = 'text';
        let price = null;
        let hasPrice = false;
        
        // Check if line contains a price (number at end)
        const priceMatch = line.match(/(\d+[.,]?\d*)\s*$/);
        if (priceMatch) {
            price = priceMatch[1];
            hasPrice = true;
            
            // Check if it's likely an item (has letters) - FIXED: using JavaScript regex test instead of Python re.search
            if (/[A-Za-z]/.test(line)) {
                type = 'item';
            } else {
                type = 'price';
            }
        }
        
        // Check if it's a header
        if (line.includes('ALBETOS') || line.includes('MEXICAN') || 
            line.includes('ARTESIA') || line.includes('Ph:')) {
            type = 'header';
        }
        
        // Check if it's a summary
        if (line.toLowerCase().includes('subtotal') || 
            line.toLowerCase().includes('total') || 
            line.toLowerCase().includes('tax')) {
            type = 'summary';
        }
        
        tableData.push({
            id: index,
            line: line,
            type: type,
            price: price,
            hasPrice: hasPrice
        });
    });
    
    return tableData;
}

// ==================== EXTRACT ITEMS FOR ODOO PREVIEW ====================
function extractItemsForOdoo(lines) {
    const items = [];
    let subtotal = 0;
    
    // Find potential items and prices
    const potentialItems = [];
    const prices = [];
    
    lines.forEach(line => {
        line = line.trim();
        if (!line) return;
        
        // Skip headers and summaries
        if (line.includes('ALBETOS') || line.includes('MEXICAN') || 
            line.includes('ARTESIA') || line.includes('Ph:') ||
            line.toLowerCase().includes('subtotal') || 
            line.toLowerCase().includes('total') || 
            line.toLowerCase().includes('tax') ||
            line.toLowerCase().includes('atm $') ||
            line.toLowerCase().includes('recall')) {
            return;
        }
        
        // Check if this is a price line (just numbers)
        const cleanLine = line.replace(/[$,\s]/g, '');
        if (cleanLine.replace('.', '').match(/^\d+$/)) {
            prices.push(parseFloat(cleanLine));
            return;
        }
        
        // This might be an item
        if (line.match(/[A-Za-z]/)) {
            potentialItems.push(line);
        }
    });
    
    // Match items with prices
    potentialItems.forEach((item, index) => {
        if (index < prices.length) {
            const totalPrice = prices[index];
            
            // Check for quantity
            const qtyMatch = item.match(/^(\d+)\s+(.+)$/);
            if (qtyMatch) {
                const quantity = parseInt(qtyMatch[1]);
                let name = qtyMatch[2].trim();
                // Remove price from name if present
                name = name.replace(/\s*\d+[.,]?\d*\s*$/, '').replace(/[$]/g, '').trim();
                
                items.push({
                    id: items.length,
                    name: name,
                    quantity: quantity,
                    totalPrice: totalPrice,
                    unitPrice: totalPrice / quantity
                });
                subtotal += totalPrice;
            } else {
                // Simple item
                let name = item.replace(/\s*\d+[.,]?\d*\s*$/, '').replace(/[$]/g, '').trim();
                items.push({
                    id: items.length,
                    name: name || item,
                    quantity: 1,
                    totalPrice: totalPrice,
                    unitPrice: totalPrice
                });
                subtotal += totalPrice;
            }
        }
    });
    
    return { items, subtotal };
}

// ==================== DISPLAY FUNCTION WITH TABLE FORMAT ====================
function displaySideBySide(data) {
    if (!resultsDiv) return;
    
    const extractedText = data.text || '';
    const lines = extractedText.split('\n').filter(line => line.trim() !== '');
    const tableData = parseReceiptToTable(lines);
    const odooItems = extractItemsForOdoo(lines);
    previewData = odooItems; // Store for later editing
    
    let html = `
    <div class="result-section">
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
            <h3 style="margin:0;">✅ Receipt Processed Successfully</h3>
            <p style="margin:5px 0 0;">${lines.length} lines • ${odooItems.items.length} items detected</p>
        </div>
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 30px;">
            <!-- Left column - Original image -->
            <div style="flex: 1; min-width: 300px; background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #1976d2;">
                    <i class="fas fa-image"></i> Original Receipt
                </h4>
                <img src="${currentImageData}" style="width: 100%; height: auto; border: 1px solid #dee2e6; border-radius: 4px;">
            </div>
            
            <!-- Right column - Extracted text in table format -->
            <div style="flex: 2; min-width: 500px; background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #28a745;">
                    <i class="fas fa-table"></i> Extracted Text (Table View)
                </h4>
                <div style="max-height: 400px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px;">
                    <table style="width:100%; border-collapse: collapse; font-size: 14px;">
                        <thead style="position: sticky; top: 0; background: #343a40; color: white;">
                            <tr>
                                <th style="padding: 10px; width: 50px;">#</th>
                                <th style="padding: 10px; text-align: left;">Line Type</th>
                                <th style="padding: 10px; text-align: left;">Content</th>
                                <th style="padding: 10px; text-align: right;">Price</th>
                            </tr>
                        </thead>
                        <tbody>`;
    
    // Add each line to table with color coding
    tableData.forEach(row => {
        let bgColor = '#ffffff';
        let typeColor = '';
        
        if (row.type === 'header') {
            bgColor = '#e3f2fd';  // Light blue
            typeColor = '#1976d2';
        } else if (row.type === 'item') {
            bgColor = '#f0fff0';  // Light green
            typeColor = '#28a745';
        } else if (row.type === 'summary') {
            bgColor = '#fff3cd';  // Light yellow
            typeColor = '#856404';
        } else if (row.type === 'price') {
            bgColor = '#fff5f5';  // Light red
            typeColor = '#dc3545';
        }
        
        html += `<tr style="background: ${bgColor}; border-bottom: 1px solid #dee2e6;">
            <td style="padding: 8px; text-align: center;">${row.id + 1}</td>
            <td style="padding: 8px; color: ${typeColor}; font-weight: 500;">${row.type}</td>
            <td style="padding: 8px; font-family: monospace;">${escapeHtml(row.line)}</td>
            <td style="padding: 8px; text-align: right; ${row.hasPrice ? 'font-weight: bold; color: #28a745;' : ''}">${row.price ? '$' + row.price : ''}</td>
        </tr>`;
    });
    
    html += `</tbody>
                    </table>
                </div>
            </div>
        </div>`;
    
    // Add editable preview section
    html += displayEditablePreview(odooItems);
    
    resultsDiv.innerHTML = html;
}

// ==================== EDITABLE PREVIEW FUNCTION ====================
function displayEditablePreview(data) {
    let html = `
    <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
        <h4 style="margin-top: 0; color: #17a2b8;">
            <i class="fas fa-edit"></i> Preview & Edit Data for Odoo
        </h4>
        <p style="color: #6c757d; margin-bottom: 20px;">Review and edit the items before uploading to Odoo</p>
        
        <div style="overflow-x: auto;">
            <table style="width:100%; border-collapse: collapse; margin-bottom: 20px;" id="previewTable">
                <thead>
                    <tr style="background: #17a2b8; color: white;">
                        <th style="padding: 12px;">Item</th>
                        <th style="padding: 12px;">Quantity</th>
                        <th style="padding: 12px;">Unit Price</th>
                        <th style="padding: 12px;">Total</th>
                        <th style="padding: 12px;">Action</th>
                    </tr>
                </thead>
                <tbody id="previewTableBody">`;
    
    data.items.forEach((item, index) => {
        html += `
        <tr data-index="${index}" style="border-bottom: 1px solid #dee2e6;">
            <td style="padding: 10px;">
                <input type="text" value="${escapeHtml(item.name)}" 
                       style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                       onchange="updatePreviewItem(${index}, 'name', this.value)">
            </td>
            <td style="padding: 10px;">
                <input type="number" value="${item.quantity}" min="1" step="1"
                       style="width: 80px; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                       onchange="updatePreviewItem(${index}, 'quantity', this.value)">
            </td>
            <td style="padding: 10px;">
                <input type="number" value="${item.unitPrice.toFixed(2)}" min="0" step="0.01"
                       style="width: 100px; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                       onchange="updatePreviewItem(${index}, 'unitPrice', this.value)">
            </td>
            <td style="padding: 10px; font-weight: bold; color: #28a745;">
                $${(item.quantity * item.unitPrice).toFixed(2)}
            </td>
            <td style="padding: 10px;">
                <button onclick="removePreviewItem(${index})" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>`;
    });
    
    html += `
                </tbody>
                <tfoot>
                    <tr style="background: #f8f9fa; font-weight: bold;">
                        <td colspan="3" style="padding: 12px; text-align: right;">Subtotal:</td>
                        <td style="padding: 12px; color: #28a745;">$${data.subtotal.toFixed(2)}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        
        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
            <button onclick="addPreviewItem()" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-plus"></i> Add Item
            </button>
            <button onclick="uploadToOdoo()" style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-upload"></i> Upload to Odoo
            </button>
        </div>
    </div>`;
    
    return html;
}

// ==================== PREVIEW EDIT FUNCTIONS ====================
window.updatePreviewItem = function(index, field, value) {
    if (!previewData) return;
    
    if (field === 'name') {
        previewData.items[index].name = value;
    } else if (field === 'quantity') {
        previewData.items[index].quantity = parseInt(value) || 1;
    } else if (field === 'unitPrice') {
        previewData.items[index].unitPrice = parseFloat(value) || 0;
    }
    
    // Recalculate subtotal
    previewData.subtotal = previewData.items.reduce((sum, item) => {
        return sum + (item.quantity * item.unitPrice);
    }, 0);
    
    // Update the total display
    updatePreviewDisplay();
};

window.removePreviewItem = function(index) {
    if (!previewData) return;
    
    previewData.items.splice(index, 1);
    previewData.subtotal = previewData.items.reduce((sum, item) => {
        return sum + (item.quantity * item.unitPrice);
    }, 0);
    
    updatePreviewDisplay();
};

window.addPreviewItem = function() {
    if (!previewData) return;
    
    previewData.items.push({
        id: previewData.items.length,
        name: 'New Item',
        quantity: 1,
        unitPrice: 0
    });
    
    updatePreviewDisplay();
};

function updatePreviewDisplay() {
    if (!previewData) return;
    
    const tbody = document.getElementById('previewTableBody');
    if (!tbody) return;
    
    let html = '';
    previewData.items.forEach((item, index) => {
        html += `
        <tr data-index="${index}" style="border-bottom: 1px solid #dee2e6;">
            <td style="padding: 10px;">
                <input type="text" value="${escapeHtml(item.name)}" 
                       style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                       onchange="updatePreviewItem(${index}, 'name', this.value)">
            </td>
            <td style="padding: 10px;">
                <input type="number" value="${item.quantity}" min="1" step="1"
                       style="width: 80px; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                       onchange="updatePreviewItem(${index}, 'quantity', this.value)">
            </td>
            <td style="padding: 10px;">
                <input type="number" value="${item.unitPrice.toFixed(2)}" min="0" step="0.01"
                       style="width: 100px; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                       onchange="updatePreviewItem(${index}, 'unitPrice', this.value)">
            </td>
            <td style="padding: 10px; font-weight: bold; color: #28a745;">
                $${(item.quantity * item.unitPrice).toFixed(2)}
            </td>
            <td style="padding: 10px;">
                <button onclick="removePreviewItem(${index})" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>`;
    });
    
    tbody.innerHTML = html;
    
    // Update subtotal in footer
    const foot = document.querySelector('#previewTable tfoot td:nth-child(2)');
    if (foot) {
        foot.textContent = `$${previewData.subtotal.toFixed(2)}`;
    }
}

// ==================== OVERRIDE UPLOAD FUNCTION ====================
async function uploadToOdoo() {
    if (!previewData) {
        alert('Please process a receipt first');
        return;
    }
    
    if (previewData.items.length === 0) {
        alert('No items to upload');
        return;
    }
    
    loadingDiv.style.display = 'block';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading to Odoo...';
    statusDiv.style.color = '#17a2b8';
    
    try {
        // Prepare data from preview
        const odooData = {
            ...extractedData,
            formatted_data: {
                ...extractedData?.formatted_data,
                invoice_lines: previewData.items.map(item => ({
                    label: item.name,
                    quantity: item.quantity,
                    price_unit: item.unitPrice
                })),
                subtotal: previewData.subtotal,
                total_amount: previewData.subtotal
            }
        };
        
        const response = await fetch('/api/odoo/upload', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                receipt_data: odooData,
                original_image: currentImageData
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Bill created in Odoo!';
            statusDiv.style.color = '#28a745';
            
            resultsDiv.innerHTML += `
                <div style="margin-top: 20px; padding: 20px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px;">
                    <h4 style="color: #155724; margin-bottom: 10px;">✅ Bill Created Successfully!</h4>
                    <p style="color: #155724; margin-bottom: 15px;">
                        Bill ID: <strong>${result.bill_id}</strong><br>
                        Bill Number: <strong>${result.bill_number || 'N/A'}</strong>
                    </p>
                    <a href="${result.bill_url}" target="_blank" style="background: #28a745; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; display: inline-block;">
                        View in Odoo
                    </a>
                </div>
            `;
            
            uploadOdooBtn.disabled = true;
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (error) {
        console.error('❌ Upload error:', error);
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Upload failed: ' + error.message;
        statusDiv.style.color = '#dc3545';
        alert('Upload failed: ' + error.message);
    } finally {
        loadingDiv.style.display = 'none';
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
            console.log('📝 RAW TEXT FROM VLM:', data.data.text);
            
            extractedData = data.data;
            displaySideBySide(data.data);
            
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Receipt processed successfully!';
            statusDiv.style.color = '#28a745';
            
            if (uploadOdooBtn) {
                uploadOdooBtn.disabled = false;
            }
        } else {
            throw new Error(data.error || 'Processing failed');
        }
    } catch (error) {
        console.error('🔴 Process error:', error);
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error: ' + error.message;
        statusDiv.style.color = '#dc3545';
        resultsDiv.innerHTML = `<div class="error-message">
            <i class="fas fa-exclamation-circle"></i>
            <p>Error: ${escapeHtml(error.message)}</p>
        </div>`;
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
    console.log('📁 File selected:', file.name);
    
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading image...';
    statusDiv.style.color = '#17a2b8';
    
    try {
        const reader = new FileReader();
        reader.onload = async function(e) {
            currentImageData = e.target.result;
            
            previewImage.src = currentImageData;
            previewImage.style.display = 'block';
            previewOverlay.style.display = 'flex';
            clearPreview.parentElement.style.display = 'flex';
            processBtn.disabled = false;
            
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Image ready for processing';
            statusDiv.style.color = '#28a745';
        };
        reader.readAsDataURL(file);
    } catch (error) {
        console.error('❌ Error in handleFile:', error);
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Failed to load image';
        statusDiv.style.color = '#dc3545';
    }
}

function clearImagePreview() {
    previewImage.src = '';
    previewImage.style.display = 'none';
    previewOverlay.style.display = 'none';
    clearPreview.parentElement.style.display = 'none';
    if (fileInput) fileInput.value = '';
    currentImageData = null;
    extractedData = null;
    previewData = null;
    processBtn.disabled = true;
    uploadOdooBtn.disabled = true;
    statusDiv.innerHTML = '<i class="fas fa-info-circle"></i> Ready to process receipt';
    statusDiv.style.color = '#1976d2';
    resultsDiv.innerHTML = '';
    zoomLevel = 100;
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM Content Loaded - Initializing...');
    
    setTimeout(checkBackendHealth, 500);
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function(e) {
            e.preventDefault();
            checkBackendHealth();
        });
    }
    
    if (dropZone) {
        dropZone.addEventListener('click', function(e) {
            if (e.target.closest('.btn-secondary')) return;
            fileInput.click();
        });
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', handleDrop);
    }
    
    if (browseBtn) {
        browseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    if (processBtn) {
        processBtn.addEventListener('click', processImage);
    }
    
    if (uploadOdooBtn) {
        uploadOdooBtn.addEventListener('click', uploadToOdoo);
    }
    
    if (clearPreview) {
        clearPreview.addEventListener('click', clearImagePreview);
        if (previewOverlay) previewOverlay.style.display = 'none';
    }
});

// ==================== ZOOM FUNCTION ====================
window.zoomImage = function(amount) {
    const img = document.getElementById('comparisonImage');
    if (!img) return;
    
    if (amount === 'reset') {
        zoomLevel = 100;
    } else {
        zoomLevel = Math.max(50, Math.min(200, zoomLevel + amount));
    }
    
    img.style.transform = `scale(${zoomLevel/100})`;
    img.style.transformOrigin = 'top left';
};

// Make functions globally available
window.checkBackendHealth = checkBackendHealth;
window.processImage = processImage;
window.uploadToOdoo = uploadToOdoo;
window.clearImagePreview = clearImagePreview;