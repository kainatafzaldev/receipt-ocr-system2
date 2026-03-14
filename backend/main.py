# main.py - COMPLETE RECEIPT OCR + ODOO INTEGRATION
from dotenv import load_dotenv
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
from image_preprocessor import ImagePreprocessor


# Initialize preprocessor
preprocessor = ImagePreprocessor()
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"🔍 Looking for .env at: {env_path}")
print(f"🔍 File exists: {os.path.exists(env_path)}")

load_dotenv(env_path)
# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"🔍 Looking for .env at: {env_path}")
print(f"🔍 File exists: {os.path.exists(env_path)}")

# Force reload with override
load_dotenv(env_path, override=True)

# Debug: Check all env vars
print("📋 Environment variables after loading:")
print(f"  NOVITA_API_KEY exists: {bool(os.getenv('NOVITA_API_KEY'))}")
print(f"  ODOO_URL exists: {bool(os.getenv('ODOO_URL'))}")
print(f"  PORT: {os.getenv('PORT')}")

# Now assign variables
NOVITA_API_KEY = os.getenv('NOVITA_API_KEY')
NOVITA_API_BASE = os.getenv('NOVITA_API_BASE', 'https://api.novita.ai/v3/openai')
VLM_MODEL = os.getenv('VLM_MODEL', 'qwen/qwen3-vl-235b-a22b-instruct')
LLM_MODEL = os.getenv('LLM_MODEL', 'meta-llama/llama-3.3-70b-instruct')
PORT = int(os.getenv('PORT', 5000))

# ==================== DISCOUNT DETECTION CONSTANTS ====================
DISCOUNT_WORDS = [
    "OFF", "DISCOUNT", "PROMO", "COUPON",
    "MARKDOWN", "SAVING", "REBATE"
]

IGNORE_WORDS = [
    "TIP", "TIP GUIDE", "GRATUITY", "CHANGE",
    "CASH", "CARD", "AUTH", "BARCODE"
]

# ==================== DISCOUNT DETECTION FUNCTIONS ====================
def normalize_lines(text):
    """Convert OCR text into clean lines"""
    lines = text.split("\n")
    return [l.strip() for l in lines if l.strip()]

def contains_ignore_word(line):
    line = line.upper()
    return any(word in line for word in IGNORE_WORDS)

def contains_discount_word(line):
    line = line.upper()
    return any(word in line for word in DISCOUNT_WORDS)

def extract_prices(line):
    """Extract all prices from line"""
    return re.findall(r"-?\d+\.\d{2}", line)

def extract_quantity(line):
    """Detect quantity at beginning of line"""
    match = re.match(r"^\d+", line)
    if match:
        return int(match.group())
    return 1
def detect_discount(line):
    line_upper = line.upper()

    if "OFF" in line_upper or "DISCOUNT" in line_upper or "PROMO" in line_upper:
        return True

    if re.search(r"\d+%\s*OFF", line_upper):
        return True

    return False


def parse_receipt_dynamic(ocr_text):
    """Parse receipt with discount detection"""
    lines = normalize_lines(ocr_text)

    invoice_lines = []
    subtotal = None
    tax = None
    total = None

    for line in lines:

        if contains_ignore_word(line):
            continue

        upper = line.upper()

        # SUBTOTAL
        if "SUBTOTAL" in upper:
            price = extract_prices(line)
            if price:
                subtotal = float(price[-1])
            continue

        # TAX
        if "TAX" in upper:
            price = extract_prices(line)
            if price:
                tax = float(price[-1])
            continue

        # TOTAL
        if "TOTAL" in upper:
            price = extract_prices(line)
            if price:
                total = float(price[-1])
            continue

def parse_receipt_dynamic(ocr_text):
    """Parse receipt with discount detection"""
    lines = normalize_lines(ocr_text)

    invoice_lines = []
    subtotal = None
    tax = None
    total = None

    for line in lines:

        if contains_ignore_word(line):
            continue

        upper = line.upper()

        # SUBTOTAL
        if "SUBTOTAL" in upper:
            price = extract_prices(line)
            if price:
                subtotal = float(price[-1])
            continue

        # TAX
        if "TAX" in upper:
            price = extract_prices(line)
            if price:
                tax = float(price[-1])
            continue

        # TOTAL
        if "TOTAL" in upper:
            price = extract_prices(line)
            if price:
                total = float(price[-1])
            continue

        prices = extract_prices(line)

        if not prices:
            continue

        quantity = extract_quantity(line)
        price = float(prices[-1])

        # DISCOUNT LINE
        if detect_discount(line):

            # 🔥 Force negative price for discount
            price = -abs(price)

            invoice_lines.append({
                "label": line,
                "quantity": 1,
                "price_unit": price,
                "is_discount": True
            })

        else:
            unit_price = price / quantity if quantity else price

            invoice_lines.append({
                "label": line,
                "quantity": quantity,
                "price_unit": round(unit_price, 2),
                "is_discount": False
            })

    return {
        "invoice_lines": invoice_lines,
        "subtotal": subtotal,
        "tax_amount": tax,
        "total_amount": total
    }     

def fix_alignment_dynamic(raw_text):
    """
    Dynamically fix alignment issues WITHOUT any hardcoding
    """
    lines = raw_text.split('\n')
    fixed_lines = []
    i = 0
    
    # First, clean up all lines
    cleaned_lines = []
    for line in lines:
        # Remove arrows and special characters but keep everything else
        line = line.replace('→', ' ').replace('->', ' ').replace('-->', ' ')
        # Remove multiple spaces but preserve structure
        line = re.sub(r'\s+', ' ', line).strip()
        if line:
            cleaned_lines.append(line)
    
    # Identify all lines with prices
    price_lines = []
    for idx, line in enumerate(cleaned_lines):
        prices = re.findall(r'\$?(\d+\.?\d*)', line)
        if prices:
            price_lines.append((idx, prices[-1]))  # Last number is usually the price
    
    # Group lines by proximity (same vertical region)
    line_groups = []
    current_group = []
    last_y = None
    
    for idx, line in enumerate(cleaned_lines):
        # In real OCR, you'd have Y-coordinates
        # Here we'll simulate by assuming consecutive lines are close
        if not current_group:
            current_group.append((idx, line))
        else:
            # If this line has no price and next line might have price, group them
            has_price = any(price_idx == idx for price_idx, _ in price_lines)
            next_has_price = any(price_idx == idx+1 for price_idx, _ in price_lines)
            
            if not has_price and next_has_price:
                current_group.append((idx, line))
            else:
                line_groups.append(current_group)
                current_group = [(idx, line)]
    
    if current_group:
        line_groups.append(current_group)
    
    # Reconstruct lines with proper pairing
    for group in line_groups:
        if len(group) == 1:
            # Single line - keep as is
            fixed_lines.append(group[0][1])
        else:
            # Multiple lines that belong together
            combined_text = ' '.join([text for _, text in group])
            
            # Find the price for this group
            for price_idx, price in price_lines:
                if any(idx == price_idx for idx, _ in group):
                    # This price belongs to this group
                    # Remove price from combined text if it's duplicated
                    if price in combined_text:
                        combined_text = combined_text.replace(price, '').strip()
                    fixed_lines.append(f"{combined_text} ${price}")
                    break
            else:
                # No price found for this group
                fixed_lines.append(combined_text)
    
    return '\n'.join(fixed_lines)

# Initialize scanner
scanner = DocumentScanner()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, 
            static_folder=FRONTEND_DIR,
            static_url_path='')

# Add before_request handler to reload environment for each request
@app.before_request
def before_request():
    """Reload environment variables before each request"""
    global NOVITA_API_KEY
    from dotenv import load_dotenv
    load_dotenv(override=True)
    NOVITA_API_KEY = os.getenv('NOVITA_API_KEY')
    print(f"🔄 Before request - API Key loaded: {NOVITA_API_KEY[:10] if NOVITA_API_KEY else 'None'}...")

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

# Get Odoo credentials from environment variables
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USERNAME = os.getenv('ODOO_USERNAME')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

# USE the environment variables, not hardcoded values
print("="*60)
print("🔴 USING ENVIRONMENT VARIABLES FOR ODOO")
print(f"URL: {ODOO_URL}")
print(f"DB: {ODOO_DB}")
print(f"Username: {ODOO_USERNAME}")
print("="*60)

odoo = OdooConnector(
    url=ODOO_URL,
    db=ODOO_DB,
    username=ODOO_USERNAME,
    password=ODOO_PASSWORD
)

def validate_api_key():
    """Validate that Novita.ai API key is configured"""
    global NOVITA_API_KEY
    
    # Force reload on each call
    from dotenv import load_dotenv
    load_dotenv(override=True)
    NOVITA_API_KEY = os.getenv('NOVITA_API_KEY')
    
    print(f"🔑 validate_api_key - checking: '{NOVITA_API_KEY[:10] if NOVITA_API_KEY else 'None'}...'")
    
    if not NOVITA_API_KEY or NOVITA_API_KEY == 'your_novita_api_key_here':
        print("❌ API key missing or placeholder")
        return False, "Novita.ai API key not configured"
    
    print(f"✅ API key valid")
    return True, "Novita.ai API key is configured"

# ==================== VLM EXTRACTION PROMPT (For Receipt OCR) ====================
VLM_EXTRACTION_PROMPT = """You are an expert OCR system for receipts and invoices. Your ONLY task is to extract ALL text EXACTLY as it appears, PRESERVING THE ORIGINAL LINE STRUCTURE AND SPACING.

CRITICAL RULES - READ CAREFULLY:

1. EXTRACT EVERYTHING VERBATIM:
   - Store names, addresses, phone numbers, emails, website URLs
   - Every single item line (including duplicates)
   - All prices, quantities, discounts, markdowns, and savings
   - Subtotal, tax, total, cash, change, payment method
   - Any text in any language (English, Arabic, Urdu, Spanish, etc.)
   - ALL spaces, tabs, and formatting exactly as they appear
   - Column headers like "QTY", "ITEM", "AMOUNT", "PRICE", "DESCRIPTION"
   - Receipt numbers, order numbers, transaction IDs
   - Date and time stamps

2. PRESERVE EXACT LINE STRUCTURE (MOST IMPORTANT):
   - The number of lines in your output MUST match the number of lines on the receipt
   - If text appears on SEPARATE lines in the receipt → output on SEPARATE lines
   - If text appears on the SAME line in the receipt → output on the SAME line
   - DO NOT combine lines that are separate in the original
   - DO NOT split lines that are together in the original
   - DO NOT merge item names with their prices if they appear on different lines
   - DO NOT separate item names from their prices if they appear on the same line

3. PRESERVE EXACT SPACING:
   - If the receipt shows "QTY    ITEM    Amt" with 4 spaces, output EXACTLY "QTY    ITEM    Amt" with 4 spaces
   - If the receipt shows "1 Hi Chk Steak(K)    $22.95" with 4 spaces, output EXACTLY with 4 spaces
   - If the receipt shows "Subtotal:    $87.55" with 4 spaces, output EXACTLY with 4 spaces
   - If the receipt shows "Total: $93.58" with 1 space, output EXACTLY with 1 space
   - DO NOT normalize, trim, or clean up spacing

4. COPY EXACTLY - FOLLOW THESE EXAMPLES OF CORRECT EXTRACTION:

   EXAMPLE A - Store Information (keep as separate lines with exact spacing):
   Receipt: "ALBETOS MEXICAN FOOD"
   Output: "ALBETOS MEXICAN FOOD"
   
   Receipt: "11732 ARTESIA BLVD."
   Output: "11732 ARTESIA BLVD."
   
   Receipt: "ARTESIA, CA. Ph: (562) 860-2530"
   Output: "ARTESIA, CA. Ph: (562) 860-2530"
   
   Receipt: "www.akirasushigroup.com"
   Output: "www.akirasushigroup.com"

   EXAMPLE B - Column Headers with spacing (CRITICAL - preserve spaces):
   Receipt: "QTY    ITEM    Amt"
   Output: "QTY    ITEM    Amt"
   
   Receipt: "QTY  ITEM  PRICE  TOTAL"
   Output: "QTY  ITEM  PRICE  TOTAL"

   EXAMPLE C - Items with quantity at start (keep as one line with exact spacing):
   Receipt: "3 ASADA TACO    $29.97"
   Output: "3 ASADA TACO    $29.97"
   
   Receipt: "2 SODA    $5.98"
   Output: "2 SODA    $5.98"
   
   Receipt: "1    Hi Chk Steak(K)    $22.95"
   Output: "1    Hi Chk Steak(K)    $22.95"

   EXAMPLE D - Items with quantity at end (keep as one line):
   Receipt: "PAPYRUS CARDS 2    $19.94"
   Output: "PAPYRUS CARDS 2    $19.94"

   EXAMPLE E - Items with multiplication (keep as one line):
   Receipt: "Snowglobe 6.99 x 3    $20.97"
   Output: "Snowglobe 6.99 x 3    $20.97"

   EXAMPLE F - Tax and Summary Lines (keep as separate lines with exact spacing):
   Receipt: "SUBTOTAL:    $87.55"
   Output: "SUBTOTAL:    $87.55"
   
   Receipt: "Tax    $6.93"
   Output: "Tax    $6.93"
   
   Receipt: "TOTAL:    $93.58"
   Output: "TOTAL:    $93.58"

   EXAMPLE G - Payment and Other Lines (keep as is):
   Receipt: "ATM    $9.58"
   Output: "ATM    $9.58"
   
   Receipt: "RECALL    :636"
   Output: "RECALL    :636"
   
   Receipt: "CASH    $20.00"
   Output: "CASH    $20.00"
   
   Receipt: "CHANGE    $10.15"
   Output: "CHANGE    $10.15"
   
   Receipt: "ORDER # 01029"
   Output: "ORDER # 01029"
   
   Receipt: "#37 PICKUP"
   Output: "#37 PICKUP"

   EXAMPLE H - Multi-column POS Receipts (Pakistani/Indian format):
   Receipt: "FG-022984 - LU SP Jaferi Nankhatai 358.4g  3  1 Piece  313.00  48.81  319.00"
   Output: "FG-022984 - LU SP Jaferi Nankhatai 358.4g  3  1 Piece  313.00  48.81  319.00"
   
   Receipt: "MD - NAN KHATAI          1    150.00    0.00   150.00"
   Output: "MD - NAN KHATAI          1    150.00    0.00   150.00"

   EXAMPLE I - Discount/Markdown Lines:
   Receipt: "Markdown    -$1.00"
   Output: "Markdown    -$1.00"
   
   Receipt: "DISCOUNT    -$5.00"
   Output: "DISCOUNT    -$5.00"

   EXAMPLE J - Arabic/Urdu Receipts:
   Receipt: "عرض اسعار    ر.س 150.00"
   Output: "عرض اسعار    ر.س 150.00"
   
   Receipt: "بریانی    Rs. 350"
   Output: "بریانی    Rs. 350"

5. HANDLE ALL FORMATS DYNAMICALLY:
   - Supermarket receipts (grocery store, retail)
   - Petrol/Fuel receipts (gas station)
   - Sales/Purchase invoices (business invoices)
   - Restaurant bills
   - Price quotations (عرض اسعار in Arabic)
   - Wholesale price lists
   - POS receipts (Point of Sale from Pakistan, India, etc.)
   - Any receipt in any language

6. MARK SPECIAL ELEMENTS:
   - If a price is crossed out or has a strikethrough, append "[STRIKETHROUGH]" after the price
   - Example: "Was $19.99 Now $14.99" with strikethrough on $19.99 → "Was $19.99[STRIKETHROUGH] Now $14.99"
   - If a line is a discount with negative amount, keep the negative sign exactly as shown
   - If there are handwritten notes or modifications, include them
   - If something is circled or highlighted, include it as is

7. PRESERVE ORDER:
   - Keep every line in the exact order it appears on the receipt
   - Do not rearrange, reorder, or sort any lines
   - Do not move tax lines, subtotals, or totals to the bottom if they appear elsewhere

8. NO MODIFICATIONS:
   - Do NOT add any text that isn't on the receipt
   - Do NOT remove any text that is on the receipt
   - Do NOT correct spelling or formatting
   - Do NOT add explanations or notes
   - Do NOT use markdown or code blocks
   - Do NOT normalize spacing
   - Do NOT trim trailing or leading spaces

9. YOUR ONLY JOB IS EXTRACTION:
   - Extract EVERY line exactly as shown
   - Do NOT decide what is an item vs what is tax/total/payment
   - Do NOT filter anything out
   - Just copy everything exactly as it appears
   - The backend will handle parsing and filtering

Return ONLY the raw text with each line exactly as it appears on the receipt. No explanations, no markdown, no additional text, no JSON formatting - JUST THE RAW TEXT WITH EXACT SPACING AND LINE BREAKS."""


# ==================== LLM RECONCILIATION PROMPT (For Odoo Formatting) ====================
LLM_RECONCILIATION_PROMPT = """You are an expert Receipt/Invoice Data Extraction AI for Odoo ERP. Your task is to take the raw OCR text and structure it into clean, accurate JSON for an account.move (Vendor Bill) object.

IMPORTANT: You MUST extract ALL line items from tables. Do NOT stop early!

Analyze this text carefully. It could be from:
- SUPERMARKET RECEIPT (grocery store, retail store)
- PETROL/FUEL RECEIPT (gas station, fuel pump)
- SALES/PURCHASE INVOICE (business invoice)
- RESTAURANT BILL
- PRICE QUOTATION (عرض اسعار in Arabic)
- WHOLESALE PRICE LIST
- POS RECEIPT (Point of Sale system receipts from Pakistan, India, etc.)
- ANY other commercial receipt or invoice in ANY language (Arabic, English, Urdu, etc.)

EXTRACT ALL DATA. Return ONLY valid JSON - NO explanations, NO markdown, NO thinking.

CRITICAL EXTRACTION RULES:
1. vendor_name = The BUSINESS/STORE NAME at the top of receipt
2. bill_reference = Receipt/Invoice number (look for: "Receipt #", "Invoice #", "Inv No", "SD", "Trans #", "Bill No", "Ticket #", "FG-" codes)
3. bill_date = Date on receipt in YYYY-MM-DD format (convert any date format you see)
4. currency = Detect from symbols or context (PKR for Pakistan, USD for US, EUR for Europe, BBD for Barbados, etc.)
5. invoice_lines = Extract EVERY SINGLE line item/product visible INCLUDING DISCOUNTS
6. total_amount = READ THE PRINTED "Total:" or "TOTAL" or "Grand Total" from the BOTTOM of receipt - THIS IS THE FINAL PAYMENT AMOUNT

MULTI-COLUMN RECEIPT FORMAT (Common in Pakistani/Indian POS systems):
Many receipts have columns like: [Item Code - Description] [Qty] [Unit] [Unit Price] [Discount] [Line Total]
- The RIGHTMOST column is usually the LINE SUBTOTAL for each item
- Read the LAST number on each line as the line_subtotal
- Example line: "FG-022984 - LU SP Jaferi Nankhatai 358.4g  3  1 Piece  313.00  48.81  319.00"
  → label: "LU SP Jaferi Nankhatai 358.4g", quantity: 3, price_unit: 313.00, discount: 48.81, line_subtotal: 319.00 (RIGHTMOST value)

DISCOUNT/MARKDOWN EXTRACTION (VERY IMPORTANT):
Many supermarket receipts show discounts as "Markdown" lines below products. You MUST:
- Look for lines labeled "Markdown", "Discount", "Price Reduction", "Special", "Savings", "MD"
- These are NEGATIVE amounts that reduce the price of the item above them
- Include discounts as SEPARATE line items with NEGATIVE price_unit values
- Example: If you see "Product: $5.00" followed by "Markdown: -$1.00", extract BOTH lines

LINE ITEM EXTRACTION:
- label: Product/item name or description (include "Markdown" for discount lines)
- quantity: Number of units (default 1 if not shown)
- price_unit: Price per unit (BEFORE any discounts)
- discount: Discount AMOUNT in currency (NOT percentage), 0 if no discount
- line_subtotal: FINAL amount for this line (the RIGHTMOST column value)

FOR TABULAR INVOICES (with columns like Qty, Unit Price, Amount):
- Read EVERY row in the table - DO NOT SKIP ANY ROWS
- The "Description" column contains the label (may be in Arabic or English)
- The "Qty" column is the quantity
- The "unit price" column is the price_unit
- The "Amount" or "line Amount" or RIGHTMOST column is the line_subtotal
- If there are 20+ rows, you MUST extract all of them

TAX EXTRACTION (VERY IMPORTANT):
Look for ANY of these tax-related items on the receipt or invoice:
- "Tax", "Sales Tax", "VAT", "GST", "Service Tax"
- "VAT [%]" column in tables - ALWAYS extract this percentage!
- "Sub Tax", "Subtax", "S.Tax", "ST"  
- "Service Charge", "Svc Charge", "SC"
- "Government Tax", "Govt Tax", "Fed Tax", "State Tax"
- "Tax Amount", "Tax amounts" (exact amount printed)
- Any percentage shown (like "17.5% RATE", "10%", "VAT 10%")

IMPORTANT: For tabular invoices with VAT columns:
- If you see a "VAT [%]" or "Tax %" column, extract the percentage shown (e.g., 10 for 10%)
- Set "tax_rate" to this percentage value (e.g., 10, not 10%)
- The SUMMARY section often shows the exact VAT percentage - ALWAYS extract this!

For EACH tax category you find, add it to the "taxes" array with:
- tax_name: The label shown (e.g. "VAT", "Sales Tax")
- tax_amount: The dollar/currency amount of the tax (READ from receipt)
- tax_rate: The percentage if shown (e.g. 10 for 10%, 17.5 for 17.5%)

SHIPPING, HANDLING & ADDITIONAL COSTS (VERY IMPORTANT):
Look for ANY of these additional cost items on the invoice:
- "Shipping", "Shipping and Handling", "S&H", "Freight", "Delivery"
- "Handling Fee", "Handling Charges"
- "Service Fee", "Service Charge", "Processing Fee"
- "Delivery Charges", "Courier Fee"
- "Packaging", "Packing Charges"
- Any other extra fee that is NOT a product line item

For EACH additional cost you find, add it to the "additional_charges" array with:
- charge_name: The label shown (e.g. "Shipping and Handling", "Delivery Fee")
- charge_amount: The amount for this charge

Also extract the TOTAL shipping/handling as "shipping_amount" if shown.

AMOUNT BREAKDOWN - READ FROM RECEIPT BOTTOM SECTION, DO NOT CALCULATE:
At the bottom of most receipts, you will see a summary section like:
- "Subtotal:" → This is the subtotal (products only, BEFORE taxes and shipping)
- "Tax Amount:" or "Sales Tax" → This is the tax_amount
- "Shipping:" or "S&H:" → This is shipping_amount
- "Total:" or "Grand Total:" → THIS IS THE FINAL total_amount (includes everything)

CRITICAL: The "Total:" printed at the bottom is ALWAYS the correct total_amount.
For example, if you see "Total: $178.48" at the bottom, total_amount = 178.48

FILTERING RULES (IMPORTANT):
- Only include ACTUAL PRODUCT ITEMS in invoice_lines
- Do NOT include tax lines, subtotal lines, total lines, or payment lines as invoice items
- Tax amounts go in the "taxes" array
- Payment information is NOT needed in the output
- Store information is ONLY used for vendor_name

JSON FORMAT (return ONLY this):
{
  "vendor_name": "Store Name",
  "bill_reference": "Invoice-4226",
  "bill_date": "2022-03-15",
  "due_date": "2022-04-16",
  "currency": "USD",
  "invoice_lines": [
    {"label": "Product Name", "quantity": 2, "price_unit": 18.00, "discount": 0, "line_subtotal": 36.00},
    {"label": "Another Product", "quantity": 1, "price_unit": 10.00, "discount": 0, "line_subtotal": 10.00}
  ],
  "subtotal": 156.00,
  "shipping_amount": 10.00,
  "additional_charges": [
    {"charge_name": "Shipping and Handling", "charge_amount": 10.00}
  ],
  "taxes": [
    {"tax_name": "Sales Tax 8%", "tax_amount": 12.48, "tax_rate": 8}
  ],
  "tax_amount": 12.48,
  "tax_rate": 8,
  "total_amount": 178.48
}

CRITICAL REMINDERS:
1. Extract ALL product line items from tables
2. Extract ALL taxes shown on the receipt - extract the ACTUAL tax percentage shown!
3. Extract ALL additional costs (shipping, handling, service fees, delivery, etc.)
4. tax_rate should be the EXACT percentage shown on invoice (could be 5, 8, 10, 15, 17.5, etc.)
5. READ the subtotal, tax_amount, shipping_amount, and total_amount DIRECTLY from the receipt
6. The printed "Total:" at the BOTTOM of the receipt is the correct total_amount
7. total_amount = subtotal + tax_amount + shipping_amount (verify this matches the printed total)
8. Only actual PRODUCTS go in invoice_lines - taxes, shipping, and fees go in their respective arrays
9. Do NOT include ATM, CASH, CHANGE, RECALL lines as items
10. Do NOT include store addresses, phone numbers, or website URLs as items

Return ONLY the JSON object. Nothing else."""
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
# ==================== TRULY DYNAMIC RECEIPT PARSER ====================
def dynamic_receipt_parser(raw_text):
    """
    Dynamically parse ANY receipt format without hardcoding
    Uses statistical analysis and pattern recognition
    """
    lines = raw_text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    
    logger.info("=" * 60)
    logger.info("🔍 DYNAMIC RECEIPT PARSER")
    logger.info(f"Processing {len(lines)} lines")
    
    # STEP 1: Analyze line patterns
    line_analysis = []
    for line in lines:
        analysis = {
            'text': line,
            'length': len(line),
            'word_count': len(line.split()),
            'has_digits': bool(re.search(r'\d', line)),
            'digit_count': len(re.findall(r'\d', line)),
            'has_currency': bool(re.search(r'[$€£₹]', line)),
            'has_alpha': bool(re.search(r'[A-Za-z]', line)),
            'possible_price': extract_possible_price(line),
            'is_likely_metadata': False
        }
        line_analysis.append(analysis)
    
    # STEP 2: Detect price lines
    price_lines = []
    for i, analysis in enumerate(line_analysis):
        if analysis['possible_price']:
            price = analysis['possible_price']
            if 0.01 < price < 10000:
                price_lines.append({
                    'index': i,
                    'price': price,
                    'text': analysis['text']
                })
    
    logger.info(f"💰 Found {len(price_lines)} potential price lines")
    
    # STEP 3: Detect metadata patterns statistically
    avg_length = sum(a['length'] for a in line_analysis) / len(line_analysis) if line_analysis else 0
    avg_word_count = sum(a['word_count'] for a in line_analysis) / len(line_analysis) if line_analysis else 0
    
    for i, analysis in enumerate(line_analysis):
        if analysis['length'] < avg_length * 0.5 or analysis['length'] > avg_length * 1.5:
            analysis['is_likely_metadata'] = True
        if analysis['digit_count'] > 3 and not analysis['has_alpha']:
            analysis['is_likely_metadata'] = True
    
    # STEP 4: Find item names
    items = []
    
    for price_info in price_lines:
        price_idx = price_info['index']
        price = price_info['price']
        
        best_item = None
        best_score = 0
        
        for lookback in range(1, min(6, price_idx + 1)):
            candidate_idx = price_idx - lookback
            candidate = line_analysis[candidate_idx]
            
            if candidate['is_likely_metadata']:
                continue
            
            score = 0
            if candidate['has_alpha']:
                score += 3
            if 5 < candidate['length'] < 50:
                score += 2
            if not candidate['possible_price']:
                score += 2
            score += (5 - lookback)
            
            if score > best_score:
                best_score = score
                best_item = candidate['text']
        
        if best_item and best_score > 5:
            quantity = 1
            if price_idx > 1:
                prev_line = line_analysis[price_idx - 1]['text']
                qty_match = re.match(r'^(\d+\.?\d*)$', prev_line)
                if qty_match:
                    qty = float(qty_match.group(1))
                    if 1 <= qty <= 100:
                        quantity = qty
            
            clean_name = re.sub(r'^[\d\s]+', '', best_item)
            clean_name = re.sub(r'[$€£₹]', '', clean_name)
            clean_name = clean_name.strip()
            
            items.append({
                'label': clean_name[:100],
                'quantity': int(quantity) if quantity.is_integer() else quantity,
                'price_unit': round(price / quantity, 2),
                'original_line': best_item
            })
            
            logger.info(f"✅ Found: '{clean_name}' | Qty: {quantity} | Price: ${price}")
    
    # STEP 5: Statistical filtering
    if items:
        avg_price = sum(item['price_unit'] for item in items) / len(items)
        filtered_items = [
            item for item in items 
            if 0.01 < item['price_unit'] < avg_price * 10
        ]
        logger.info(f"📊 After filtering: {len(filtered_items)} items")
        return filtered_items
    
    return []

# ========== ALSO ADD THIS HELPER FUNCTION ==========
def extract_possible_price(text):
    """Extract a possible price from text"""
    clean = re.sub(r'[$€£₹,]', '', text)
    matches = re.findall(r'\d+\.?\d*', clean)
    if matches:
        try:
            return float(matches[-1])
        except:
            pass
    return None

# ==================== PREPARE ODOO DATA - COMPLETE MERGED VERSION ====================
def prepare_odoo_data(receipt_data):
    """
    Prepare data for Odoo upload - Filters out non-items and uses dynamic parsing
    Combines keyword filtering with smart pattern recognition
    """
    try:
        # Get data from receipt
        formatted = receipt_data.get('formatted_data', {})
        raw_text = receipt_data.get('text', '')
        
        logger.info("=" * 60)
        logger.info("🔍 PREPARING ODOO DATA - COMPLETE PARSING")
        logger.info(f"Raw text length: {len(raw_text)} chars")
        
        # ===== STEP 1: Extract basic info =====
        vendor_name = formatted.get('vendor_name', 'Unknown Vendor')
        bill_date = formatted.get('bill_date', datetime.now().strftime('%Y-%m-%d'))
        
        # ===== STEP 2: Use discount-aware parser =====
        parsed_result = parse_receipt_dynamic(raw_text)
        items = parsed_result.get('invoice_lines', [])
        
        logger.info(f"📊 After discount-aware parsing: {len(items)} items")
        
        # ===== STEP 3: Apply strict filtering =====
        filtered_items = filter_odoo_items(items)
        
        # ===== STEP 4: Try to extract date if not in formatted data =====
        if not bill_date or bill_date == datetime.now().strftime('%Y-%m-%d'):
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',   # MM/DD/YYYY
                r'\d{2}-\d{2}-\d{4}',   # MM-DD-YYYY
                r'\d{2}\.\d{2}\.\d{4}', # MM.DD.YYYY
            ]
            
            lines = raw_text.split('\n')
            for line in lines:
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        date_str = match.group()
                        try:
                            if '/' in date_str:
                                parts = date_str.split('/')
                                bill_date = f"{parts[2]}-{parts[0]}-{parts[1]}"
                            elif '-' in date_str and len(date_str) == 10:
                                bill_date = date_str
                            elif '.' in date_str:
                                parts = date_str.split('.')
                                bill_date = f"{parts[2]}-{parts[0]}-{parts[1]}"
                            logger.info(f"📅 Found date: {bill_date}")
                            break
                        except:
                            pass
                    if bill_date != datetime.now().strftime('%Y-%m-%d'):
                        break
        
        # ===== STEP 5: If still no items, use raw text as note =====
        if not filtered_items:
            logger.warning("⚠️ No items found after parsing")
            return {
                'vendor_name': vendor_name,
                'bill_date': bill_date,
                'due_date': bill_date,
                'currency': detect_currency(raw_text),
                'invoice_lines': [],
                'narration': f"Raw receipt text:\n{raw_text}"
            }
        
        # ===== STEP 6: Final logging and return =====
        logger.info("=" * 60)
        logger.info(f"📊 FINAL ITEMS FOR ODOO ({len(filtered_items)}):")
        for idx, item in enumerate(filtered_items, 1):
            total = item['quantity'] * item['price_unit']
            discount_tag = " (DISCOUNT)" if item.get('is_discount') else ""
            logger.info(f"   {idx}. {item['label'][:30]}{discount_tag}: {item['quantity']} x ${item['price_unit']:.2f} = ${total:.2f}")
        logger.info("=" * 60)
        
        return {
            'vendor_name': vendor_name,
            'bill_date': bill_date,
            'due_date': bill_date,
            'currency': detect_currency(raw_text),
            'invoice_lines': filtered_items,
            'subtotal': parsed_result.get('subtotal'),
            'tax_amount': parsed_result.get('tax_amount'),
            'total_amount': parsed_result.get('total_amount')
        }
        
    except Exception as e:
        logger.error(f"❌ Error in prepare_odoo_data: {e}")
        traceback.print_exc()
        return {
            'vendor_name': 'Unknown Vendor',
            'bill_date': datetime.now().strftime('%Y-%m-%d'),
            'due_date': datetime.now().strftime('%Y-%m-%d'),
            'currency': 'USD',
            'invoice_lines': [],
            'narration': f"Error processing receipt. Raw text:\n{receipt_data.get('text', '')}"
        }

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
        
        # STEP 1: Extract base64 image
        if 'base64,' in original_image:
            image_for_vlm = original_image.split('base64,')[1]
        else:
            image_for_vlm = original_image
        
        # STEP 2: Check image quality
        logger.info("🔍 Checking image quality...")
        assessment = preprocessor.quick_assessment(original_image)
        
        quality_status = "GOOD" if not assessment['needs_preprocessing'] else "POOR"
        logger.info(f"📊 Image Quality: {quality_status}")
        logger.info(f"   Resolution: {assessment.get('resolution', 'Unknown')}")
        logger.info(f"   Sharpness: {assessment.get('sharpness', 'Unknown')}")
        
        # STEP 3: Apply preprocessing ONLY if needed
        enhanced_image = None
        if assessment['needs_preprocessing']:
            logger.info("🔄 Image needs enhancement - applying preprocessing...")
            enhanced_image = preprocessor.preprocess(original_image)
            
            if enhanced_image:
                # Extract base64 without prefix
                if 'base64,' in enhanced_image:
                    image_for_vlm = enhanced_image.split('base64,')[1]
                else:
                    image_for_vlm = enhanced_image
                logger.info("✅ Preprocessing applied successfully")
            else:
                logger.warning("⚠️ Preprocessing failed, using original image")
        else:
            logger.info("✅ Image quality is good - skipping preprocessing")
        
        # STEP 4: Continue with VLM extraction
        logger.info("🔥 STEP 1: VLM extracting raw text...")
        success, vlm_result = extract_text_with_vlm(image_for_vlm)
        
        if not success:
            return jsonify({'success': False, 'error': vlm_result}), 500
        
        # STEP 5: Parse with discount-aware parser
        parsed_result = parse_receipt_dynamic(vlm_result['text'])
        
        # STEP 6: Prepare formatted data
        formatted_data = {
            'vendor_name': 'Unknown Vendor',
            'bill_reference': '',
            'bill_date': datetime.now().strftime('%Y-%m-%d'),
            'currency': detect_currency(vlm_result['text']),
            'invoice_lines': parsed_result.get('invoice_lines', []),
            'subtotal': parsed_result.get('subtotal', 0),
            'tax_amount': parsed_result.get('tax_amount', 0),
            'total_amount': parsed_result.get('total_amount', 0)
        }
        
        # STEP 7: Return results with quality info
        result = {
            'text': vlm_result['text'],
            'formatted_data': formatted_data,
            'vlm_model': VLM_MODEL,
            'tokens_used': vlm_result.get('tokens_used', 0),
            'enhanced_image': enhanced_image if assessment['needs_preprocessing'] and enhanced_image else original_image,
            'quality_assessment': {
                'needed_preprocessing': assessment['needs_preprocessing'],
                'resolution': assessment.get('resolution', 'Unknown'),
                'sharpness': assessment.get('sharpness', 'Unknown'),
                'quality_status': quality_status
            }
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
        
        # The frontend now sends the EDITED preview data directly
        receipt_data = data.get('receipt_data', {})
        original_image = data.get('original_image', '')
        
        # FIX: Use environment variables as fallback if frontend data is missing
        odoo_connector = OdooConnector(
            data.get('odoo_url') or ODOO_URL,
            data.get('odoo_db') or ODOO_DB, 
            data.get('odoo_username') or ODOO_USERNAME,
            data.get('odoo_password') or ODOO_PASSWORD
        )
        
        # Debug logging
        logger.info(f"DEBUG: Attempting Odoo connection with URL: {data.get('odoo_url') or ODOO_URL}, DB: {data.get('odoo_db') or ODOO_DB}, User: {data.get('odoo_username') or ODOO_USERNAME}")
        
        if not odoo_connector.connect():
            logger.error("❌ CRITICAL: Could not connect to Odoo.")
            return jsonify({'success': False, 'error': 'Could not connect to Odoo'}), 500
        
        # Check if check_access_rights method exists before calling it
        if hasattr(odoo_connector, 'check_access_rights'):
            try:
                has_access = odoo_connector.check_access_rights('account.move', 'create')
                logger.info(f"🔑 User has 'create' access for account.move: {has_access}")
                
                if not has_access:
                    return jsonify({'success': False, 'error': 'User lacks permission to create Vendor Bills'}), 403
            except Exception as e:
                logger.warning(f"⚠️ Could not check access rights: {e}")
                # Continue anyway - the create_vendor_bill will fail if permissions are insufficient
        else:
            logger.warning("⚠️ check_access_rights method not found, skipping permission check")
        
        # Use the EDITED data directly from preview (NO additional filtering)
        odoo_data = {
            'vendor_name': receipt_data.get('vendor_name', 'Unknown Vendor'),
            'bill_date': receipt_data.get('bill_date', datetime.now().strftime('%Y-%m-%d')),
            'due_date': receipt_data.get('due_date', receipt_data.get('bill_date', datetime.now().strftime('%Y-%m-%d'))),
            'currency': receipt_data.get('currency', detect_currency(receipt_data.get('text', ''))),
            'invoice_lines': receipt_data.get('invoice_lines', [])
        }
        
        # Validate that we have invoice lines
        if not odoo_data or not odoo_data.get('invoice_lines'):
            logger.error("❌ No invoice lines to upload")
            return jsonify({'success': False, 'error': 'No items to upload'}), 400
        
        logger.info(f"📤 Uploading EDITED preview data with {len(odoo_data['invoice_lines'])} items")
        
        # Create vendor bill with image attachment
        bill_result = odoo_connector.create_vendor_bill(odoo_data, original_image)
        
        if bill_result:
            bill_id = bill_result.get('id')
            
            # Generate Odoo URL to view the bill
            odoo_base = data.get('odoo_url') or ODOO_URL
            if odoo_base:
                bill_url = f"{odoo_base.rstrip('/')}/web#id={bill_id}&model=account.move"
            else:
                bill_url = f"https://kainatcecos4.odoo.com/web#id={bill_id}&model=account.move"
            
            logger.info(f"✅ Bill created successfully! ID: {bill_id}")
            logger.info(f"🔗 View bill at: {bill_url}")
            
            return jsonify({
                'success': True, 
                'bill_id': bill_id,
                'bill_url': bill_url,
                'message': f'Bill created successfully with {len(odoo_data["invoice_lines"])} items from your edited preview'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create bill'}), 500
            
    except Exception as e:
        logger.error(f"❌ Upload error: {str(e)}")
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