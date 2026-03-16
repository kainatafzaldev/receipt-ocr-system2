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

// ADD THIS: Global variable to store receipt data for Odoo
window.lastProcessedReceipt = null;

// Get DOM elements - FIXED IDs to match HTML
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

// FIXED: Use the correct IDs from HTML
const odoUrl = document.getElementById('odoOurl');  // Note: odoOurl not odooUrl
const odoDb = document.getElementById('odoDb');
const odoUsername = document.getElementById('odoUsername');
const odoPassword = document.getElementById('odoPassword');

// ==================== PHONE NUMBER DETECTION ====================
function isPhoneNumber(text) {
    if (!text) return false;
    
    // Common phone number patterns
    const patterns = [
        /^\+?\d{1,4}[-.\s]?\d{3,4}[-.\s]?\d{4,5}$/,  // International
        /^\(\d{3}\)\s*\d{3}[-\s]?\d{4}$/,            // (123) 456-7890
        /^\d{3}[-\s]\d{3}[-\s]\d{4}$/,               // 123-456-7890
        /^\d{3}[-\s]\d{4}$/,                          // 123-4567
        /^\+?\d{10,15}$/,                             // Just digits, 10-15 long
    ];
    
    for (let pattern of patterns) {
        if (pattern.test(text.trim())) {
            return true;
        }
    }
    
    // Check if it's mostly numbers
    const digits = (text.match(/\d/g) || []).length;
    const letters = (text.match(/[a-zA-Z]/g) || []).length;
    
    // If more digits than letters and at least 7 digits, likely a phone
    if (digits > letters && digits >= 7 && letters < 3) {
        return true;
    }
    
    // Check for common phone keywords
    const lower = text.toLowerCase();
    if (lower.includes('tel:') || lower.includes('phone:') || lower.includes('fax:')) {
        return true;
    }
    
    return false;
}

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

// ==================== UPDATED DISPLAY FUNCTION - FILTERED PREVIEW ====================
function displaySideBySide(data) {
    if (!resultsDiv) return;
    
    // Store the receipt data globally for Odoo upload
    window.lastProcessedReceipt = {
        text: data.text,
        formatted_data: data.formatted_data || {},
        vlm_model: data.vlm_model,
        tokens_used: data.tokens_used
    };
    
    console.log("✅ Stored receipt data for Odoo:", window.lastProcessedReceipt);
    
    const extractedText = data.text || '';
    const lines = extractedText.split('\n').filter(line => line.trim() !== '');
    
    // Create preview with ONLY real items (filtered)
    const odooPreview = createFilteredPreview(lines);
    previewData = odooPreview;
    
    let html = `
    <div class="result-section">
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
            <h3 style="margin:0;">✅ Receipt Processed Successfully</h3>
            <p style="margin:5px 0 0;">${lines.length} lines detected, ${odooPreview.items.length} items found</p>
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
    
    html += displayFilteredPreview(odooPreview);
    resultsDiv.innerHTML = html;
    
    // Enable upload button after successful processing
    if (uploadOdooBtn) {
        uploadOdooBtn.disabled = false;
    }
}

// ==================== CREATE FILTERED PREVIEW - CORRECT DISCOUNT HANDLING ====================
function createFilteredPreview(lines) {
    const items = [];
    let subtotal = 0;
    
    // Keywords that indicate NON-ITEMS (to exclude from preview)
    const EXCLUDE_KEYWORDS = [
        'subtotal', 'tax', 'total', 'balance', 'amount due', 'cash', 'change', 'Tel',
        'tel','phone','fax','email','www','.com','address','date','Date','time','Time','total',
        'Total','road','street','blvd','avenue','drive','city','state','zip','table','server',
        'cashier','guest','party','order #','receipt #','check #'
        ,'tab #','ticket #','subtotal','tax','total','balance','cash','change',
        'debit','visa','mastercard','amex','payment','thank you',
        'welcome','tip','gratuity','tip guide','please come again',
        'credit', 'debit', 'visa', 'mastercard', 'amex', 'payment', 'tender',
        'server:', 'cashier:', 'table:', 'order #', 'receipt #', 'phone:',
        'www.', '.com', 'thank you', 'welcome', 'address', 'road', 'street',
        'blvd', 'avenue', 'albetos', 'mexican', 'grill', 'restaurant', 'cafe',
        'ph:', 'tel:', 'phone:', 'fax:', 'email:', 'web:', 'website:'
    ];
    
    // Discount indicators (lowercase for case-insensitive matching)
    const DISCOUNT_INDICATORS = ['%off', 'off ', 'discount', 'birthday', 'promo', 'save'];
    
    lines.forEach((line, index) => {
        const originalLine = line;
        line = line.trim();
        const lineLower = line.toLowerCase();
        
        // Skip if line contains any excluded keyword
        for (let keyword of EXCLUDE_KEYWORDS) {
            if (lineLower.includes(keyword)) {
                console.log(`⏭️ Preview skipping: ${line} (contains '${keyword}')`);
                return;
            }
        }
        
        // ADD THIS - Skip phone numbers
        if (isPhoneNumber(line)) {
            console.log(`⏭️ Preview skipping phone number: ${line}`);
            return;
        }
        
        // Also skip lines that are mostly numbers
        const digitCount = (line.match(/\d/g) || []).length;
        const totalChars = line.length;
        if (digitCount > 0 && digitCount / totalChars > 0.4) {
            // Skip if more than 40% of the line is digits (likely a phone/ID)
            console.log(`⏭️ Preview skipping numeric line: ${line} (${digitCount}/${totalChars} digits)`);
            return;
        }
        
        // Check if line contains discount indicators
        const hasDiscountIndicator = DISCOUNT_INDICATORS.some(indicator => 
            lineLower.includes(indicator)
        );
        
        // Check if line contains negative numbers (like -0.50 or -14.94)
        const hasNegativeNumber = line.includes('-');
        
        // This is a discount line if it has discount indicators OR negative numbers
        const isDiscount = hasDiscountIndicator || hasNegativeNumber;
        
        // Extract all numbers from the line (including negatives)
        const numbers = line.match(/-?\d+\.?\d*/g) || [];
        if (numbers.length === 0) return;
        
        // Log for debugging
        console.log(`Processing line: "${line}"`);
        console.log(`  Numbers found: ${numbers.join(', ')}`);
        console.log(`  isDiscount: ${isDiscount}`);
        
        // For regular items, always use positive numbers
        // For discounts, preserve negativity
        
        let price = 0;
        let quantity = 1;
        let name = line;
        
        // Try to find quantity (first number if line starts with a number)
        const qtyMatch = line.match(/^(\d+)\s+(.+)$/);
        if (qtyMatch) {
            quantity = parseInt(qtyMatch[1]);
            name = qtyMatch[2].trim();
            
            // Get the last number as price
            const lastNumber = numbers[numbers.length - 1];
            price = parseFloat(lastNumber);
            
            // For regular items, ensure price is positive
            if (!isDiscount) {
                price = Math.abs(price);
            }
        } else {
            // No quantity at start, just name and price
            name = line.replace(/\s*[-\d]+\.?\d*\s*$/, '').trim();
            
            // Get the last number as price
            const lastNumber = numbers[numbers.length - 1];
            price = parseFloat(lastNumber);
            
            // For regular items, ensure price is positive
            if (!isDiscount) {
                price = Math.abs(price);
            }
        }
        
        // Clean up name - remove any trailing numbers
        name = name.replace(/\s*\d+[.,]?\d*\s*$/, '').trim();
        
        // If name is empty, use a placeholder
        if (!name || name.length < 2) {
            if (isDiscount) {
                name = 'Discount';
            } else {
                name = `Item ${index + 1}`;
            }
        }
        
        // Calculate unit price
        const unitPrice = quantity > 0 ? price / quantity : price;
        
        items.push({
            name: name,
            quantity: quantity,
            unitPrice: unitPrice,
            isDiscount: isDiscount
        });
        
        subtotal += price;
        
        console.log(`  Added item: ${name}, qty: ${quantity}, price: ${price}, isDiscount: ${isDiscount}`);
    });
    
    // If no items found, show message
    if (items.length === 0) {
        items.push({
            name: 'No valid items found - please check raw text',
            quantity: 0,
            unitPrice: 0,
            isDiscount: false
        });
    }
    
    console.log('Final items:', items);
    console.log('Subtotal:', subtotal);
    
    return { items, subtotal };
}

// ==================== FILTERED EDITABLE PREVIEW ====================
function displayFilteredPreview(data) {
    if (data.items.length === 0 || (data.items.length === 1 && data.items[0].name.includes('No valid items'))) {
        return `
        <div style="background: #fff3cd; border: 1px solid #ffeeba; border-radius: 8px; padding: 20px; margin-top: 20px;">
            <h4 style="color: #856404; margin-top: 0;"><i class="fas fa-exclamation-triangle"></i> No Items Found</h4>
            <p>No valid items could be automatically detected. Please check the raw text above or upload a clearer receipt.</p>
        </div>`;
    }
    
    let html = `
    <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <h4 style="margin: 0; color: #17a2b8;">
                    <i class="fas fa-edit"></i> Detected Items (Edit if needed)
                </h4>
                <p style="color: #6c757d; margin: 5px 0 0;">Headers, taxes, totals, and phone numbers are automatically filtered out</p>
            </div>
            <button onclick="window.addNewPreviewItem()" style="background: #28a745; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold;">
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
                        <td id="previewSubtotalDisplay" style="padding: 12px; color: ${data.subtotal < 0 ? '#e74c3c' : '#28a745'}; text-align: right;">$${data.subtotal.toFixed(2)}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        
        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
            <button onclick="window.uploadToOdoo()" style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                <i class="fas fa-upload"></i> Upload to Odoo
            </button>
        </div>
    </div>`;
    
    return html;
}

// Helper to generate row HTML with discount support
function generateRowHtml(item, index) {
    const unitPrice = parseFloat(item.unitPrice) || 0;
    const qty = parseInt(item.quantity) || 0;
    const total = qty * unitPrice;
    const isDiscount = item.isDiscount || false;
    
    return `
    <tr data-index="${index}" style="border-bottom: 1px solid #dee2e6; ${isDiscount ? 'background-color: #fff5f5;' : ''}">
        <td style="padding: 10px;">
            <input type="text" value="${escapeHtml(item.name)}" 
                   style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                   onchange="window.updatePreviewItem(${index}, 'name', this.value)">
        </td>
        <td style="padding: 10px;">
            <input type="number" value="${qty}" min="0" step="1"
                   style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
                   onchange="window.updatePreviewItem(${index}, 'quantity', this.value)">
        </td>
        <td style="padding: 10px;">
            <input type="number" value="${unitPrice.toFixed(2)}" step="0.01"
                   style="width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 4px; ${unitPrice < 0 ? 'color: #e74c3c; font-weight: bold;' : ''}"
                   onchange="window.updatePreviewItem(${index}, 'unitPrice', this.value)">
        </td>
        <td style="padding: 10px; font-weight: bold; ${unitPrice < 0 ? 'color: #e74c3c;' : 'color: #28a745;'} text-align: right;">
            ${unitPrice < 0 ? '-$' : '$'}${Math.abs(total).toFixed(2)}
        </td>
        <td style="padding: 10px; text-align: center;">
            <button onclick="window.removePreviewItem(${index})" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
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
        unitPrice: 0.00,
        isDiscount: false
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
    
    // Update footer with color based on value
    if (subtotalDisplay) {
        subtotalDisplay.textContent = `$${previewData.subtotal.toFixed(2)}`;
        subtotalDisplay.style.color = previewData.subtotal < 0 ? '#e74c3c' : '#28a745';
    }
}

window.uploadToOdoo = async function() {
    // Use previewData (what you edited) instead of lastProcessedReceipt
    if (!previewData || previewData.items.length === 0) {
        alert('❌ No items to upload. Please process a receipt first.');
        return;
    }
    
    const uploadBtn = document.getElementById('uploadOdooBtn');
    const originalText = uploadBtn.innerHTML;
    
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    uploadBtn.disabled = true;
    loadingDiv.style.display = 'block';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading to Odoo...';
    
    try {
        // Prepare data from the EDITED preview
        const odooData = {
            vendor_name: 'Unknown Vendor',
            bill_date: new Date().toISOString().split('T')[0],
            invoice_lines: previewData.items.map(item => ({
                label: item.name,
                quantity: item.quantity,
                price_unit: item.unitPrice
            }))
        };
        
        const odooPayload = {
            receipt_data: odooData,
            original_image: currentImageData,
            odoo_url: odoUrl.value,
            odoo_db: odoDb.value,
            odoo_username: odoUsername.value,
            odoo_password: odoPassword.value
        };
        
        console.log("📤 Uploading EDITED preview data:", odooData);
        
        const response = await fetch('/api/odoo/upload', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(odooPayload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            const odooBase = odoUrl.value || 'https://kainatcecos4.odoo.com';
            const fallbackUrl = `${odooBase.replace(/\/$/, '')}/web#id=${result.bill_id}&model=account.move`;
            const billUrl = result.bill_url || fallbackUrl;
            
            const message = `
                <div style="text-align: center; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <i class="fas fa-check-circle" style="color: #28a745; font-size: 64px; margin-bottom: 15px;"></i>
                    <h3 style="color: #28a745; margin: 10px 0;">Bill Created Successfully!</h3>
                    <p style="font-size: 16px;">Bill ID: <strong>${result.bill_id}</strong></p>
                    <p style="color: #6c757d;">Items uploaded: ${previewData.items.length}</p>
                    <a href="${billUrl}" target="_blank" 
                       style="display: inline-block; background: #007bff; color: white; 
                              padding: 12px 25px; text-decoration: none; border-radius: 5px;
                              margin: 15px 0; font-weight: bold;">
                        <i class="fas fa-external-link-alt"></i> View Bill in Odoo
                    </a>
                    <p style="color: #6c757d; margin-top: 15px; font-size: 0.9em;">
                        Your edited preview has been uploaded exactly as shown.
                    </p>
                </div>
            `;
            
            resultsDiv.innerHTML = message;
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Bill created in Odoo!';
            statusDiv.style.color = '#28a745';
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + error.message;
        statusDiv.style.color = '#dc3545';
        alert('❌ Upload failed: ' + error.message);
    } finally {
        uploadBtn.innerHTML = originalText;
        uploadBtn.disabled = false;
        loadingDiv.style.display = 'none';
    }
};

// ==================== TEST ODOO CONNECTION ====================
window.testOdooConnection = async function() {
    // Check if elements exist
    if (!odoUrl || !odoDb || !odoUsername || !odoPassword) {
        alert('Odoo configuration elements not found');
        return;
    }
    
    const odooConfig = {
        odoo_url: odoUrl.value,
        odoo_db: odoDb.value,
        odoo_username: odoUsername.value,
        odoo_password: odoPassword.value
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
};

// ==================== PROCESS FUNCTION ====================
async function processImage() {
    if (!currentImageData) {
        alert('Please select an image first');
        return;
    }
    
    loadingDiv.style.display = 'block';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing receipt...';
    
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
            displaySideBySide(data.data);
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Receipt processed successfully!';
            statusDiv.style.color = '#28a745';
        } else {
            throw new Error(data.error || 'Processing failed');
        }
    } catch (error) {
        statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error: ' + error.message;
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
    window.lastProcessedReceipt = null;
    processBtn.disabled = true;
    if (uploadOdooBtn) uploadOdooBtn.disabled = true;
    statusDiv.innerHTML = '<i class="fas fa-info-circle"></i> Ready to process receipt';
    statusDiv.style.color = '#1976d2';
    resultsDiv.innerHTML = '';
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    setTimeout(checkBackendHealth, 500);
    
    // Add event listeners
    if (refreshBtn) refreshBtn.addEventListener('click', checkBackendHealth);
    if (testOdooBtn) testOdooBtn.addEventListener('click', window.testOdooConnection);
    if (uploadOdooBtn) uploadOdooBtn.addEventListener('click', window.uploadToOdoo);
    
    if (dropZone) {
        dropZone.addEventListener('click', (e) => { 
            if (!e.target.closest('#browseBtn')) fileInput.click(); 
        });
        dropZone.addEventListener('dragover', (e) => { 
            e.preventDefault(); 
            dropZone.classList.add('dragover'); 
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', handleDrop);
    }
    
    if (browseBtn) browseBtn.addEventListener('click', () => fileInput.click());
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);
    if (processBtn) processBtn.addEventListener('click', processImage);
    if (clearPreview) clearPreview.addEventListener('click', clearImagePreview);
    
    console.log('Initialization complete');
});

// Make functions globally available
window.addNewPreviewItem = addNewPreviewItem;
window.updatePreviewItem = updatePreviewItem;
window.removePreviewItem = removePreviewItem;
window.uploadToOdoo = uploadToOdoo;
window.testOdooConnection = testOdooConnection;