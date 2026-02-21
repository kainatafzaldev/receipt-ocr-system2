# 🚀 Quick Start Guide - OCR Receipt Processor

## What does this project do?

1. **Upload Receipt** → Upload any receipt image (JPG, PNG, GIF, WebP, PDF)
2. **Process with AI** → Extract text using advanced AI OCR
3. **View Data** → See all extracted information (items, prices, dates, etc.)
4. **Ready for Odoo** → Data formatted and ready to upload to Odoo ERP

---

## ⚙️ Setup (One-Time)

### 1️⃣ Get Novita API Key
1. Go to https://novita.ai/
2. Create account or login
3. Get your API key from the dashboard
4. Copy the key (starts with `sk_`)

### 2️⃣ Update .env File
Edit `backend/.env` and update:
```
NOVITA_API_KEY=paste_your_key_here
PORT=5000
DEBUG=True
```

### 3️⃣ Install Dependencies (First Time Only)
```bash
cd backend
pip install -r ../requirements.txt
```

Or just double-click `START_SERVER.bat` (it will install automatically)

---

## ▶️ Run the Project

### **Windows Users - Easy Way:**
1. Double-click **`START_SERVER.bat`** in the project folder
2. Wait for server to start (shows "Running on http://localhost:5000")
3. Open browser to **http://localhost:5000**

### **Windows Users - Manual Way:**
```bash
cd backend
python main.py
```

### **Mac/Linux Users:**
```bash
cd backend
python main.py
```

---

## 📸 How to Use

### Step 1: Check Backend Connection
![Status Check]
- Look at top of page
- Should show "Backend: ✅ Connected"
- Should show "API Key: ✅ Known"

If not connected:
- Make sure backend is running
- Check http://localhost:5000 in browser directly
- See **Troubleshooting** section below

### Step 2: Upload Receipt
- **Drag & Drop**: Drag image onto the upload area
- **Or Click**: Click "Browse Files" button
- Supported formats: JPG, PNG, GIF, WebP, PDF
- Max file size: 10MB

### Step 3: Preview & Process
- Image preview appears after upload
- Click **"Process Receipt"** button
- Wait for spinning animation (usually 2-5 seconds)

### Step 4: View Results
The system will show:
- ✅ **Extracted Text** - All text from receipt
- ✅ **Vendor Info** - Store name, address, phone
- ✅ **Items** - Products and prices
- ✅ **Dates** - Transaction date/time
- ✅ **Financial Summary** - Subtotal, tax, total
- ✅ **Statistics** - Token usage, processing time

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                │
│        HTML + CSS + JavaScript (index.html)         │
│  - File upload & preview                            │
│  - Send image to backend                            │
│  - Display extracted data                           │
│  - Connection status                                │
└───────────────┬─────────────────────────────────────┘
                │ HTTP POST to /api/process-receipt
                │
┌───────────────▼─────────────────────────────────────┐
│               BACKEND (Flask Server)                 │
│              Backend on Port 5000                    │
│  - Serve frontend files                             │
│  - Receive image data                               │
│  - Call Novita AI API                               │
│  - Clean & format text                              │
│  - Return structured JSON                           │
└───────────────┬─────────────────────────────────────┘
                │ API Call
                │
┌───────────────▼─────────────────────────────────────┐
│           NOVITA AI - DeepSeek OCR-2                 │
│              (Cloud AI Service)                      │
│  - Extract text from image                          │
│  - Support multiple languages                       │
│  - Return extracted content                         │
└─────────────────────────────────────────────────────┘
```

---

## 🔌 API Endpoints

### 1. Health Check
```
GET http://localhost:5000/api/health
```
Response: `{ status: "healthy", api_key_configured: true, ... }`

### 2. Process Receipt (Main Endpoint)
```
POST http://localhost:5000/api/process-receipt
Content-Type: application/json

{
  "image": "data:image/png;base64,iVBORw0KGgoAA..."
}
```

Response:
```json
{
  "success": true,
  "data": {
    "text": "Extracted receipt text...",
    "raw_text": "Original OCR output...",
    "tokens_used": 150,
    "model": "deepseek/deepseek-ocr-2"
  },
  "processing_time_seconds": 2.45
}
```

### 3. Test Endpoint
```
GET http://localhost:5000/api/test
```
Response: `{ success: true, message: "API is working correctly!" }`

---

## 🐛 Troubleshooting

### ❌ "Cannot connect to backend"

**Solution 1: Check Backend is Running**
```
# Open new terminal and run:
cd backend
python main.py
```
Look for: `Running on http://127.0.0.1:5000`

**Solution 2: Check Port 5000**
```
# Windows - check what's using port 5000:
netstat -ano | findstr :5000

# Kill the process using the port:
taskkill /PID <PID> /F
```

**Solution 3: Firewall**
- Make sure Windows Firewall allows Python
- Or disable firewall for testing

---

### ❌ "Invalid API key" Error

**Solution:**
1. Check your `.env` file: `backend/.env`
2. Verify API key starts with `sk_`
3. Make sure it's not truncated
4. Try logging into https://novita.ai/ to confirm key is valid
5. Restart backend after updating
6. Refresh browser (Ctrl+F5)

---

### ❌ "No text extracted" or Empty Results

**Possible Causes:**
1. **Low quality image** - Receipt is blurry or dark
   - Try clearer, well-lit photo
   - Straight angle (not tilted)

2. **Complex receipt** - Receipts with 100+ items take longer
   - Processing time might be 10+ seconds

3. **Language issue** - Non-English receipts might have issues
   - System supports multiple languages but works best with English

4. **API issue** - Novita API might be rate limited
   - Wait a minute and try again
   - Check API usage at https://novita.ai/

---

### ⚠️ Processing Takes Too Long

**Solutions:**
1. **Reduce image size**
   - Compress image before uploading
   - Use online tool or image editor

2. **Check internet connection**
   - Backend needs connection to Novita AI API

3. **Try simpler receipt**
   - Small receipts process faster
   - Start with short receipts for testing

---

## 📝 Example Usage

### Test Receipt Image
A sample `test_receipt.png` is included in the project root.

### Step-by-step example:
1. Start server: `START_SERVER.bat` or `python backend/main.py`
2. Open http://localhost:5000
3. Upload `test_receipt.png`
4. Click "Process Receipt"
5. See extracted data appear below

---

## 🎯 Next Steps

### To Implement Odoo Integration:
1. Install Odoo or get access to existing Odoo instance
2. Get Odoo XML-RPC API credentials
3. Backend needs new endpoint to create vendor bills
4. Update frontend "Upload to Odoo" button to actually do it

### To Add More Features:
- Receipt image enhancement/preprocessing
- Duplicate receipt detection
- Manual data correction UI
- Batch processing multiple receipts
- Export results to CSV/Excel
- Receipt history/database

---

## 🚨 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| ModuleNotFoundError: flask | Flask not installed | `pip install flask` |
| Invalid API key | Wrong key in .env | Check https://novita.ai/ |
| Connection refused | Backend not running | Run `python main.py` |
| CORS error | Frontend/backend on different ports | Should not happen - using same host |
| Timeout error | API taking too long | Try smaller image or wait |

---

## 📞 Support

If something doesn't work:

1. **Check logs** - Look at terminal output when running backend
2. **Browser console** - Press F12, look at Console tab
3. **Network tab** - Press F12 > Network > refresh page
4. **Check status indicators** - Backend connection status at top of page

---

## 💡 Tips & Tricks

### Best Receipt Practices:
- Take receipt photo straight-on (not tilted)
- Good lighting (natural light is best)
- Entire receipt visible (no cropping)
- Sharp focus (not blurry)
- Plain background (not on other papers)

### Performance:
- Small receipts: 1-3 seconds
- Medium receipts: 3-8 seconds
- Large receipts (100+ items): 10-20 seconds

### File Formats:
- **JPG** - Good for photos, smaller file size
- **PNG** - Best quality, larger file size
- **WebP** - Modern format, smaller files
- **PDF** - Works but slower

---

## 📊 What Data Gets Extracted?

From each receipt, the system extracts:

- **Vendor Info**: Store name, address, phone, email
- **Purchase Info**: Receipt number, date, time
- **Items**: Product names, quantities, prices
- **Totals**: Subtotal, tax, tip, final amount
- **Payment**: Card type, last 4 digits (if available)
- **Analysis**: Receipt type (restaurant, retail, etc.)

---

## ✅ Testing Checklist

When everything is set up, verify:

- [ ] `START_SERVER.bat` runs without errors
- [ ] Server shows "Running on http://localhost:5000"
- [ ] Browser opens to http://localhost:5000
- [ ] "Backend: ✅ Connected" shows at top
- [ ] Can upload image file
- [ ] Image preview shows correctly
- [ ] "Process Receipt" button works
- [ ] Data extracts and displays
- [ ] No red error messages
- [ ] Browser console (F12) has no errors

---

## 🎓 Learning Resources

- **Flask**: https://flask.palletsprojects.com/
- **DeepSeek OCR**: https://novita.ai/
- **Odoo**: https://www.odoo.com/
- **JavaScript**: https://developer.mozilla.org/en-US/docs/Web/JavaScript/

---

**Version**: 1.0.0  
**Last Updated**: February 11, 2026  
**Status**: ✅ Ready to Use
