import os
import base64
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

print("=== SIMPLE NOVITA OCR TEST ===")

# Load environment
load_dotenv()

api_key = os.getenv('NOVITA_API_KEY')
print(f"API Key present: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"Key starts with: {api_key[:10]}...")
    print(f"Key length: {len(api_key)}")

# Find or create test image
test_image = None
if Path('uploads').exists():
    images = list(Path('uploads').glob('*.png')) + list(Path('uploads').glob('*.jpg'))
    if images:
        test_image = str(images[0])
        print(f"Found test image: {test_image}")

if not test_image:
    print("Creating test image...")
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (400, 200), color='white')
    d = ImageDraw.Draw(img)
    d.text((10,10), "TEST RECEIPT\nDate: 2026-02-10\nStore: Test Mart\nItem: Apple - $2.99\nTotal: $24.99", fill='black')
    test_image = 'test_receipt.png'
    img.save(test_image)
    print(f"Created: {test_image}")

# Read image
with open(test_image, 'rb') as f:
    image_bytes = f.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

print(f"Image size: {len(image_bytes)} bytes")
print(f"Base64 length: {len(base64_image)} chars")

# Make API call
url = "https://api.novita.ai/v3/openai/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "deepseek/deepseek-ocr-2",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this receipt image."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    "max_tokens": 1000,
    "temperature": 0.1
}

print(f"\nSending request to Novita AI...")
print(f"URL: {url}")
print(f"Model: {payload['model']}")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"\nResponse Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("SUCCESS: Request reached Novita and will show as 'used'")
        
        text = result['choices'][0]['message']['content']
        print(f"\nExtracted text ({len(text)} chars):")
        print("-" * 50)
        print(text[:500] + ("..." if len(text) > 500 else ""))
        print("-" * 50)
        
        # Token usage
        if 'usage' in result:
            usage = result['usage']
            print(f"\nToken Usage:")
            print(f"  Prompt tokens: {usage.get('prompt_tokens')}")
            print(f"  Completion tokens: {usage.get('completion_tokens')}")
            print(f"  Total tokens: {usage.get('total_tokens')}")
            print("\nThis will appear in Novita dashboard under 'Last Used'")
            
    else:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}")
    print(f"Error: {str(e)}")
    
print("\nTest completed.")
