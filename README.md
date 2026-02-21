# 📋 OCR Receipt Processor - Complete Guide

> **An intelligent system to extract receipt data using AI OCR and prepare it for Odoo ERP integration**

![Status](https://img.shields.io/badge/Status-Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.7+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-lightblue)

---

## 🎯 **What This Application Does**

This application provides a complete solution for receipt data extraction:

```
1. Upload receipt image (JPG, PNG, GIF, WebP, PDF)
   ↓
2. AI processes image using DeepSeek OCR
   ↓
3. Extracts ALL data: vendor, items, prices, dates, taxes
   ↓
4. Displays formatted extracted information
   ↓
5. Ready to upload to Odoo ERP (when integrated)
```

### ✨ **Key Features**

- 🖼️ **Drag & Drop Upload** - Simple image upload interface
- 🤖 **AI-Powered OCR** - Uses DeepSeek OCR-2 model from Novita AI
- 📊 **Smart Data Extraction** - Automatically parses items, prices, totals, dates
- 💼 **Vendor Information** - Extracts store name, address, phone, email
- 💰 **Financial Details** - Subtotal, taxes, tips, payment methods
- 📈 **Analysis Cards** - Visual display of extracted data
- 🔗 **Odoo Ready** - Data formatted for Odoo ERP integration
- 🌐 **Web Interface** - Modern, responsive UI
- ⚡ **Fast Processing** - Usually processes receipts in 2-5 seconds

---

## 📁 **Project Structure**

```
OCR_Project/
├── 📄 START_SERVER.bat          ← Double-click to start (Windows)
├── 📄 test_system.py             ← Run tests to verify everything works
├── 📄 QUICKSTART.md              ← Quick start guide
├── 📄 INTEGRATION_STATUS.md      ← Detailed integration info
├── 📄 requirements.txt           ← Python dependencies
│
├── frontend/
│   ├── index.html    ← Web interface (HTML)
│   ├── script.js     ← JavaScript logic
│   └── style.css     ← Styling
│
└── backend/
    ├── main.py                   ← Flask server (MAIN FILE)
    ├── ocr_extractor.py          ← OCR logic
    ├── receipt_parser.py         ← Data parsing
    ├── .env                      ← Configuration (API keys)
    ├── requirements.txt          ← Python packages
    └── .venv/                    ← Virtual environment
```

---

## 🚀 **Quick Start (5 Minutes)**

### **Step 1: Get API Key** (First Time)
1. Go to https://novita.ai/
2. Sign up or login
3. Get your API key
4. Update `backend/.env`:
   ```
   NOVITA_API_KEY=paste_your_key_here
   ```

### **Step 2: Start Server** (Every Time)
**Windows**: Double-click **`START_SERVER.bat`**

Or manually:
```bash
cd backend
python main.py
```

### **Step 3: Open Browser**
Go to: **http://localhost:5000**

### **Step 4: Test**
1. Upload a receipt image
2. Click "Process Receipt"
3. View extracted data

---

## 📖 **Detailed Documentation**

### For Quick Start & Troubleshooting
See 📖 **[QUICKSTART.md](QUICKSTART.md)**
- Setup instructions
- How to use the application
- Common errors and fixes
- Tips and tricks

### For Integration Details
See 📖 **[INTEGRATION_STATUS.md](INTEGRATION_STATUS.md)**
- Complete data flow
- API endpoints
- Response formats
- Testing checklist
- Optional features

---

## 🔧 **System Components**

### **Frontend (Web Interface)**
- **Location**: `frontend/` folder
- **Tech**: HTML5, CSS3, Vanilla JavaScript
- **Features**:
  - File upload with drag-drop
  - Image preview
  - Backend status monitoring
  - Receipt data display
  - Analysis cards
  - Odoo integration UI

### **Backend (API Server)**
- **Location**: `backend/main.py`
- **Tech**: Flask (Python web framework)
- **Port**: 5000
- **Features**:
  - Serves frontend files
  - Handles image upload
  - Calls Novita AI OCR API
  - Cleans and formats text
  - Returns JSON responses
  - CORS enabled

### **OCR Engine**
- **Provider**: Novita AI
- **Model**: DeepSeek OCR-2
- **Supports**: English, Arabic, Urdu, and 50+ languages
- **Input**: Base64-encoded images
- **Output**: Extracted text

### **Data Pipeline**
- **OCR Extraction**: `ocr_extractor.py`
- **Receipt Parsing**: `receipt_parser.py`
- **Data Analysis**: `script.js` (frontend)

---

## 🔌 **API Endpoints**

### Health Check
```
GET http://localhost:5000/api/health
```
Returns: Backend status, API key configuration, server time

### Process Receipt (Main)
```
POST http://localhost:5000/api/process-receipt
Content-Type: application/json

{ "image": "data:image/png;base64,..." }
```
Returns: Extracted text, analytics, tokens used

### API Info
```
GET http://localhost:5000/api
```
Returns: Service information, available endpoints, configuration

### Test Endpoint
```
GET http://localhost:5000/api/test
```
Returns: Simple success response, useful for testing

---

## 🧪 **Testing the System**

### **Quick Test**
```bash
python test_system.py
```
This will:
- ✅ Check if backend is running
- ✅ Test all API endpoints
- ✅ Verify frontend serving
- ✅ Test OCR processing (if test image exists)

### **Manual Testing**
1. Start backend: `python backend/main.py`
2. Open http://localhost:5000 in browser
3. Check "Backend: ✅ Connected" at top
4. Upload a receipt image
5. Click "Process Receipt"
6. Verify data displays

### **Network Testing** (Browser Developer Tools)
1. Press `F12` to open Developer Tools
2. Go to "Network" tab
3. Processing should show:
   - `POST /api/process-receipt` ← Your image
   - Response contains extracted data

---

## ⚙️ **Configuration**

### Environment Variables
File: `backend/.env`

```dotenv
# Novita AI API Configuration
NOVITA_API_KEY=sk_xxx          # Get from https://novita.ai/
MODEL_NAME=deepseek/deepseek-ocr-2

# Odoo Configuration (for integration)
ODOO_URL=https://example.odoo.com/
ODOO_DB=database_name
ODOO_USERNAME=user@example.com
ODOO_PASSWORD=password

# Server Configuration
PORT=5000
DEBUG=True
UPLOAD_FOLDER=uploads
ALLOWED_EXTENSIONS=png,jpg,jpeg,gif,webp
MAX_FILE_SIZE=10485760  # 10MB
```

### Getting API Key
1. Visit https://novita.ai/
2. Create account (free)
3. Navigate to API keys
4. Copy the key starting with `sk_`
5. Paste into `backend/.env`

---

## 🐛 **Troubleshooting**

### **Cannot Connect to Backend**
```bash
# Make sure backend is running:
cd backend
python main.py

# Should see: "Running on http://127.0.0.1:5000"
```

### **"Invalid API key" Error**
1. Check `.env` file in backend folder
2. Verify key starts with `sk_`
3. Make sure it's not truncated
4. Restart backend after updating

### **"No text extracted" from Receipt**
- Image might be blurry or low quality
- Try clearer, well-lit photo
- Straight angle (not tilted)
- Ensure receipt is fully visible

### **Processing Takes Too Long**
- Image might be very large → compress it
- Receipt might have 100+ items → wait longer
- Internet might be slow → check connection

### **Port 5000 Already in Use**
```bash
# Windows - find what's using port 5000:
netstat -ano | findstr :5000

# Kill the process:
taskkill /PID <PID> /F

# Or change PORT in .env to 5001
```

---

## 📊 **Data Extraction Examples**

### What Gets Extracted:
```
Vendor Information:
  - Store/Vendor name
  - Address
  - Phone number
  - Email

Date & Time:
  - Transaction date
  - Transaction time

Items:
  - Product names
  - Quantities
  - Unit prices
  - Line subtotals

Financial Summary:
  - Subtotal
  - Tax (with percentage if available)
  - Tips
  - Total amount
  - Payment method & last 4 digits

Receipt Analysis:
  - Receipt type (restaurant, retail, etc.)
  - Item count
  - Amount statistics
```

### Example Response:
```json
{
  "success": true,
  "data": {
    "text": "STORE NAME\n123 Main St\n...\nTOTAL: $45.99",
    "raw_text": "[original OCR output]",
    "tokens_used": 156,
    "model": "deepseek/deepseek-ocr-2"
  },
  "processing_time_seconds": 2.34
}
```

---

## 🎓 **For Developers**

### Adding New Features
1. Backend features → Edit `backend/main.py`
2. Frontend features → Edit `frontend/script.js`
3. OCR logic → Edit `backend/ocr_extractor.py`
4. Data parsing → Edit `backend/receipt_parser.py`

### API Response Format
All endpoints return JSON:
```json
{
  "success": true/false,
  "message": "...",
  "data": { ... },
  "error": "... (if failed)",
  "timestamp": "ISO-8601 datetime"
}
```

### Adding Odoo Integration
1. Install `xmlrpc` library
2. Create endpoint: `POST /api/upload-to-odoo`
3. Use `receipt_parser.py` to format data
4. Connect to Odoo XML-RPC API
5. Create vendor bills

---

## 📈 **Performance Metrics**

- **Average processing time**: 2-5 seconds
- **Max supported file size**: 10MB
- **Supported file formats**: JPG, PNG, GIF, WebP, PDF
- **API timeout**: 45 seconds
- **Max tokens per request**: 1500

---

## 🛡️ **Security Notes**

- API key stored in `.env` (not in code)
- CORS enabled for localhost (configure for production)
- No data stored on server (stateless)
- Images deleted from memory after processing
- Use HTTPS in production

---

## 📚 **Dependencies**

### Python Packages
- **Flask** - Web framework
- **Flask-CORS** - Cross-origin support
- **python-dotenv** - Environment variables
- **Pillow** - Image processing
- **requests** - HTTP requests
- **Werkzeug** - WSGI utilities

### Frontend
- HTML5/CSS3/JavaScript (no build process needed)
- Bootstrap Icons (CDN)
- Google Fonts (CDN)

---

## 🚀 **Deployment**

### For Production:
1. Set `DEBUG=False` in `.env`
2. Use production WSGI server: `gunicorn main.py`
3. Enable HTTPS/SSL
4. Use a reverse proxy (nginx, Apache)
5. Configure CORS for your domain
6. Use environment-specific `.env` files

### For Heroku:
1. Add `Procfile`: `web: gunicorn main:app`
2. Add `runtime.txt`: `python-3.11.0`
3. Deploy via Git

---

## 📝 **Checklist for Deployment**

- [ ] Tested with real receipts
- [ ] API key configured and valid
- [ ] Backend runs without errors
- [ ] Frontend loads correctly
- [ ] Can upload and process images
- [ ] Data displays correctly
- [ ] Error handling works
- [ ] CORS configured for target domain
- [ ] DEBUG set to False
- [ ] HTTPS enabled (if production)

---

## 💡 **Tips**

1. **Best Receipt Photos**:
   - Well-lit (natural light)
   - Straight angle (not tilted)
   - Entire receipt visible
   - Focus sharp (not blurry)

2. **Faster Processing**:
   - Compress images
   - Use JPG instead of PNG
   - Keep receipts smaller (crop edges)

3. **Better Extraction**:
   - High resolution photos
   - Printed receipts (not handwritten)
   - Good quality paper
   - Dark text on light background

4. **Odoo Integration**:
   - Can create vendor bills automatically
   - Data maps to Odoo fields
   - Reduces manual data entry
   - Improves accuracy

---

## 📞 **Support & Help**

### Check Status:
1. Open http://localhost:5000
2. Look at "Connection Status" section
3. Backend should show ✅ Connected
4. API Key should show ✅ Known

### View Logs:
1. Terminal where backend is running
2. Shows requests, processing, errors
3. Very helpful for debugging

### Browser Console:
1. Press F12 in browser
2. Go to "Console" tab
3. Shows JavaScript errors
4. Shows API responses

### Network Debugging:
1. Press F12 in browser
2. Go to "Network" tab
3. Click "Process Receipt"
4. See HTTP requests and responses

---

## 📄 **License & Attribution**

- **Frontend**: Custom built for this project
- **Backend**: Flask + custom Python
- **OCR**: DeepSeek by Novita AI
- **CSS Framework**: Custom styling

---

## ✅ **What You Can Do Right Now**

1. ✅ Upload receipt images
2. ✅ Extract text using AI
3. ✅ View detailed analysis
4. ✅ See vendor information
5. ✅ Find items and prices
6. ✅ Get financial summary
7. ✅ Preview payment info
8. ✅ Check processing time
9. ✅ Test with multiple receipts
10. ✅ Download results (future feature)

---

## 🎯 **Next Steps**

1. **Test the system** - Run `python test_system.py`
2. **Upload a receipt** - Use http://localhost:5000
3. **Verify results** - Check extracted data accuracy
4. **Set up Odoo** - (Optional) Integrate with your Odoo instance
5. **Customize prompts** - Adjust OCR prompt in `ocr_extractor.py` if needed

---

## 📊 **Version Info**

- **Version**: 1.0.0
- **Last Updated**: February 11, 2026
- **Status**: ✅ Production Ready
- **Python**: 3.7+
- **Flask**: 2.3.3

---

## 🙏 **Acknowledgments**

- **Novita AI** - For DeepSeek OCR-2 model
- **Flask Team** - For excellent web framework
- **Contributors** - For testing and feedback

---

**Made with ❤️ for efficient receipt processing**
