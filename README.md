# Receipt OCR + Odoo Integration

A powerful receipt processing system that extracts text from receipt images using AI and integrates with Odoo ERP for automated vendor bill creation.

## 📋 Features

- **OCR Processing**: Uses Novita.ai Vision API to extract text from receipt images
- **Image Preprocessing**: Automatic enhancement for blurry, wrinkled, or low-quality receipts
- **Smart Filtering**: Automatically filters out non-item lines (taxes, totals, store info, etc.)
- **Odoo Integration**: Creates vendor bills directly in Odoo
- **Image Attachment**: Attaches original receipt images to Odoo bills
- **Quality Assessment**: Checks image quality and applies preprocessing only when needed

## 🏗️ Project Structurebackend/
├── main.py # Main Flask application
├── odoo_integration.py # Odoo connection and bill creation
├── image_preprocessor.py # Image enhancement and preprocessing
├── document_scanner.py # Document scanning utilities
├── requirements.txt # Python dependencies
├── .env # Environment variables (not in repo)
└── README.md # This documentation


## 🚀 Installation

### Prerequisites
- Python 3.8+
- Tesseract OCR (optional, for backup)
- Odoo instance (v16+)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/kainatafzaldev/receipt-ocr-system2.git
cd receipt-ocr-system2/backend

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

##Create .env file

# Novita AI API Configuration (supports DeepSeek models)
NOVITA_API_KEY=sk_W9itWypRe9KoDG5m8difsYrN4_GwoDTiB4jKOY7hFYs
OPENROUTER_API_KEY=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
API_BASE_URL=https://api.novita.ai/v3/openai
MODEL_NAME=qwen/qwen3-vl-235b-a22b-instruct
# Odoo ERP Configuration
#ODOO_URL=https://epic-marketing1.odoo.com/
#ODOO_DB=epic-marketing1
#ODOO_USERNAME=haris.herry@gmail.com
#ODOO_PASSWORD=Honda125

# Server Configuration
#PORT=5000
#DEBUG=True



# Application Settings
#UPLOAD_FOLDER=uploads
#ALLOWED_EXTENSIONS=png,jpg,jpeg,gif,webp
#MAX_FILE_SIZE=10485760  # 10MB
#TIMEOUT=120



ODOO_URL=https://kainatecos1.odoo.com
ODOO_DB=kainatecos1
ODOO_USERNAME=kainatcecos17@gmail.com
ODOO_PASSWORD=ThePasswordYouJustSet

 Usage
Start the Flask server


python main.py


Access the web interface
Open browser and navigate to http://localhost:5000

Process a receipt

Upload a receipt image

Click "Process Receipt"

Review extracted text

Click "Upload to Odoo"

View in Odoo

Click the "View Bill in Odoo" link

Review and edit the bill as needed

Confirm/Post the bill

⚙️ Configuration Options
Image Preprocessing
The system automatically checks image quality and applies preprocessing when needed:

Resolution enhancement: Upscales low-resolution images

Skew correction: Straightens tilted receipts

Noise removal: Cleans up grainy backgrounds

Contrast enhancement: Improves text readability

Shadow removal: Eliminates uneven lighting

Filtering Rules
The system filters out non-item lines including:

Restaurant/store names

Addresses and phone numbers

Tax lines and calculations

Subtotal and total lines

Payment information

Thank you messages




 API Endpoints
Endpoint	                        Method	                           Description
/api/health	                       GET	                             Check backend status
/api/process-receipt	             POST                              Process receipt image
/api/odoo/upload	                 POST	                             Upload to Odoo
/api/odoo/test-connection        	 POST                         	   Test Odoo connection
/api/test-novita	                 GET                               Test Novita.ai API


 Troubleshooting
Common Issues
Connection Status shows "Offline"

Check if Flask server is running

Verify BACKEND_URL in script.js

Check CORS configuration

Odoo authentication fails

Verify credentials in .env

For Odoo.com instances, use API key instead of password

Check if user has API access enabled

No items extracted

Check image quality

Review VLM prompt settings

Adjust filtering keywords

Image attachment fails

Verify Odoo version compatibility

Check file size limits

Ensure proper base64 encoding

🤝 Contributing
Fork the repository

Create a feature branch

Commit your changes

Push to the branch

Open a Pull Request

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

👥 Authors
Kainat Afzal - Initial work - GitHub

🙏 Acknowledgments
Novita.ai for Vision API services

Odoo Community for ERP platform

OpenCV community for image processing tools

📞 Support
For issues or questions:

Open an issue on GitHub

Contact: [kainatcecos17@gmail.com]


Version: 1.0.0
Last Updated: March 2026


## **Also create a `requirements.txt` file:**

```txt
Flask==3.0.0
Flask-CORS==4.0.1
python-dotenv==1.0.0
requests==2.31.0
Pillow==10.1.0
opencv-python==4.8.1.78
opencv-contrib-python==4.8.1.78
numpy==1.26.2
pytesseract==0.3.10

LICENSE file (optional):
MIT License

Copyright (c) 2026 Kainat Afzal

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


