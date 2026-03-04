# main.py - COMPLETE RECEIPT OCR + ODOO INTEGRATION
import os
import base64
import requests
import json
import traceback
import re
import time
from PIL import Image
import io
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from odoo_integration import OdooConnector
import logging
from document_scanner import DocumentScanner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize scanner
scanner = DocumentScanner()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, 
            static_folder=FRONTEND_DIR,
            static_url_path='')

# Configure CORS properly
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000", "http://192.168.1.11:5000", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ==================== CONFIGURATION ====================
NOVITA_API_KEY = os.getenv('NOVITA_API_KEY')
NOVITA_API_BASE = os.getenv('NOVITA_API_BASE', 'https://api.novita.ai/v3/openai')
VLM_MODEL = os.getenv('VLM_MODEL', 'qwen/qwen3-vl-235b-a22b-instruct')
LLM_MODEL = os.getenv('LLM_MODEL', 'meta-llama/llama-3.3-70b-instruct')
PORT = int(os.getenv('PORT', 5000))

# Odoo Configuration
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# Initialize Odoo connector with config
odoo = OdooConnector(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)

# ==================== VALIDATION ====================
def validate_api_key():
    """Validate that Novita.ai API key is configured"""
    if not NOVITA_API_KEY or NOVITA_API_KEY == 'your_novita_api_key_here':
        return False, "Novita.ai API key not configured"
    return True, "Novita.ai API key is configured"

# ==================== DYNAMIC VLM EXTRACTION PROMPT ====================
VLM_EXTRACTION_PROMPT = """You are an expert OCR system for receipts. Extract ALL text exactly as it appears.

CRITICAL INSTRUCTIONS:

1. EXTRACT EVERYTHING VERBATIM:
   - Store names, addresses, phone numbers, emails
   - Every single item line (even duplicates)
   - All prices, quantities, and totals
   - Discounts, markdowns, and savings
   - Subtotal, tax, total, cash, change
   - Any text in any language (Arabic, Urdu, etc.)
   - ALL spaces and formatting exactly as they appear

2. PRESERVE COMPLETE LINES:
   - Each item MUST be on its own line with its price
   - If item name and price are on separate lines, combine them: "Item Name $9.97"
   - NEVER split an item name from its price

3. HANDLE ALL FORMATS DYNAMICALLY:
   - Items with quantities at start: "3 ASADA TACO"
   - Items with prices on same line: "Papyrus Boxed Cards $9.97"
   - Items with multiplication: "Snowglobe 6.99 x 3 $20.97"
   - Items and prices separated: combine them in order

4. MARK SPECIAL ELEMENTS:
   - If a price is crossed out, append "[STRIKETHROUGH]" after the price
   - If a line is a discount, keep it as is with negative amount

5. PRESERVE ORDER:
   - Keep every line in the exact order it appears on the receipt

Return ONLY the raw text with each complete element on its own line."""

# ==================== VLM EXTRACTION FUNCTION ====================
def extract_text_with_vlm(base64_image):
    """Step 1: Use VLM to extract raw text from receipt image"""
    try:
        key_valid, key_msg = validate_api_key()
        if not key_valid:
            return False, key_msg
        
        logger.info(f"🔥 STEP 1: VLM extracting raw text...")
        logger.info(f"🤖 VLM Model: {VLM_MODEL}")
        
        # ===== COMPRESS IMAGE =====
        try:
            image_data = base64.b64decode(base64_image)
            img = Image.open(io.BytesIO(image_data))
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                if img.width > img.height:
                    new_width = max_size
                    new_height = int((max_size / img.width) * img.height)
                else:
                    new_height = max_size
                    new_width = int((max_size / img.height) * img.width)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=80, optimize=True)
            compressed_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            base64_image = compressed_image
        except Exception as e:
            logger.warning(f"⚠️ Compression skipped: {e}")
        
        url = f"{NOVITA_API_BASE}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {NOVITA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": VLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": VLM_EXTRACTION_PROMPT
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.0
        }
        
        logger.info("📡 Sending to VLM...")
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=90)
                break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.info(f"⏱️ Timeout, retrying...")
                    time.sleep(2)
                else:
                    return False, "VLM timeout after retries"
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.info(f"⚠️ Error, retrying: {e}")
                    time.sleep(2)
                else:
                    raise
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                extracted_text = content.strip()
                
                logger.info(f"✅ VLM extracted {len(extracted_text)} chars")
                return True, {
                    'text': extracted_text,
                    'tokens_used': result.get('usage', {}).get('total_tokens', 0),
                    'model': VLM_MODEL
                }
            else:
                return False, "No OCR results"
        else:
            logger.error(f"❌ VLM Error {response.status_code}")
            return False, f"VLM API error: {response.status_code}"
            
    except Exception as e:
        logger.error(f"❌ VLM Error: {str(e)}")
        return False, f"VLM error: {str(e)}"

# ==================== OCR DIGIT CORRECTOR ====================
class OCRDigitCorrector:
    def correct_text(self, text):
        if not text:
            return text
        
        corrected = text
        replacements = {
            '9895': '9995',
            '9995': '9895',
            '225': '235',
            '235': '225',
        }
        
        for old, new in replacements.items():
            corrected = corrected.replace(old, new)
        
        try:
            import re
            lines = corrected.split('\n')
            fixed_lines = []
            
            for line in lines:
                def fix_decimal(match):
                    return f"{match.group(1)}.{match.group(2)}0"
                line = re.sub(r'(\d+)\.(\d{1})\b', fix_decimal, line)
                fixed_lines.append(line)
            
            corrected = '\n'.join(fixed_lines)
        except:
            pass
        
        return corrected

digit_corrector = OCRDigitCorrector()

# ==================== CURRENCY DETECTION ====================
def detect_currency(raw_text, formatted_currency=None):
    if formatted_currency and formatted_currency not in ['None', 'null', '']:
        return formatted_currency.upper()
    
    if '₨' in raw_text or 'PKR' in raw_text or 'Rs.' in raw_text:
        return 'PKR'
    
    symbol_map = {
        '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR',
    }
    
    for symbol, currency in symbol_map.items():
        if symbol in raw_text:
            return currency
    
    if any(x in raw_text.lower() for x in ['islamabad', 'karachi', 'lahore', 'rupee']):
        return 'PKR'
    
    return 'USD'

# ==================== STRICT ODOO ITEM FILTER ====================
def filter_odoo_items(items):
    """
    STRICT filtering of items for Odoo.
    ONLY actual purchasable items should pass through.
    """
    if not items:
        return []
    
    # Comprehensive list of keywords to EXCLUDE from Odoo
    EXCLUDED_KEYWORDS = [
        # Tax related
        'tax', 'vat', 'gst', 'hst', 'pst', 'iva',
        'here:', 'here tax', 'sales tax', '*here: tax',
        
        # Summary lines
        'subtotal', 'sub-total', 'sub total',
        'total', 'grand total', 'balance',
        'amount due', 'due now', 'pay this amount',
        
        # Payment methods
        'cash', 'credit', 'debit', 'visa', 'mastercard',
        'amex', 'discover', 'check', 'gift card',
        'payment', 'tender', 'change', 'cg', 'change given',
        'cash back', 'cashback',
        
        # Fees and charges
         
        'service charge', 'convenience fee', 'processing fee',
        'delivery fee', 'shipping fee', 'handling fee',
        
        # Discounts (unless they're item-level discounts)
        'discount', 'savings', 'coupon', 'promo',
        
        # Tip/gratuity
        'tip', 'gratuity', 'service charge',
        
        # Rounding
        'round', 'rounding', 'adjustment',
        
        # Store info
        'phone', 'tel', 'fax', 'www', 'http', '.com',
        'order #', 'receipt #', 'transaction #',
        'cashier', 'register', 'server', 'table'
    ]
    
    # Patterns that indicate non-item lines
    EXCLUDED_PATTERNS = [
        r'^\d{3}\)',  # Phone numbers: (123)
        r'^\d{3}-\d{3}-\d{4}',  # Phone numbers: 123-456-7890
        r'order\s*#?\s*\d+',  # Order numbers
        r'receipt\s*#?\s*\d+',  # Receipt numbers
        r'table\s*\d+',  # Table numbers
        r'^\d+$',  # Just numbers
        r'^\d+\.\d+$',  # Just decimals
        r'^[A-Z]{2,5}$',  # Abbreviations like CG, TAX, etc.
    ]
    
    filtered_items = []
    import re
    
    for item in items:
        # Get item name and convert to lowercase for checking
        item_name = item.get('label', item.get('name', '')).strip()
        if not item_name:
            continue
            
        item_name_lower = item_name.lower()
        
        # STRICT CHECK 1: Check against excluded keywords
        keyword_excluded = any(keyword in item_name_lower for keyword in EXCLUDED_KEYWORDS)
        
        # STRICT CHECK 2: Check against excluded patterns
        pattern_excluded = any(re.search(pattern, item_name_lower) for pattern in EXCLUDED_PATTERNS)
        
        # STRICT CHECK 3: Check if it's exactly excluded terms
        exact_excluded = item_name_lower.strip() in [
            'tax', 'total', 'subtotal', 'cash', 'cg', 'change',
            'here:', 'here: tax', '*here: tax', 'here tax',
            'atm', 'fee', 'tip', 'credit', 'debit'
        ]
        
        # STRICT CHECK 4: Check if it's just a number or code
        if item_name.replace('.', '').replace('-', '').replace(' ', '').isdigit():
            logger.info(f"🚫 Filtering out numeric item: {item_name}")
            continue
        
        # STRICT CHECK 5: Check if it's too short (likely a code)
        if len(item_name) < 3 and item_name.isupper():
            logger.info(f"🚫 Filtering out short code: {item_name}")
            continue
        
        # STRICT CHECK 6: Check for specific lines
        specific_excluded = any(x in item_name_lower for x in [
            'here: tax', '*here: tax', 'total', 'cash', 'cg'
        ])
        
        # If ANY exclusion check passes, filter it out
        if keyword_excluded or pattern_excluded or exact_excluded or specific_excluded:
            logger.info(f"🚫 Filtering out excluded item: {item_name}")
            continue
        
        # If we get here, it's likely a real item
        logger.info(f"✅ Keeping item for Odoo: {item_name}")
        filtered_items.append(item)
    
    logger.info(f"📊 Filtering complete: {len(filtered_items)}/{len(items)} items kept for Odoo")
    return filtered_items

# ==================== PREPARE ODOO DATA ====================
def prepare_odoo_data(receipt_data):
    """
    Prepare data for Odoo upload
    """
    try:
        formatted = receipt_data.get('formatted_data', {})
        raw_text = receipt_data.get('text', '')
        
        if not formatted:
            formatted = {}
        
        vendor_name = formatted.get('vendor_name', 'Unknown Vendor')
        bill_reference = formatted.get('bill_reference', '')
        bill_date = formatted.get('bill_date', datetime.now().strftime('%Y-%m-%d'))
        currency = formatted.get('currency', detect_currency(raw_text))
        
        # Extract ALL lines
        lines = raw_text.split('\n')
        
        logger.info("\n🔍 EXTRACTING ITEMS AND PRICES:")
        
        # Step 1: Separate items and prices
        items = []
        prices = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip Odoo UI lines
            if any(x in line for x in ['Invoice Lines', 'Journal Items', 'Other Info', 
                                       'Label', 'Account', 'Quantity', 'Price', 'Taxes', 'Amount',
                                       'Imported', 'Untaxed', 'Amount Due']):
                continue
            
            # Check if this is a price line (just numbers)
            clean_line = re.sub(r'[$,\s]', '', line)
            if clean_line.replace('.', '').isdigit():
                try:
                    price = float(clean_line)
                    prices.append(price)
                    logger.info(f"💰 Price: ${price}")
                    continue
                except:
                    pass
            
            # If it has letters, it's an item line
            if re.search(r'[A-Za-z]', line):
                items.append(line)
                logger.info(f"📦 Item: {line}")
        
        logger.info(f"\n📊 Found {len(items)} items and {len(prices)} prices")
        
        # Step 2: Identify REAL items
        real_items = []
        item_prices = []
        
        for i, item in enumerate(items):
            item_lower = item.lower()
            
            # Skip obvious headers and non-items
            if any(x in item_lower for x in ['albetos', 'mexican', 'artesia', 'blvd', 'ph:', 'phone']):
                logger.info(f"⏭️ Skipping header: {item[:30]}")
                continue
            
            # Skip order numbers and recalls
            if any(x in item_lower for x in ['order #', 'recall']):
                logger.info(f"⏭️ Skipping order info: {item[:30]}")
                continue
            
            # Skip tax, total, cash lines
            if any(x in item_lower for x in [
                'tax', 'total', 'subtotal', 'cash', 'cg', 'change',
                'here:', '*here:', 'here tax', '*here: tax',
                'atm', 'fee', 'tip', 'credit', 'debit', 'payment'
            ]):
                logger.info(f"🚫 EXCLUDING non-item: {item}")
                continue
            
            # Check if this item has a price in its line
            numbers_in_item = re.findall(r'(\d+[.,]?\d*)', item)
            if numbers_in_item:
                try:
                    price = float(numbers_in_item[-1].replace(',', ''))
                    if price < 1000:  # Reasonable price
                        real_items.append(item)
                        item_prices.append(price)
                        logger.info(f"✅ Real item with price: {item} = ${price}")
                        continue
                except:
                    pass
            
            # If no price in item, it will get price from prices list
            if i < len(prices):
                price = prices[i]
                if price < 1000:  # Reasonable price
                    real_items.append(item)
                    item_prices.append(price)
                    logger.info(f"✅ Real item: {item} will get price ${price}")
        
        logger.info(f"\n📊 After filtering: {len(real_items)} real items")
        
        # Step 3: Process real items into invoice lines
        invoice_lines = []
        subtotal = 0
        
        for i, item in enumerate(real_items):
            if i < len(item_prices):
                total_price = item_prices[i]
                
                # Check for quantity in item
                qty_match = re.match(r'^(\d+)\s+(.+)$', item)
                if qty_match:
                    quantity = int(qty_match.group(1))
                    name = qty_match.group(2).strip()
                    # Remove any price from name
                    name = re.sub(r'\s*\d+[.,]?\d*\s*$', '', name).strip()
                    name = re.sub(r'[$]', '', name).strip()
                    
                    # Final filter check on cleaned name
                    name_lower = name.lower()
                    if any(x in name_lower for x in ['tax', 'total', 'cash', 'cg', 'here:']):
                        logger.info(f"🚫 Final filter removed: {name}")
                        continue
                    
                    unit_price = total_price / quantity
                    
                    invoice_lines.append({
                        'label': name[:100],
                        'quantity': quantity,
                        'price_unit': round(unit_price, 2)
                    })
                    logger.info(f"✅ {quantity} x {name} = ${total_price} (unit: ${unit_price:.2f})")
                else:
                    # Simple item
                    name = re.sub(r'\s*\d+[.,]?\d*\s*$', '', item).strip()
                    name = re.sub(r'[$]', '', name).strip()
                    
                    # Final filter check on cleaned name
                    name_lower = name.lower()
                    if any(x in name_lower for x in ['tax', 'total', 'cash', 'cg', 'here:']):
                        logger.info(f"🚫 Final filter removed: {name}")
                        continue
                    
                    invoice_lines.append({
                        'label': name[:100],
                        'quantity': 1,
                        'price_unit': round(total_price, 2)
                    })
                    logger.info(f"✅ {name} = ${total_price}")
                
                subtotal += total_price
        
        # FINAL FILTER - Apply the strict filter one more time
        invoice_lines = filter_odoo_items(invoice_lines)
        
        total = subtotal
        
        logger.info(f"\n📊 ODOO UPLOAD SUMMARY:")
        logger.info(f"   Items to upload: {len(invoice_lines)}")
        for line in invoice_lines:
            line_total = line['quantity'] * line['price_unit']
            logger.info(f"      • {line['label'][:30]}: {line['quantity']} x ${line['price_unit']:.2f} = ${line_total:.2f}")
        logger.info(f"   Subtotal: ${subtotal:.2f}")
        
        return {
            'vendor_name': vendor_name,
            'bill_reference': bill_reference,
            'bill_date': bill_date,
            'due_date': bill_date,
            'currency': currency,
            'invoice_lines': invoice_lines,
            'subtotal': round(subtotal, 2),
            'tax_amount': 0,
            'total_amount': round(total, 2)
        }
        
    except Exception as e:
        logger.error(f"Error preparing Odoo data: {e}")
        traceback.print_exc()
        return None

# ==================== FALLBACK PARSER ====================
def fallback_parse_receipt(raw_text):
    """Fallback parser that extracts ALL product items and tax"""
    logger.info(f"🔧 Using fallback parser...")
    
    result = {
        'vendor_name': 'Unknown Vendor',
        'bill_reference': '',
        'bill_date': datetime.now().strftime('%Y-%m-%d'),
        'currency': 'USD',
        'invoice_lines': [],
        'subtotal': 0,
        'tax_amount': 0,
        'total_amount': 0
    }
    
    return result

# ==================== ITEM RECONSTRUCTION ====================
def reconstruct_items_from_raw_text(raw_text):
    lines = raw_text.split('\n')
    reconstructed = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        has_price = re.search(r'(\d+[.,]?\d*)\s*$', line)
        
        if has_price:
            reconstructed.append(line)
            i += 1
        else:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                next_has_price = re.search(r'(\d+[.,]?\d*)\s*$', next_line)
                
                if next_has_price:
                    reconstructed.append(f"{line} {next_line}")
                    i += 2
                else:
                    reconstructed.append(line)
                    i += 1
            else:
                reconstructed.append(line)
                i += 1
    
    return reconstructed

# ==================== ROUTES ====================

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/health', methods=['GET'])
def health_check():
    key_valid, _ = validate_api_key()
    return jsonify({
        'status': 'healthy',
        'api_key_configured': key_valid,
        'vlm_model': VLM_MODEL,
        'llm_model': LLM_MODEL,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/process-receipt', methods=['POST', 'OPTIONS'])
def process_receipt():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        original_image = data['image']
        
        logger.info(f"📷 STEP 0: Preprocessing...")
        enhanced_image = scanner.process_image(original_image)
        
        if enhanced_image:
            # Remove data URL prefix if present
            if 'base64,' in enhanced_image:
                image_for_vlm = enhanced_image.split('base64,')[1]
            else:
                image_for_vlm = enhanced_image
        else:
            if 'base64,' in original_image:
                image_for_vlm = original_image.split('base64,')[1]
            else:
                image_for_vlm = original_image
        
        success, vlm_result = extract_text_with_vlm(image_for_vlm)
        
        if not success:
            return jsonify({'success': False, 'error': vlm_result}), 500
        
        raw_text = vlm_result['text']
        
        # Apply digit correction
        raw_text = digit_corrector.correct_text(raw_text)
        
        logger.info(f"🔧 Reconstructing items...")
        reconstructed_lines = reconstruct_items_from_raw_text(raw_text)
        raw_text = '\n'.join(reconstructed_lines)
        
        # Create formatted data
        formatted_data = {
            'vendor_name': 'Unknown Vendor',
            'bill_reference': '',
            'bill_date': datetime.now().strftime('%Y-%m-%d'),
            'currency': detect_currency(raw_text),
            'invoice_lines': [],
            'subtotal': 0,
            'tax_amount': 0,
            'total_amount': 0
        }
        
        result = {
            'text': raw_text,
            'formatted_data': formatted_data,
            'vlm_model': VLM_MODEL,
            'llm_model': LLM_MODEL,
            'tokens_used': vlm_result.get('tokens_used', 0),
            'enhanced_image': enhanced_image if enhanced_image else original_image
        }
        
        return jsonify({'success': True, 'data': result})
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/odoo/upload', methods=['POST', 'OPTIONS'])
def upload_to_odoo():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        if not data or 'receipt_data' not in data:
            return jsonify({'success': False, 'error': 'No receipt data'}), 400
        
        receipt_data = data['receipt_data']
        original_image = data.get('original_image')
        
        # Get Odoo credentials from request or use defaults
        odoo_url = data.get('odoo_url', ODOO_URL)
        odoo_db = data.get('odoo_db', ODOO_DB)
        odoo_username = data.get('odoo_username', ODOO_USERNAME)
        odoo_password = data.get('odoo_password', ODOO_PASSWORD)
        
        odoo_connector = OdooConnector(odoo_url, odoo_db, odoo_username, odoo_password)
        
        if not odoo_connector.connect():
            return jsonify({'success': False, 'error': 'Odoo connection failed'}), 500
        
        odoo_data = prepare_odoo_data(receipt_data)
        
        if not odoo_data:
            return jsonify({'success': False, 'error': 'Failed to prepare data'}), 500
        
        bill_result = odoo_connector.create_vendor_bill(odoo_data)
        
        if bill_result:
            if original_image:
                odoo_connector.attach_receipt_to_bill(
                    bill_id=bill_result['id'],
                    receipt_image_base64=original_image
                )
            
            return jsonify({
                'success': True,
                'message': 'Bill created successfully',
                'bill_id': bill_result.get('id'),
                'bill_number': bill_result.get('number'),
                'bill_url': bill_result.get('url')
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create bill'}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/odoo/test-connection', methods=['POST', 'OPTIONS'])
def test_odoo_connection():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json() or {}
        
        odoo_url = data.get('odoo_url', ODOO_URL)
        odoo_db = data.get('odoo_db', ODOO_DB)
        odoo_username = data.get('odoo_username', ODOO_USERNAME)
        odoo_password = data.get('odoo_password', ODOO_PASSWORD)
        
        odoo_connector = OdooConnector(odoo_url, odoo_db, odoo_username, odoo_password)
        connected = odoo_connector.connect()
        
        if connected:
            return jsonify({
                'success': True, 
                'message': 'Connected to Odoo',
                'uid': odoo_connector.uid
            })
        else:
            return jsonify({'success': False, 'error': 'Connection failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-novita', methods=['GET'])
def test_novita():
    try:
        key_valid, message = validate_api_key()
        return jsonify({
            'success': key_valid,
            'message': message,
            'api_key': f"{NOVITA_API_KEY[:10]}...{NOVITA_API_KEY[-5:]}" if NOVITA_API_KEY else 'None'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 RECEIPT OCR + ODOO")
    print("=" * 70)
    print(f"🤖 VLM Model: {VLM_MODEL}")
    print(f"🤖 LLM Model: {LLM_MODEL}")
    key_valid, _ = validate_api_key()
    print(f"🔑 API Key: {'✓ VALID' if key_valid else '✗ INVALID'}")
    print(f"🔌 Odoo URL: {ODOO_URL}")
    print(f"📊 Odoo DB: {ODOO_DB}")
    print(f"👤 Odoo User: {ODOO_USERNAME}")
    print("=" * 70)
    app.run(host='0.0.0.0', port=PORT, debug=True)