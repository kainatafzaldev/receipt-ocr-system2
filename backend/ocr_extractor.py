"""
OCR Extractor using Novita AI DeepSeek OCR-2
EXACT text extraction - no JSON, no hallucinated data
"""

import os
import base64
import json
import re
import requests
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def extract_text_from_image(image_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract EXACT text from receipt image - no JSON, no hallucinated data
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API configuration
        api_key = os.getenv('NOVITA_API_KEY')
        model_name = os.getenv('MODEL_NAME', 'deepseek/deepseek-ocr-2')
        
        # Validate API key
        if not api_key or api_key == 'your_actual_api_key_here':
            logger.error("❌ NOVITA_API_KEY not configured in .env file")
            return None
        
        logger.info(f"🔑 Using API key: {api_key[:10]}...")
        logger.info(f"🤖 Using model: {model_name}")
        
        # Check if image exists
        if not os.path.exists(image_path):
            logger.error(f"❌ Image file not found: {image_path}")
            return None
        
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        logger.info(f"📷 Image loaded: {len(image_bytes)} bytes")
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine MIME type
        file_ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp'
        }
        mime_type = mime_types.get(file_ext, 'image/png')
        
        # SIMPLE PROMPT - Extract exactly what you see
        ocr_prompt = """You are an OCR system. Extract ALL text exactly as it appears on this receipt.

STRICT RULES:
1. Extract EVERY letter, number, and symbol you see on the receipt
2. Do NOT add any text that is not on the receipt
3. Do NOT summarize or interpret
4. Do NOT add JSON or markdown
5. ONLY output the actual text from the receipt, nothing else

Extract line by line, exactly as shown."""

        # Prepare API request
        url = "https://api.novita.ai/v3/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an OCR system. Extract text exactly as it appears. No JSON, no explanations, no markdown."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ocr_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.0,
            "top_p": 0.01
        }
        
        logger.info(f"🌐 Sending OCR request to Novita AI...")
        
        # Make API call
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        
        logger.info(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message'].get('content', '')
                
                # Clean the text
                if isinstance(content, list):
                    text = '\n'.join([str(c.get('text', '')) for c in content if isinstance(c, dict)])
                else:
                    text = str(content)
                
                # Remove markdown code blocks if present
                text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
                text = re.sub(r'`.*?`', '', text)
                
                # Clean up
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                cleaned_text = '\n'.join(lines)
                
                logger.info(f"✅ Successfully extracted {len(cleaned_text)} characters")
                
                # Parse the receipt text with enhanced tax extraction
                parsed_data = parse_receipt_text(cleaned_text)
                
                # Calculate tax rate for dynamic tax mapping
                if parsed_data['subtotal'] > 0 and parsed_data['tax'] > 0:
                    tax_rate = (parsed_data['tax'] / parsed_data['subtotal']) * 100
                    parsed_data['tax_rate'] = round(tax_rate, 2)
                    logger.info(f"💰 Calculated Tax Rate: {parsed_data['tax_rate']}%")
                else:
                    parsed_data['tax_rate'] = 0
                    logger.info("💰 No tax detected or subtotal is zero")
                
                return {
                    'raw_text': cleaned_text,
                    'structured_data': parsed_data,
                    'statistics': {
                        'characters': len(cleaned_text),
                        'lines': len(lines),
                        'items_found': len(parsed_data.get('items', [])),
                        'tax_rate': parsed_data.get('tax_rate', 0)  # ADDED
                    },
                    'metadata': {
                        'model': model_name,
                        'api_provider': 'Novita AI',
                        'extraction_type': 'exact_text'
                    }
                }
            else:
                logger.error("❌ No 'choices' in API response")
                return None
        else:
            logger.error(f"❌ API Error {response.status_code}: {response.text[:500]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def parse_receipt_text(text):
    """Parse receipt text into structured format with enhanced tax extraction"""
    lines = text.strip().split('\n')
    structured = {
        'vendor_name': '',
        'address': '',
        'phone': '',
        'bill_reference': '',
        'items': [],
        'subtotal': 0,
        'tax': 0,
        'total': 0,
        'payment': '',
        'recall': '',
        'tax_rate': 0  # ADDED
    }
    
    # Common tax keywords in receipts
    tax_keywords = ['TAX', 'VAT', 'GST', 'SALES TAX', 'TAX TOTAL', 'TAX AMOUNT']
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Store name
        if i == 0 and line and not structured['vendor_name']:
            structured['vendor_name'] = line
        
        # Address
        if 'BLVD' in line or 'ST' in line or 'AVE' in line or 'RD' in line:
            structured['address'] = line
        
        # Phone
        if 'Ph:' in line or '(562)' in line:
            structured['phone'] = line
        
        # Bill reference - more generic pattern
        if any(ref in line.upper() for ref in ['ORDER #', 'BILL #', 'INVOICE #', 'RECEIPT #', 'REF #']):
            # Extract just the reference number
            parts = line.split()
            for part in parts:
                if '/' in part or part.isdigit():
                    structured['bill_reference'] = part
                    break
            if not structured['bill_reference']:
                structured['bill_reference'] = line
        
        # Items - more generic pattern for any receipt
        # Look for lines with price at the end
        price_pattern = r'\d+\.\d{2}$'
        if re.search(price_pattern, line) and not any(keyword in line.upper() for keyword in tax_keywords + ['SUBTOTAL', 'TOTAL', 'BALANCE', 'CHANGE']):
            parts = line.split()
            if len(parts) >= 2:
                # Try to extract price from the end
                try:
                    price = parts[-1]
                    # Check if it's a valid price
                    if re.match(r'^\d+\.\d{2}$', price):
                        # Try to get quantity if it's at the beginning
                        qty = '1'
                        if parts[0].replace('x', '').replace('X', '').isdigit():
                            qty = parts[0].replace('x', '').replace('X', '')
                            description = ' '.join(parts[1:-1])
                        else:
                            description = ' '.join(parts[:-1])
                        
                        structured['items'].append({
                            'description': description,
                            'quantity': qty,
                            'price': float(price),
                            'line_total': float(price) * float(qty)
                        })
                except (ValueError, IndexError):
                    pass
        
        # Tax extraction - look for any line containing tax keywords
        for keyword in tax_keywords:
            if keyword in line.upper():
                match = re.search(r'(\d+\.\d{2})', line)
                if match:
                    structured['tax'] = float(match.group(1))
                    logger.info(f"💰 Found tax: {structured['tax']} in line: {line}")
                    break
        
        # Subtotal
        if 'SUBTOTAL' in line.upper():
            match = re.search(r'(\d+\.\d{2})', line)
            if match:
                structured['subtotal'] = float(match.group(1))
        
        # Total
        if 'TOTAL' in line.upper() and 'TAX' not in line.upper():
            match = re.search(r'(\d+\.\d{2})', line)
            if match:
                structured['total'] = float(match.group(1))
        
        # Payment
        if 'ATM' in line and '$' in line:
            structured['payment'] = line
        
        # Recall
        if 'RECALL' in line:
            structured['recall'] = line
    
    # If tax wasn't found but we have subtotal and total, calculate tax
    if structured['tax'] == 0 and structured['subtotal'] > 0 and structured['total'] > 0:
        calculated_tax = structured['total'] - structured['subtotal']
        if calculated_tax > 0:
            structured['tax'] = round(calculated_tax, 2)
            logger.info(f"💰 Tax calculated from total - subtotal: {structured['tax']}")
    
    # Calculate tax rate
    if structured['subtotal'] > 0 and structured['tax'] > 0:
        structured['tax_rate'] = round((structured['tax'] / structured['subtotal']) * 100, 2)
    
    return structured

# For testing
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("=" * 70)
    print("🔍 OCR EXTRACTOR - EXACT TEXT EXTRACTION")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Processing: {image_path}\n")
        
        result = extract_text_from_image(image_path)
        if result:
            print("✅ EXTRACTION SUCCESSFUL!")
            print("-" * 70)
            print("\n📄 EXTRACTED TEXT:")
            print("-" * 70)
            print(result['raw_text'])
            print("-" * 70)
            print(f"\n📊 Statistics:")
            print(f"   - Characters: {result['statistics']['characters']}")
            print(f"   - Lines: {result['statistics']['lines']}")
            print(f"   - Items found: {result['statistics']['items_found']}")
            print(f"   - Tax Rate: {result['statistics']['tax_rate']}%")  # ADDED
            print(f"\n💰 Extracted Values:")
            print(f"   - Subtotal: ${result['structured_data']['subtotal']}")
            print(f"   - Tax: ${result['structured_data']['tax']}")
            print(f"   - Tax Rate: {result['structured_data']['tax_rate']}%")
            print(f"   - Total: ${result['structured_data']['total']}")
        else:
            print("\n❌ EXTRACTION FAILED")
    else:
        print("Usage: python ocr_extractor.py <image_path>")
        print("Example: python ocr_extractor.py receipt.jpg")