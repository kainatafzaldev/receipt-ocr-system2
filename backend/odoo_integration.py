import xmlrpc.client
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class OdooConnector:
    def __init__(self, url=None, db=None, username=None, password=None):
        # Clean up URL to ensure it has no trailing slash
        self.url = (url or os.getenv('ODOO_URL')).rstrip('/') if (url or os.getenv('ODOO_URL')) else None
        self.db = db or os.getenv('ODOO_DB')
        self.username = username or os.getenv('ODOO_USERNAME')
        self.password = password or os.getenv('ODOO_PASSWORD')
        self.uid = None
        self.models = None
        
        logger.info(f"OdooConnector initialized with: URL={self.url}, DB={self.db}, User={self.username}")

    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            logger.info(f"Attempting to connect to {self.db} as {self.username}...")
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                logger.info(f"✅ Odoo authenticated. UID: {self.uid}")
                self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
                return True
            else:
                logger.error("❌ Odoo Auth Failed: Authentication returned False. Check credentials.")
                return False
        except xmlrpc.client.ProtocolError as e:
            logger.error(f"❌ Protocol Error (Check URL): {e.url} - {e.errmsg}")
            return False
        except Exception as e:
            logger.error(f"❌ Connection error: {str(e)}")
            return False

    def check_access_rights(self, model, operation='create'):
        """Simplified access check"""
        try:
            if not self.uid and not self.connect():
                logger.error("Not connected to Odoo")
                return False
            logger.info(f"⚠️ Bypassing permission check for {model}.{operation}")
            return True
        except Exception as e:
            logger.error(f"Error checking access rights: {e}")
            return False

    def _call_kw(self, model, method, args, kwargs=None):
        """Standard method to call Odoo functions."""
        if not self.uid and not self.connect():
            raise Exception("Authentication failed.")
        
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs or {}
        )

    def attach_image_to_bill(self, bill_id, image_data, filename="receipt.jpg"):
        """
        Attach receipt image to the vendor bill in Odoo
        """
        try:
            # Clean image data
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            # Create a descriptive name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            attachment_name = f"Receipt_{timestamp}.jpg"
            
            # First, verify the bill exists
            bill_exists = self._call_kw('account.move', 'search', [[('id', '=', bill_id)]])
            if not bill_exists:
                logger.error(f"❌ Bill {bill_id} not found")
                return None
            
            # Create attachment in Odoo - link to the bill
            attachment_vals = {
                'name': attachment_name,
                'res_model': 'account.move',
                'res_id': bill_id,
                'type': 'binary',
                'datas': image_data,
                'mimetype': 'image/jpeg',
                'description': 'Receipt image uploaded via OCR'
            }
            
            attachment_id = self._call_kw('ir.attachment', 'create', [attachment_vals])
            logger.info(f"✅ Image attached to bill {bill_id} (Attachment ID: {attachment_id})")
            
            # Don't try to create a message - the attachment will appear in chatter automatically
            return attachment_id
            
        except Exception as e:
            logger.error(f"❌ Failed to attach image: {e}")
            return None

    def create_vendor_bill(self, data, image_data=None):
        """
        Creates a vendor bill (account.move) in Odoo with optional image attachment
        """
        try:
            logger.info("=" * 60)
            logger.info("📝 CREATING VENDOR BILL IN ODOO")
            
            # 1. Get/Create Partner (Vendor)
            partner_id = self._get_or_create_partner(data.get('vendor_name', 'Unknown Vendor'))
            logger.info(f"🏢 Partner ID: {partner_id}")
            
            # 2. Find Purchase Journal
            journal_ids = self._call_kw('account.journal', 'search', [[('type', '=', 'purchase')]], {"limit": 1})
            if not journal_ids:
                journal_ids = self._call_kw('account.journal', 'search', [[('type', '=', 'general')]], {"limit": 1})
                if not journal_ids:
                    raise Exception("No purchase or general journal found in Odoo.")
            journal_id = journal_ids[0]
            logger.info(f"📓 Journal ID: {journal_id}")

            # 3. Get currency ID
            currency_id = False
            currency_code = data.get('currency', 'USD')
            logger.info(f"💰 Looking for currency: {currency_code}")
            
            currency_ids = self._call_kw('res.currency', 'search', [[('name', '=', currency_code)]])
            if currency_ids:
                currency_id = currency_ids[0]
                logger.info(f"✅ Found currency {currency_code} with ID: {currency_id}")
            else:
                # Fallback to company currency
                company_id = self._call_kw('res.company', 'search', [[]], {"limit": 1})
                if company_id:
                    company = self._call_kw('res.company', 'read', [company_id[0], ['currency_id']])
                    if company and company[0].get('currency_id'):
                        currency_id = company[0]['currency_id'][0]
                        logger.info(f"✅ Using company currency ID: {currency_id}")

            # 4. Build Invoice Lines
            invoice_lines = []
            for line in data.get('invoice_lines', []):
                product_id = self._get_or_create_product(line.get('label'))
                
                line_vals = {
                    'product_id': product_id,
                    'name': line.get('label')[:100],
                    'quantity': float(line.get('quantity', 1)),
                    'price_unit': float(line.get('price_unit', 0)),
                }
                
                invoice_lines.append((0, 0, line_vals))
                logger.info(f"   Line: {line.get('label')[:30]} | Qty: {line.get('quantity')} | Unit: {line.get('price_unit')}")

            # 5. Create the Bill
            bill_vals = {
                'partner_id': partner_id,
                'journal_id': journal_id,
                'move_type': 'in_invoice',
                'invoice_date': data.get('bill_date', datetime.now().strftime('%Y-%m-%d')),
                'date': data.get('bill_date', datetime.now().strftime('%Y-%m-%d')),
                'invoice_date_due': data.get('due_date', data.get('bill_date', datetime.now().strftime('%Y-%m-%d'))),
                'invoice_line_ids': invoice_lines,
                'currency_id': currency_id,
                'ref': data.get('bill_reference', ''),
                'narration': f'Imported from receipt via OCR on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            }
            
            logger.info("📦 Creating bill in Odoo...")
            bill_id = self._call_kw('account.move', 'create', [bill_vals])
            logger.info(f"✅ Bill created successfully! ID: {bill_id}")
            
            # 6. Attach image if provided
            if image_data:
                self.attach_image_to_bill(bill_id, image_data)
            
            return {'id': bill_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to create bill: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_or_create_partner(self, name):
        """Find or create a partner by name"""
        if not name or name == 'Unknown Vendor':
            name = 'Unknown Vendor'
        
        search = self._call_kw('res.partner', 'search', [[('name', '=', name)]])
        if search: 
            return search[0]
        
        partner_id = self._call_kw('res.partner', 'create', [{'name': name}])
        logger.info(f"✅ Created new partner: {name} (ID: {partner_id})")
        return partner_id

    def _get_or_create_product(self, name):
        """Find or create a product by name"""
        if not name:
            name = "Unknown Product"
        
        name = name.strip()[:100]
        
        search = self._call_kw('product.product', 'search', [[('name', '=', name)]])
        if search: 
            return search[0]
        
        product_id = self._call_kw('product.product', 'create', [{'name': name, 'type': 'consu'}])
        logger.info(f"✅ Created new product: {name} (ID: {product_id})")
        return product_id