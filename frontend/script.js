// script.js - ORIGINAL RECEIPT AND EXTRACTED TEXT SIDE BY SIDE
// Shows original receipt image next to ALL extracted text in a clean table

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    console.log('🔍 Checking DOM elements:');
    console.log('   uploadOdooBtn:', document.getElementById('uploadOdooBtn'));
    console.log('   processBtn:', document.getElementById('processBtn'));
    console.log('   resultsDiv:', document.getElementById('results'));
    
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const previewImage = document.getElementById('previewImage');
    const processBtn = document.getElementById('processBtn');
    const uploadOdooBtn = document.getElementById('uploadOdooBtn');
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const statusDiv = document.getElementById('status');
    const backendStatus = document.getElementById('backendStatus');
    const apiKeyStatus = document.getElementById('apiKeyStatus');
    const refreshBtn = document.getElementById('refreshStatusBtn');
    const clearPreview = document.getElementById('clearPreview');
    const previewOverlay = document.getElementById('previewOverlay');
    const browseBtn = document.querySelector('.btn-secondary'); // Get the browse button
    
    let currentImageData = null;
    let extractedData = null;
    let zoomLevel = 100;
    
    // Check backend health immediately
    checkBackendHealth();
    
    // Event Listeners - FIXED: Properly handle upload triggers
    if (dropZone) {
        // Only trigger file input when clicking on the dropZone background
        // But NOT when clicking on buttons inside it
        dropZone.addEventListener('click', function(e) {
            // Check if the click target is the button or its children
            if (e.target.closest('.btn-secondary')) {
                return; // Don't trigger file input if clicking the button
            }
            fileInput.click();
        });
        
        // Drag and drop events
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        dropZone.addEventListener('drop', handleDrop);
    }
    
    // Separate handler for the Browse Files button
    if (browseBtn) {
        browseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent event from bubbling up
            fileInput.click();
        });
    }
    
    // File input change handler
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    // Process button
    if (processBtn) {
        processBtn.addEventListener('click', processImage);
    }
    
    // Refresh button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', checkBackendHealth);
    }
    
    // Clear preview
    if (clearPreview) {
        clearPreview.addEventListener('click', clearImagePreview);
        if (previewOverlay) {
            previewOverlay.style.display = 'none';
        }
    }
    
    // Upload to Odoo button
    if (uploadOdooBtn) {
        console.log('✅ Adding click event listener to uploadOdooBtn');
        uploadOdooBtn.addEventListener('click', uploadToOdoo);
    } else {
        console.error('❌ uploadOdooBtn not found when trying to add listener');
    }
    
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
    
    function handleFile(file) {
        console.log('File selected:', file.name);
        
        const reader = new FileReader();
        reader.onload = function(e) {
            currentImageData = e.target.result;
            if (previewImage) {
                previewImage.src = currentImageData;
                previewImage.style.display = 'block';
            }
            if (previewOverlay) {
                previewOverlay.style.display = 'flex';
            }
            if (clearPreview) {
                clearPreview.parentElement.style.display = 'flex';
            }
            if (processBtn) processBtn.disabled = false;
            if (statusDiv) {
                statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> File ready for processing';
                statusDiv.style.color = '#28a745';
            }
        };
        reader.readAsDataURL(file);
    }
    
    function clearImagePreview() {
        if (previewImage) {
            previewImage.src = '';
            previewImage.style.display = 'none';
        }
        if (previewOverlay) {
            previewOverlay.style.display = 'none';
        }
        if (clearPreview) {
            clearPreview.parentElement.style.display = 'none';
        }
        if (fileInput) fileInput.value = '';
        currentImageData = null;
        extractedData = null;
        if (processBtn) processBtn.disabled = true;
        if (uploadOdooBtn) uploadOdooBtn.disabled = true;
        if (statusDiv) {
            statusDiv.innerHTML = '<i class="fas fa-info-circle"></i> Ready to process receipt';
            statusDiv.style.color = '#1976d2';
        }
        if (resultsDiv) resultsDiv.innerHTML = '';
        zoomLevel = 100;
    }
    
    async function checkBackendHealth() {
        if (!backendStatus) return;
        
        try {
            backendStatus.textContent = '⏳ Checking...';
            backendStatus.className = 'status-dot checking';
            if (apiKeyStatus) {
                apiKeyStatus.textContent = '⏳ Checking...';
                apiKeyStatus.className = 'status-dot checking';
            }
            
            const response = await fetch('/api/health');
            
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
    
    async function processImage() {
        if (!currentImageData) {
            alert('Please select an image first');
            return;
        }
        
        console.log('🔍 STEP 1: Starting processImage');
        console.log('   uploadOdooBtn before:', uploadOdooBtn?.disabled);
        
        if (loadingDiv) loadingDiv.style.display = 'block';
        if (statusDiv) {
            statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing receipt...';
            statusDiv.style.color = '#17a2b8';
        }
        if (resultsDiv) resultsDiv.innerHTML = '';
        
        try {
            let imageData = currentImageData;
            if (imageData.includes('base64,')) {
                imageData = imageData.split('base64,')[1];
            }
            
            console.log('🔍 STEP 2: Sending to API');
            const response = await fetch('/api/process-receipt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({image: imageData})
            });
            
            const data = await response.json();
            console.log('🔍 STEP 3: API Response:', data);
            
            if (data.success) {
                extractedData = data.data;
                console.log('🔍 STEP 4: Processing successful');
                
                displaySideBySide(data.data);
                
                if (statusDiv) {
                    statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Receipt processed successfully!';
                    statusDiv.style.color = '#28a745';
                }
                
                // ENABLE BUTTON
                console.log('🔍 STEP 5: Enabling upload button');
                if (uploadOdooBtn) {
                    uploadOdooBtn.disabled = false;
                    console.log('   uploadOdooBtn after:', uploadOdooBtn.disabled);
                    console.log('   button HTML:', uploadOdooBtn.outerHTML);
                    
                    // Double-check that the click event is attached
                    if (!uploadOdooBtn.hasAttribute('data-listener-attached')) {
                        console.log('   Attaching click listener to upload button');
                        uploadOdooBtn.addEventListener('click', uploadToOdoo);
                        uploadOdooBtn.setAttribute('data-listener-attached', 'true');
                    }
                } else {
                    console.error('🔴 uploadOdooBtn not found in DOM!');
                }
                
            } else {
                throw new Error(data.error || 'Processing failed');
            }
        } catch (error) {
            console.error('🔴 Process error:', error);
            if (statusDiv) {
                statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error: ' + error.message;
                statusDiv.style.color = '#dc3545';
            }
            if (resultsDiv) {
                resultsDiv.innerHTML = `<div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Error: ${escapeHtml(error.message)}</p>
                </div>`;
            }
        } finally {
            if (loadingDiv) loadingDiv.style.display = 'none';
            console.log('🔍 STEP 6: Process complete');
        }
    }
    
    // ============ SIDE BY SIDE DISPLAY - ORIGINAL IMAGE AND EXTRACTED TEXT ============
    function displaySideBySide(data) {
        if (!resultsDiv) return;
        
        const extractedText = data.text || '';
        const lines = extractedText.split('\n').filter(line => line.trim() !== '');
        
        // Parse lines to extract NAME and PRICE/Value
        const tableData = parseReceiptLines(lines);
        
        let html = `<div class="result-section">`;
        
        // Header with success message
        html += `<div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px 25px; border-radius: 15px; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between;">`;
        html += `<div style="display: flex; align-items: center; gap: 15px;">`;
        html += `<i class="fas fa-check-circle" style="font-size: 2.5rem;"></i>`;
        html += `<div>`;
        html += `<h3 style="color: white; margin: 0 0 5px 0;">✅ RECEIPT PROCESSED SUCCESSFULLY</h3>`;
        html += `<p style="color: white; margin: 0; opacity: 0.95;">${tableData.length} items extracted • Ready for comparison</p>`;
        html += `</div>`;
        html += `</div>`;
        html += `<span style="background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 50px; font-size: 0.9rem;"><i class="fas fa-robot"></i> ${data.model || 'AI Model'}</span>`;
        html += `</div>`;
        
        // ============ SIDE BY SIDE CONTAINER ============
        html += `<div style="display: flex; gap: 30px; margin: 30px 0; flex-wrap: wrap;">`;
        
        // LEFT COLUMN: Original Receipt Image
        html += `<div style="flex: 1; min-width: 300px; background: #f8f9fa; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border: 1px solid #e9ecef;">`;
        html += `<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #667eea;">`;
        html += `<i class="fas fa-image" style="font-size: 2rem; color: #667eea;"></i>`;
        html += `<div>`;
        html += `<h3 style="font-size: 1.3rem; color: #495057; margin: 0;">Original Receipt</h3>`;
        html += `<p style="color: #6c757d; font-size: 0.9rem; margin: 5px 0 0 0;">Uploaded image</p>`;
        html += `</div>`;
        html += `</div>`;
        
        html += `<div style="background: white; border-radius: 10px; padding: 20px; border: 1px solid #dee2e6; text-align: center;">`;
        html += `<img id="comparisonImage" src="${currentImageData}" alt="Original Receipt" style="max-width: 100%; max-height: 500px; border-radius: 8px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); transform: scale(${zoomLevel/100}); transform-origin: center; transition: transform 0.3s ease;">`;
        html += `<div style="display: flex; justify-content: center; gap: 10px; margin-top: 15px;">`;
        html += `<button class="zoom-btn" onclick="window.zoomImage(-10)"><i class="fas fa-search-minus"></i> Zoom Out</button>`;
        html += `<span style="padding: 5px 15px; background: #f8f9fa; border-radius: 5px;">${zoomLevel}%</span>`;
        html += `<button class="zoom-btn" onclick="window.zoomImage(10)"><i class="fas fa-search-plus"></i> Zoom In</button>`;
        html += `<button class="zoom-btn" onclick="window.zoomImage('reset')"><i class="fas fa-undo"></i> Reset</button>`;
        html += `</div>`;
        html += `</div>`;
        html += `</div>`;
        
        // RIGHT COLUMN: Extracted Text in Table Format with NAME and PRICE/Value
        html += `<div style="flex: 1.5; min-width: 500px; background: #f8f9fa; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border: 1px solid #e9ecef;">`;
        html += `<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #28a745;">`;
        html += `<i class="fas fa-table" style="font-size: 2rem; color: #28a745;"></i>`;
        html += `<div>`;
        html += `<h3 style="font-size: 1.3rem; color: #495057; margin: 0;">Receipt Items</h3>`;
        html += `<p style="color: #6c757d; font-size: 0.9rem; margin: 5px 0 0 0;">NAME and PRICE/Value</p>`;
        html += `</div>`;
        html += `</div>`;
        
        // Table with NAME and PRICE/Value columns
        html += `<div style="overflow-x: auto; max-height: 500px; overflow-y: auto; border: 2px solid #dee2e6; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">`;
        html += `<table style="width: 100%; border-collapse: collapse; background: white; font-size: 14px; border: 1px solid #dee2e6;">`;
        
        // Table Header - With line number column
        html += `<thead style="position: sticky; top: 0; background: linear-gradient(135deg, #4a6cf7 0%, #6f42c1 100%); color: white; z-index: 10;">`;
        html += `<tr>`;
        html += `<th style="padding: 15px 20px; text-align: center; font-weight: 600; font-size: 15px; width: 60px; border-right: 1px solid rgba(255,255,255,0.2);">#</th>`;
        html += `<th style="padding: 15px 20px; text-align: left; font-weight: 600; font-size: 15px; border-right: 1px solid rgba(255,255,255,0.2);">NAME</th>`;
        html += `<th style="padding: 15px 20px; text-align: right; font-weight: 600; font-size: 15px;">PRICE/Value</th>`;
        html += `</tr>`;
        html += `</thead>`;
        
        // Table Body - With alternating row colors
        html += `<tbody>`;
        
        tableData.forEach((item, index) => {
            const bgColor = index % 2 === 0 ? '#ffffff' : '#f2f2f2';
            
            html += `<tr style="background: ${bgColor}; border-bottom: 1px solid #dee2e6;">`;
            
            // Line number column
            html += `<td style="padding: 12px 20px; text-align: center; font-family: 'Courier New', monospace; font-size: 14px; border-right: 1px solid #dee2e6; color: #667eea; font-weight: 600;">`;
            html += item.number;
            html += `</td>`;
            
            // NAME column
            html += `<td style="padding: 12px 20px; text-align: left; font-family: 'Courier New', monospace; font-size: 14px; border-right: 1px solid #dee2e6; color: #212529;">`;
            html += escapeHtml(item.name);
            html += `</td>`;
            
            // PRICE/Value column
            html += `<td style="padding: 12px 20px; text-align: right; font-family: 'Courier New', monospace; font-size: 14px; font-weight: ${item.price !== 'N/A' ? '600' : '400'}; ${item.price !== 'N/A' ? 'color: #28a745;' : 'color: #6c757d;'}">`;
            html += item.price;
            html += `</td>`;
            
            html += `</tr>`;
        });
        
        html += `</tbody>`;
        html += `</table>`;
        html += `</div>`;
        
        // Statistics Footer
        html += `<div style="margin-top: 20px; display: flex; gap: 15px; justify-content: flex-end; font-size: 13px; color: #6c757d; border-top: 1px dashed #dee2e6; padding-top: 15px;">`;
        html += `<span><i class="fas fa-list-ol"></i> Total lines: ${tableData.length}</span>`;
        html += `<span><i class="fas fa-tag"></i> Items with prices: ${tableData.filter(item => item.price !== 'N/A').length}</span>`;
        html += `</div>`;
        
        html += `</div>`; // Close right column
        html += `</div>`; // Close flex container
        
        // Simple verification message
        html += `<div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 12px; padding: 15px 20px; margin: 20px 0; text-align: center; color: #6c757d;">`;
        html += `<i class="fas fa-check-circle" style="color: #28a745; margin-right: 8px;"></i> Verify that the extracted items match your receipt`;
        html += `</div>`;
        
        html += `</div>`; // Close result-section
        resultsDiv.innerHTML = html;
        
        // Add zoom functions to window
        window.zoomImage = function(amount) {
            const img = document.getElementById('comparisonImage');
            if (!img) return;
            
            if (amount === 'reset') {
                zoomLevel = 100;
            } else {
                zoomLevel = Math.max(50, Math.min(200, zoomLevel + amount));
            }
            
            img.style.transform = `scale(${zoomLevel/100})`;
            
            // Update zoom display
            const zoomDisplay = document.querySelector('.zoom-btn + span');
            if (zoomDisplay) {
                zoomDisplay.textContent = `${zoomLevel}%`;
            }
        };
    }
    
    // ============ CLEAN, DYNAMIC PARSE RECEIPT LINES FUNCTION - NO HARDCODING ============
  function parseReceiptLines(lines) {
    const tableData = [];
    let lineNumber = 1;

    lines.forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return;

        let name = trimmed;
        let value = "N/A";

        // =====================================================
        // 1️⃣ PHONE NUMBER DETECTION
        // =====================================================
        if (/ph|phone|tel/i.test(trimmed)) {

            // Extract ALL digits
            const digits = trimmed.replace(/\D/g, '');

            if (digits.length >= 7) {  // minimum phone length
                value = digits;
                name = trimmed.split(':')[0] + ':';
            }
        }

        // =====================================================
        // 2️⃣ NORMAL PRICE DETECTION (Take LAST number)
        // =====================================================
        else {
            const matches = [...trimmed.matchAll(/(\$?\d+[.,]?\d*\$?)/g)];

            if (matches.length > 0) {
                const lastMatch = matches[matches.length - 1][0];

                value = lastMatch;

                if (value.includes("$") && !value.startsWith("$")) {
                    value = "$" + value.replace("$", "");
                }

                const lastIndex = trimmed.lastIndexOf(lastMatch);
                name =
                    trimmed.substring(0, lastIndex) +
                    trimmed.substring(lastIndex + lastMatch.length);

                name = name.trim();
            }
        }

        name = name.replace(/\s+/g, " ").trim();

        tableData.push({
            number: lineNumber++,
            name: name,
            price: value
        });
    });

    return tableData;
}

    
    // ============ UPLOAD TO ODOO FUNCTION ============
    async function uploadToOdoo() {
        console.log('🚀 uploadToOdoo function called');
        
        if (!extractedData) {
            console.error('❌ No extracted data available');
            alert('Please process a receipt first');
            return;
        }
        
        console.log('📦 Extracted data:', extractedData);
        
        if (loadingDiv) loadingDiv.style.display = 'block';
        if (statusDiv) {
            statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading to Odoo...';
            statusDiv.style.color = '#17a2b8';
        }
        
        try {
            console.log('📡 Sending request to /api/odoo/upload');
            const response = await fetch('/api/odoo/upload', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({receipt_data: extractedData})
            });
            
            console.log('📥 Response status:', response.status);
            const result = await response.json();
            console.log('📦 Response data:', result);
            
            if (result.success) {
                // Show success message with link to Odoo
                if (statusDiv) {
                    statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Bill created in Odoo!';
                    statusDiv.style.color = '#28a745';
                }
                
                // Show Odoo bill link
                if (resultsDiv) {
                    resultsDiv.innerHTML += `
                        <div style="margin-top: 20px; padding: 20px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px;">
                            <h4 style="color: #155724; margin-bottom: 10px;">
                                <i class="fas fa-check-circle"></i> Bill Created Successfully!
                            </h4>
                            <p style="color: #155724; margin-bottom: 15px;">
                                Bill ID: <strong>${result.bill_id}</strong><br>
                                Bill Number: <strong>${result.bill_number || 'N/A'}</strong>
                            </p>
                            <a href="${result.bill_url}" target="_blank" style="background: #28a745; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; display: inline-block;">
                                <i class="fas fa-external-link-alt"></i> View in Odoo
                            </a>
                        </div>
                    `;
                }
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('❌ Upload error:', error);
            if (statusDiv) {
                statusDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Upload failed: ' + error.message;
                statusDiv.style.color = '#dc3545';
            }
            alert('Upload failed: ' + error.message);
        } finally {
            if (loadingDiv) loadingDiv.style.display = 'none';
        }
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});

// Helper function to force enable Odoo button (for debugging)
window.forceEnableOdooButton = function() {
    const uploadOdooBtn = document.getElementById('uploadOdooBtn');
    if (uploadOdooBtn) {
        uploadOdooBtn.disabled = false;
        console.log('✅ Button manually enabled');
        alert('Button should now be enabled! Try clicking it.');
    } else {
        console.error('❌ Button not found');
    }
};

// Helper function for zoom (needs to be in global scope)
window.zoomImage = function(amount) {
    const img = document.getElementById('comparisonImage');
    if (!img) return;
    console.log('Zoom:', amount);
};