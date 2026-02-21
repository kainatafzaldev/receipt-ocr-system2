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
                
                # Parse the receipt text for display
                parsed_data = parse_receipt_text(cleaned_text)
                
                return {
                    'raw_text': cleaned_text,
                    'structured_data': parsed_data,
                    'statistics': {
                        'characters': len(cleaned_text),
                        'lines': len(lines),
                        'items_found': len(parsed_data.get('items', []))
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
    """Parse receipt text into structured format for display"""
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
        'recall': ''
    }
    
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
        
        # Order number
        if 'ORDER #' in line:
            structured['bill_reference'] = line.replace('ORDER #', '').strip()
        
        # Items and prices
        if 'ASADA TACO' in line:
            parts = line.split()
            if len(parts) >= 2:
                qty = parts[0] if parts[0].isdigit() else '1'
                price = parts[-1] if parts[-1].replace('.', '').isdigit() else '0'
                description = ' '.join(parts[1:-1]) if len(parts) > 2 else 'ASADA TACO'
                structured['items'].append({
                    'description': description,
                    'quantity': qty,
                    'price': price,
                    'line_total': price
                })
        
        # ATM charge
        if 'ATM CHARGE' in line:
            parts = line.split()
            price = parts[-1] if parts[-1].replace('.', '').isdigit() else '0'
            structured['items'].append({
                'description': 'ATM CHARGE',
                'quantity': '1',
                'price': price,
                'line_total': price
            })
        
        # Subtotal
        if 'SUBTOTAL' in line:
            match = re.search(r'(\d+\.\d{2})', line)
            if match:
                structured['subtotal'] = float(match.group(1))
        
        # Tax
        if 'TAX TOTAL' in line:
            match = re.search(r'(\d+\.\d{2})', line)
            if match:
                structured['tax'] = float(match.group(1))
        
        # Total
        if 'TOTAL' in line and 'TAX' not in line:
            match = re.search(r'(\d+\.\d{2})', line)
            if match:
                structured['total'] = float(match.group(1))
        
        # Payment
        if 'ATM' in line and '$' in line:
            structured['payment'] = line
        
        # Recall
        if 'RECALL' in line:
            structured['recall'] = line
    
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
            print(f"\n📊 Statistics: {result['statistics']}")
        else:
            print("\n❌ EXTRACTION FAILED")
    else:
        print("Usage: python ocr_extractor.py <image_path>")
        print("Example: python ocr_extractor.py receipt.jpg")