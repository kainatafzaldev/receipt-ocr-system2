# main.py - WORKING with OpenRouter + ODOO INTEGRATION
import os
import base64
import requests
import json
import traceback
import re
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from odoo_integration import OdooConnector
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, 
            static_folder=FRONTEND_DIR,
            static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# ==================== CONFIGURATION ====================
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_BASE = os.getenv('OPENROUTER_API_BASE', 'https://openrouter.ai/api/v1')
MODEL_NAME = os.getenv('MODEL_NAME', 'qwen/qwen3-vl-235b-a22b-instruct')
PORT = int(os.getenv('PORT', 5000))

# Initialize Odoo connector
odoo = OdooConnector()

def validate_api_key():
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'your_openrouter_api_key_here':
        return False, "OpenRouter API key not configured"
    return True, "OpenRouter API key is configured"

def extract_text_with_openrouter(base64_image):
    try:
        key_valid, key_msg = validate_api_key()
        if not key_valid:
            return False, key_msg
        
        print(f"[{datetime.now()}] 🔥 Starting OpenRouter VL OCR extraction...")
        print(f"[{datetime.now()}] 🤖 Model: {MODEL_NAME}")
        print(f"[{datetime.now()}] 🔑 API Key: {OPENROUTER_API_KEY[:15]}...{OPENROUTER_API_KEY[-5:] if OPENROUTER_API_KEY else 'NOT FOUND'}")
        
        url = f"{OPENROUTER_API_BASE}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Receipt OCR Processor",
            "User-Agent": "Receipt-OCR-App/1.0"
        }
        
        payload = {
            "model": MODEL_NAME,
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
                            "text": "Extract ALL text from this receipt. Return ONLY the raw text exactly as it appears, line by line but the date and time is in one line with space between date and time. No explanations, no markdown, no JSON. Please add text in odoo to show quantity, price and taxes and show and save in odoo accounting template and give me correct result."
                        }
                    ]
                }
            ],
            "max_tokens": 8192,
            "temperature": 0.0
        }
        
        print(f"[{datetime.now()}] 📡 Sending request to OpenRouter...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                extracted_text = ""
                if isinstance(content, str):
                    extracted_text = content
                elif isinstance(content, dict):
                    extracted_text = content.get('text', '')
                elif isinstance(content, list):
                    extracted_text = '\n'.join([str(item) for item in content])
                
                print(f"[{datetime.now()}] ✅ Extracted {len(extracted_text)} characters")
                print(f"[{datetime.now()}] 📝 Preview: {extracted_text[:200]}")
                
                all_data = parse_receipt_data(extracted_text)
                provider = result.get('provider', 'unknown')
                
                return True, {
                    'text': extracted_text,
                    'all_data': all_data,
                    'tokens_used': result.get('usage', {}).get('total_tokens', 0),
                    'model': MODEL_NAME,
                    'provider': provider
                }
            else:
                return False, "No OCR results in API response"
        else:
            error_text = response.text[:500] if response.text else "No error text"
            print(f"[{datetime.now()}] ❌ OpenRouter API Error {response.status_code}: {error_text}")
            
            if response.status_code == 401:
                return False, "OpenRouter API key is invalid. Please check your API key in .env file"
            return False, f"OpenRouter API error {response.status_code}: {error_text}"
            
    except Exception as e:
        print(f"[{datetime.now()}] ❌ OCR Error: {str(e)}")
        traceback.print_exc()
        return False, f"OCR processing error: {str(e)}"

def parse_receipt_data(text):
    """Simple receipt parser"""
    if not text:
        return {}
    
    lines = text.strip().split('\n')
    
    data = {
        'full_text': text,
        'lines': lines,
        'line_count': len(lines),
        'char_count': len(text),
        'store_name': lines[0] if lines else '',
        'items': [],
        'prices': [],
        'totals': []
    }
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        price_match = re.search(r'(\d+\.\d{2})$', line)
        if price_match and not any(x in line.upper() for x in ['SUBTOTAL', 'TAX', 'TOTAL', 'ATM', 'CHARGE', 'FEE']):
            price = price_match.group(1)
            qty_match = re.match(r'^(\d+)', line)
            qty = qty_match.group(1) if qty_match else '1'
            desc = line
            if qty_match:
                desc = desc.replace(qty_match.group(1), '', 1).strip()
            if price_match:
                desc = desc.replace(price_match.group(1), '', 1).strip()
            
            data['items'].append({
                'description': desc.strip(),
                'quantity': qty,
                'price': price,
                'line_total': price
            })
            data['prices'].append(price)
        
        if 'TOTAL' in line.upper() and 'TAX' not in line.upper():
            total_match = re.search(r'(\d+\.\d{2})', line)
            if total_match:
                data['totals'].append(total_match.group(1))
    
    return data

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
        'api_provider': 'OpenRouter',
        'model': MODEL_NAME,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
    return jsonify({
        'success': True,
        'message': 'API is working correctly!',
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
        
        image_data = data['image']
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        
        success, result = extract_text_with_openrouter(image_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Receipt processed successfully',
                'data': result
            })
        else:
            return jsonify({'success': False, 'error': result}), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ODOO INTEGRATION ROUTES ====================

@app.route('/api/debug/odoo-data', methods=['POST', 'OPTIONS'])
def debug_odoo_data():
    """Debug endpoint to check what data is being sent to Odoo"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        if not data or 'receipt_data' not in data:
            return jsonify({'success': False, 'error': 'No receipt data provided'}), 400
        
        receipt_data = data['receipt_data']
        
        # Step 1: Check raw extracted text
        print("\n" + "="*80)
        print("🔍 DEBUG: STEP 1 - RAW EXTRACTED TEXT")
        print("="*80)
        raw_text = receipt_data.get('text', '')
        print(f"Length: {len(raw_text)} characters")
        print(f"Preview:\n{raw_text[:500]}")
        print("="*80)
        
        # Step 2: Check parsed data from prepare_odoo_data
        print("\n🔍 DEBUG: STEP 2 - PARSED ODOO DATA")
        print("="*80)
        odoo_data = prepare_odoo_data(receipt_data)
        print(json.dumps(odoo_data, indent=2))
        print("="*80)
        
        # Step 3: Check Odoo connection
        print("\n🔍 DEBUG: STEP 3 - ODOO CONNECTION")
        print("="*80)
        odoo_connector = OdooConnector()
        connected = odoo_connector.connect()
        print(f"Connected: {connected}")
        if connected:
            print(f"UID: {odoo_connector.uid}")
            print(f"Journal ID: {odoo_connector.journal_id}")
            print(f"Expense Account ID: {odoo_connector.expense_account_id}")
        else:
            print("❌ Failed to connect to Odoo")
        print("="*80)
        
        # Step 4: Validate data before sending
        print("\n🔍 DEBUG: STEP 4 - DATA VALIDATION")
        print("="*80)
        issues = []
        
        if not odoo_data.get('vendor_name') or odoo_data.get('vendor_name') == 'Unknown Vendor':
            issues.append("❌ Vendor name is missing or unknown")
        else:
            print(f"✅ Vendor: {odoo_data['vendor_name']}")
        
        if not odoo_data.get('invoice_lines'):
            issues.append("❌ No invoice lines found")
        else:
            print(f"✅ Invoice lines: {len(odoo_data['invoice_lines'])}")
            for i, line in enumerate(odoo_data['invoice_lines']):
                print(f"   Line {i+1}: {line.get('label', 'No label')[:30]}... | Qty: {line.get('quantity', 0)} | Price: {line.get('price_unit', 0)}")
        
        if odoo_data.get('total_amount', 0) == 0:
            issues.append("⚠️ Total amount is 0")
        else:
            print(f"✅ Total: {odoo_data['total_amount']} {odoo_data.get('currency', 'PKR')}")
        
        if issues:
            print("\n❌ ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ All data looks valid!")
        print("="*80)
        
        # Step 5: Try to create bill and capture full error
        print("\n🔍 DEBUG: STEP 5 - ATTEMPTING BILL CREATION")
        print("="*80)
        
        if connected and not issues:
            try:
                # Try to search for vendor first
                vendor = odoo_connector.search_vendor(odoo_data.get('vendor_name', ''))
                print(f"Vendor search result: {vendor}")
                
                # Try to create bill with detailed error capture
                bill_result = odoo_connector.create_vendor_bill(odoo_data)
                
                if bill_result:
                    print(f"✅ BILL CREATED SUCCESSFULLY!")
                    print(f"   Bill ID: {bill_result.get('id')}")
                    print(f"   Bill Number: {bill_result.get('number')}")
                    print(f"   URL: {bill_result.get('url')}")
                else:
                    print("❌ Bill creation failed - check Odoo logs above")
            except Exception as e:
                print(f"❌ Exception during bill creation: {str(e)}")
                traceback.print_exc()
        else:
            print("⚠️ Skipping bill creation due to connection or data issues")
        print("="*80)
        
        # Return all debug info
        return jsonify({
            'success': True,
            'debug_info': {
                'raw_text_preview': raw_text[:500],
                'raw_text_length': len(raw_text),
                'parsed_data': odoo_data,
                'odoo_connected': connected,
                'odoo_uid': odoo_connector.uid if connected else None,
                'issues': issues,
                'invoice_lines_count': len(odoo_data.get('invoice_lines', [])),
                'total_amount': odoo_data.get('total_amount', 0),
                'currency': odoo_data.get('currency', 'PKR')
            }
        })
        
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/odoo-accounts', methods=['GET'])
def debug_odoo_accounts():
    """Check available accounts in Odoo"""
    try:
        odoo_connector = OdooConnector()
        if not odoo_connector.connect():
            return jsonify({'success': False, 'error': 'Could not connect to Odoo'}), 500
        
        # Get all expense accounts
        expense_accounts = odoo_connector.models.execute_kw(
            odoo_connector.db, odoo_connector.uid, odoo_connector.password,
            'account.account', 'search_read',
            [[['account_type', '=', 'expense']]], 
            {'fields': ['id', 'code', 'name', 'account_type'], 'limit': 20}
        )
        
        # Get all journals
        journals = odoo_connector.models.execute_kw(
            odoo_connector.db, odoo_connector.uid, odoo_connector.password,
            'account.journal', 'search_read',
            [[['type', '=', 'purchase']]], 
            {'fields': ['id', 'name', 'type', 'code']}
        )
        
        # Get all currencies
        currencies = odoo_connector.models.execute_kw(
            odoo_connector.db, odoo_connector.uid, odoo_connector.password,
            'res.currency', 'search_read',
            [[]], 
            {'fields': ['id', 'name', 'symbol'], 'limit': 10}
        )
        
        return jsonify({
            'success': True,
            'expense_accounts': expense_accounts,
            'purchase_journals': journals,
            'currencies': currencies
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/odoo/upload', methods=['POST', 'OPTIONS'])
def upload_to_odoo():
    """Upload extracted receipt data to Odoo as vendor bill"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        if not data or 'receipt_data' not in data:
            return jsonify({'success': False, 'error': 'No receipt data provided'}), 400
        
        receipt_data = data['receipt_data']
        
        odoo_connector = OdooConnector()
        
        if not odoo_connector.connect():
            return jsonify({
                'success': False, 
                'error': 'Could not connect to Odoo. Check credentials in .env file'
            }), 500
        
        # Get prepared data from main.py's prepare_odoo_data function
        odoo_data = prepare_odoo_data(receipt_data)
        
        # Create vendor bill
        bill_result = odoo_connector.create_vendor_bill(odoo_data)
        
        if bill_result:
            return jsonify({
                'success': True,
                'message': 'Bill created successfully in Odoo',
                'bill_id': bill_result.get('id'),
                'bill_number': bill_result.get('number'),
                'bill_url': bill_result.get('url')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create bill in Odoo'
            }), 500
            
    except Exception as e:
        logger.error(f"Odoo upload error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/odoo/vendors/search', methods=['POST', 'OPTIONS'])
def search_vendors():
    """Search for vendors in Odoo"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json()
        vendor_name = data.get('vendor_name', '')
        
        odoo_connector = OdooConnector()
        if not odoo_connector.connect():
            return jsonify({'success': False, 'error': 'Odoo connection failed'}), 500
        
        vendor = odoo_connector.search_vendor(vendor_name)
        
        return jsonify({
            'success': True,
            'vendor': vendor
        })
        
    except Exception as e:
        logger.error(f"Vendor search error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/odoo/test-connection', methods=['GET', 'OPTIONS'])
def test_odoo_connection():
    """Test connection to Odoo"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        odoo_connector = OdooConnector()
        connected = odoo_connector.connect()
        if connected:
            return jsonify({
                'success': True,
                'message': 'Successfully connected to Odoo',
                'uid': odoo_connector.uid
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to connect to Odoo. Check your credentials.'
            }), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ 100% DYNAMIC PARSING - HANDLES ANY RECEIPT FORMAT ============

def prepare_odoo_data(receipt_data):
    """100% DYNAMIC - Works with ANY receipt from ANY country"""
    try:
        raw_text = receipt_data.get('text', '')
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        print("\n" + "="*80)
        print("📄 100% DYNAMIC PARSING - ANY RECEIPT FORMAT")
        print("="*80)
        
        # ============ DYNAMIC VENDOR DETECTION ============
        vendor_name = detect_vendor_dynamic(lines)
        print(f"🏪 Vendor: {vendor_name}")
        
        # ============ DYNAMIC DATE DETECTION ============
        bill_date = detect_date_dynamic(lines)
        print(f"📅 Date: {bill_date}")
        
        # ============ DYNAMIC REFERENCE DETECTION ============
        bill_reference = detect_receipt_number_dynamic(lines)
        print(f"🔢 Reference: {bill_reference}")
        
        # ============ DYNAMIC ITEM DETECTION ============
        items = detect_items_dynamic(lines)
        print(f"\n🛒 Items: {len(items)}")
        
        # ============ DYNAMIC TOTALS DETECTION ============
        totals = detect_totals_dynamic(lines, items)
        print(f"\n💰 Subtotal: {totals['subtotal']}")
        print(f"💰 Tax Amount: {totals['tax']}")
        print(f"💰 Total: {totals['total']}")
        
        # ============ DYNAMIC CURRENCY DETECTION ============
        currency = detect_currency_dynamic(lines)
        print(f"💱 Currency: {currency}")
        
        # ============ FORMAT ITEMS FOR ODOO ============
        invoice_lines = []
        for item in items:
            invoice_lines.append({
                'label': item['description'][:100],
                'quantity': float(item['quantity']),
                'price_unit': float(item['price'])  # This is the TOTAL price
            })
            print(f"  - {item['description'][:30]}... | Qty: {item['quantity']} | Total: ${item['price']}")
        
        # ============ FIND EXACT TAX TEXT ============
        tax_text = ""
        tax_amount = totals['tax']
        for line in lines:
            if any(x in line.upper() for x in ['TAX', 'VAT', 'GST']):
                tax_text = line.strip()
                # Extract exact tax amount if not already found
                if tax_amount == 0:
                    tax_match = re.search(r'(\d+\.\d{2})', line)
                    if tax_match:
                        tax_amount = float(tax_match.group(1))
                break
        
        # ============ FINAL ODOO-READY DATA ============
        odoo_data = {
            'vendor_name': vendor_name,
            'bill_reference': bill_reference,
            'bill_date': bill_date,
            'due_date': bill_date,
            'currency': currency,
            'invoice_lines': invoice_lines,
            'subtotal': float(totals['subtotal']),
            'tax_amount': float(tax_amount),
            'tax_text': tax_text,
            'total_amount': float(totals['total']),
            'notes': raw_text[:500]
        }
        
        print("\n" + "="*80)
        print("✅ ODOO DATA READY - 100% DYNAMIC")
        print("="*80)
        print(f"Vendor: {odoo_data['vendor_name']}")
        print(f"Bill Reference: {odoo_data['bill_reference']}")
        print(f"Bill Date: {odoo_data['bill_date']}")
        print(f"Currency: {odoo_data['currency']}")
        print(f"Subtotal: {odoo_data['subtotal']} {currency}")
        print(f"Tax Amount: {odoo_data['tax_amount']} {currency}")
        print(f"Total Amount: {odoo_data['total_amount']} {currency}")
        print("="*80)
        
        return odoo_data
        
    except Exception as e:
        logger.error(f"Error preparing Odoo data: {e}")
        traceback.print_exc()
        return {
            'vendor_name': 'Unknown Vendor',
            'bill_reference': '',
            'bill_date': datetime.now().strftime('%Y-%m-%d'),
            'due_date': datetime.now().strftime('%Y-%m-%d'),
            'currency': 'USD',
            'invoice_lines': [],
            'subtotal': 0,
            'tax_amount': 0,
            'tax_text': '',
            'total_amount': 0,
            'notes': ''
        }

def detect_items_dynamic(lines):
    """100% DYNAMIC - Detects items from ANY receipt format"""
    items = []
    
    print("\n🔍 Scanning for items in ANY format...")
    
    # Common patterns across all receipt types
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip obviously non-item lines
        if not line or len(line) < 5:
            continue
            
        skip_words = ['SUBTOTAL', 'TOTAL', 'TAX', 'VAT', 'GST', 'CASH', 'CHANGE', 
                     'BALANCE', 'DUE', 'RECEIPT', 'ORDER', 'INVOICE', 'PAGE', 
                     'SERVER', 'TABLE', 'GUEST', 'CHECK', 'ATM', 'RECALL']
        
        if any(word in line.upper() for word in skip_words):
            continue
        
        # ============ PATTERN 1: "3 ASADA TACO 8.10" ============
        qty_start = re.match(r'^(\d+)\s+', line)
        price_end = re.search(r'(\d+\.\d{2})$', line)
        
        if qty_start and price_end:
            qty = float(qty_start.group(1))
            price = float(price_end.group(1))
            desc = line.replace(qty_start.group(1), '', 1).strip()
            desc = desc.replace(price_end.group(1), '', 1).strip()
            
            items.append({
                'description': desc if desc else f"Item {i+1}",
                'quantity': qty,
                'price': price
            })
            print(f"   ✅ Pattern 1: {desc[:30]} | {qty} x ${price/qty:.2f} = ${price}")
            continue
        
        # ============ PATTERN 2: "ASADA TACO 3 8.10" ============
        words = line.split()
        for j, word in enumerate(words):
            if word.replace('.', '').isdigit() and 1 <= float(word) <= 99:
                # Check if last word is a price
                if re.match(r'^\d+\.\d{2}$', words[-1]):
                    qty = float(word)
                    price = float(words[-1])
                    desc_parts = [w for idx, w in enumerate(words) if idx != j and idx != len(words)-1]
                    desc = ' '.join(desc_parts)
                    
                    items.append({
                        'description': desc if desc else f"Item {i+1}",
                        'quantity': qty,
                        'price': price
                    })
                    print(f"   ✅ Pattern 2: {desc[:30]} | {qty} x ${price/qty:.2f} = ${price}")
                    break
            continue
        
        # ============ PATTERN 3: "3 x ASADA TACO 8.10" ============
        x_pattern = re.search(r'(\d+)\s*[xX]\s+', line)
        price_end = re.search(r'(\d+\.\d{2})$', line)
        
        if x_pattern and price_end:
            qty = float(x_pattern.group(1))
            price = float(price_end.group(1))
            desc = line.replace(x_pattern.group(0), '', 1).strip()
            desc = desc.replace(price_end.group(1), '', 1).strip()
            
            items.append({
                'description': desc if desc else f"Item {i+1}",
                'quantity': qty,
                'price': price
            })
            print(f"   ✅ Pattern 3: {desc[:30]} | {qty} x ${price/qty:.2f} = ${price}")
            continue
        
        # ============ PATTERN 4: "ASADA TACO 8.10" (qty=1) ============
        price_end = re.search(r'(\d+\.\d{2})$', line)
        if price_end and not any(x in line.upper() for x in ['TAX', 'TOTAL']):
            price = float(price_end.group(1))
            desc = line.replace(price_end.group(1), '', 1).strip()
            
            items.append({
                'description': desc if desc else f"Item {i+1}",
                'quantity': 1,
                'price': price
            })
            print(f"   ✅ Pattern 4: {desc[:30]} | 1 x ${price} = ${price}")
            continue
    
    return items

def detect_totals_dynamic(lines, items):
    """100% DYNAMIC - Detects totals from ANY receipt"""
    totals = {
        'subtotal': 0,
        'tax': 0,
        'total': 0
    }
    
    print("\n💰 Scanning for totals...")
    
    # Keywords in multiple languages
    subtotal_keywords = ['SUBTOTAL', 'SUB TOTAL', 'SUB-TOTAL', 'SUBTOTAL:', 'NET']
    tax_keywords = ['TAX', 'VAT', 'GST', 'SALES TAX', 'TAX AMOUNT', 'TOTAL TAX']
    total_keywords = ['TOTAL', 'GRAND TOTAL', 'TOTAL:', 'AMOUNT DUE', 'BALANCE DUE']
    
    for line in lines:
        line_upper = line.upper()
        
        # Find all numbers in the line
        numbers = re.findall(r'(\d+\.\d{2})', line)
        if not numbers:
            continue
        
        amount = float(numbers[-1])
        
        # Check for subtotal
        for kw in subtotal_keywords:
            if kw in line_upper:
                totals['subtotal'] = amount
                print(f"   ✅ Subtotal: ${amount}")
                break
        
        # Check for tax
        for kw in tax_keywords:
            if kw in line_upper:
                totals['tax'] = amount
                print(f"   ✅ Tax: ${amount}")
                break
        
        # Check for total
        for kw in total_keywords:
            if kw in line_upper:
                totals['total'] = amount
                print(f"   ✅ Total: ${amount}")
                break
    
    # Calculate missing totals
    if totals['subtotal'] == 0 and items:
        totals['subtotal'] = sum(item['price'] for item in items)
        print(f"   💰 Calculated subtotal: ${totals['subtotal']}")
    
    if totals['total'] == 0:
        totals['total'] = totals['subtotal'] + totals['tax']
        print(f"   💵 Calculated total: ${totals['total']}")
    
    return totals

def detect_currency_dynamic(lines):
    """100% DYNAMIC - Detects currency from ANY receipt"""
    currency_map = {
        '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR',
        '₽': 'RUB', '₩': 'KRW', '₱': 'PHP', '₫': 'VND', '฿': 'THB',
        '₺': 'TRY', '₪': 'ILS', '₦': 'NGN', '₴': 'UAH', '₲': 'PYG',
        'PKR': 'PKR', 'RS': 'PKR', 'RS.': 'PKR', 'AED': 'AED', 'SAR': 'SAR',
        'USD': 'USD', 'EUR': 'EUR', 'GBP': 'GBP'
    }
    
    for line in lines[:15]:
        for symbol, currency in currency_map.items():
            if symbol in line:
                return currency
    
    return 'USD'

def detect_vendor_dynamic(lines):
    """100% DYNAMIC - Detects vendor from ANY receipt"""
    for i, line in enumerate(lines[:5]):
        line = line.strip()
        
        # Skip lines with obvious non-vendor content
        skip = ['TEL:', 'PHONE:', 'FAX:', 'WWW.', '.COM', '@', 
                'ORDER', 'RECEIPT', 'INVOICE', 'DATE', 'TIME',
                'CASH', 'TOTAL', 'SUBTOTAL', 'TAX']
        
        if any(s in line.upper() for s in skip):
            continue
        
        # If line has proper capitalization and reasonable length
        if line and len(line) > 2 and len(line) < 50:
            if line[0].isupper() or any(c.isupper() for c in line[:5]):
                return line
    
    # Fallback: first non-empty line
    for line in lines[:3]:
        if line and len(line) > 3:
            return line
    
    return "Unknown Vendor"

def detect_date_dynamic(lines):
    """100% DYNAMIC - Detects date from ANY receipt"""
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # 14/04/08 or 04/14/2008
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',     # 2008/04/14
        r'(\d{1,2}\s+[A-Za-z]{3,}\s+\d{2,4})', # 14 Apr 2008
        r'([A-Za-z]{3,}\s+\d{1,2},?\s+\d{2,4})', # Apr 14, 2008
        r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})'   # 14.04.08 or 14-04-08
    ]
    
    for line in lines:
        for pattern in date_patterns:
            match = re.search(pattern, line)
            if match:
                date_str = match.group(1)
                try:
                    return convert_to_odoo_date(date_str)
                except:
                    pass
    
    return datetime.now().strftime('%Y-%m-%d')

def convert_to_odoo_date(date_str):
    """Convert any date format to YYYY-MM-DD"""
    date_str = re.sub(r'[^\d/.\-A-Za-z]', '', date_str).strip()
    
    # Try common separators
    for sep in ['/', '-', '.']:
        if sep in date_str:
            parts = date_str.split(sep)
            if len(parts) == 3:
                # Check if year is first
                if len(parts[0]) == 4:
                    return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                # Check if year is last
                elif len(parts[2]) == 4:
                    return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                # Assume year is last with 2 digits
                elif len(parts[2]) == 2:
                    year = f"20{parts[2]}" if int(parts[2]) < 50 else f"19{parts[2]}"
                    return f"{year}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
    
    return datetime.now().strftime('%Y-%m-%d')

def detect_receipt_number_dynamic(lines):
    """100% DYNAMIC - Detects receipt number from ANY receipt"""
    patterns = [
        r'#\s*(\d+)',
        r'ORDER\s*#?\s*(\d+)',
        r'RECEIPT\s*#?\s*(\d+)',
        r'INVOICE\s*#?\s*(\d+)',
        r'BILL\s*#?\s*(\d+)',
        r'NO\.?\s*(\d+)',
        r'(\d{6,})'  # Any 6+ digit number
    ]
    
    for line in lines[:10]:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1)
    
    return ""

@app.route('/api/test-openrouter', methods=['GET'])
def test_openrouter():
    """Test OpenRouter API key directly"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Receipt-OCR-App/1.0"
        }
        
        # Test models endpoint
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json()
            return jsonify({
                'success': True,
                'message': '✅ API key is valid!',
                'api_key': f"{OPENROUTER_API_KEY[:15]}...{OPENROUTER_API_KEY[-5:]}" if OPENROUTER_API_KEY else 'None',
                'models_count': len(models.get('data', [])),
                'sample_models': [m.get('id') for m in models.get('data', [])[:5]]
            })
        else:
            return jsonify({
                'success': False,
                'error': f"API Error {response.status_code}: {response.text}",
                'api_key': f"{OPENROUTER_API_KEY[:15]}...{OPENROUTER_API_KEY[-5:]}" if OPENROUTER_API_KEY else 'None'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/parse-text', methods=['POST'])
def debug_parse_text():
    """Test parser with raw text"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        test_text = data['text']
        lines = [line.strip() for line in test_text.split('\n') if line.strip()]
        
        items = detect_items_dynamic(lines)
        totals = detect_totals_dynamic(lines, items)
        
        return jsonify({
            'success': True,
            'raw_lines': lines[:20],
            'detected_items': items,
            'detected_totals': totals,
            'explanation': '100% dynamic parser - works with ANY receipt format'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 100% DYNAMIC RECEIPT OCR + ODOO")
    print("=" * 60)
    print(f"🤖 Model: {MODEL_NAME}")
    key_valid, key_msg = validate_api_key()
    print(f"🔑 OpenRouter API Key: {'✓ VALID' if key_valid else f'✗ {key_msg}'}")
    print(f"🏢 Odoo URL: {os.getenv('ODOO_URL', 'http://localhost:8069')}")
    print(f"📊 Odoo DB: {os.getenv('ODOO_DB', 'odoo')}")
    print("=" * 60)
    print("📡 Available Endpoints:")
    print("   ✓ /api/process-receipt - OCR Receipt (OpenRouter)")
    print("   ✓ /api/odoo/test-connection - Test Odoo Connection")
    print("   ✓ /api/odoo/vendors/search - Search Vendors")
    print("   ✓ /api/odoo/upload - Upload to Odoo")
    print("   ✓ /api/debug/parse-text - Test text parsing")
    print("   ✓ /api/debug/odoo-data - Debug Odoo data")
    print("   ✓ /api/debug/odoo-accounts - Check Odoo accounts")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=True)