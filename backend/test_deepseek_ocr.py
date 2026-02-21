import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('NOVITA_API_KEY')
# CORRECT model name for Novita.ai DeepSeek OCR-2
model = "deepseek/deepseek-ocr-2"  # This is the correct format!

# Use your Albetos receipt
image_path = "C:/Users/Kainat/Documents/OCR_Project/backend/images/1151-receipt.jpg"

print(f"Testing DeepSeek OCR-2")
print(f"API Key: {api_key[:10]}...")
print(f"Model: {model}")
print(f"Image: {image_path}")
print("-" * 50)

# Check if image exists
if not os.path.exists(image_path):
    print(f"❌ Image not found: {image_path}")
    # Try to find any receipt image
    import glob
    images = glob.glob("images/*.jpg") + glob.glob("images/*.jpeg") + glob.glob("images/*.png")
    if images:
        image_path = images[0]
        print(f"✅ Using instead: {image_path}")
    else:
        print("❌ No images found in images/ directory")
        exit(1)

# Read and encode image
with open(image_path, 'rb') as f:
    image_bytes = f.read()

base64_image = base64.b64encode(image_bytes).decode('utf-8')

# Novita API endpoint
url = "https://api.novita.ai/v3/openai/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Simple prompt for DeepSeek OCR-2
payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this receipt. Return ONLY the raw text."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    "max_tokens": 4096,
    "temperature": 0.01
}

print("Sending request to Novita.ai...")
try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            print("\n✅ EXTRACTED TEXT:")
            print("=" * 50)
            print(content)
            print("=" * 50)
            
            # Save to file
            with open('extracted_receipt.txt', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Saved to extracted_receipt.txt")
        else:
            print("❌ No choices in response")
            print(result)
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text[:500])
except Exception as e:
    print(f"❌ Exception: {e}")