from odoo_integration import OdooConnector

# Initialize
odoo = OdooConnector()

# Mock data (This is what your VLM/OCR usually produces)
test_data = {
    'vendor_name': 'Test Vendor Inc',
    'bill_date': '2026-03-06',
    'invoice_lines': [
        {
            'label': 'Cloud Server Subscription',
            'quantity': 1,
            'price_unit': 45.00
        },
        {
            'label': 'Domain Maintenance',
            'quantity': 2,
            'price_unit': 15.00
        }
    ]
}

print("📤 Attempting to create a test vendor bill...")
result = odoo.create_vendor_bill(test_data)

if result:
    print(f"✅ Success! Bill created with ID: {result['id']}")
    print("Go to Odoo > Accounting > Vendors > Bills to see it.")
else:
    print("❌ Failed to create the bill. Check your terminal logs.")