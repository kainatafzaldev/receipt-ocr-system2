# odoo_integration.py
import xmlrpc.client
import logging
from datetime import datetime
import base64
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class OdooConnector:
    def __init__(self, url=None, db=None, username=None, password=None):
        # Use environment variables as fallback
        self.url = url or os.getenv('ODOO_URL', 'http://localhost:8069')
        self.db = db or os.getenv('ODOO_DB', 'odoo')
        self.username = username or os.getenv('ODOO_USERNAME', 'admin')
        self.password = password or os.getenv('ODOO_PASSWORD', 'admin')
        self.uid = None
        self.models = None
        self.common = None
    
    def connect(self):
        """Connect to Odoo"""
        try:
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                logger.info(f"✅ Connected to Odoo as {self.username}")
                return True
            else:
                logger.error("❌ Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False
    
    def create_vendor_bill(self, data):
        """Create a vendor bill in Odoo"""
        try:
            if not self.models:
                if not self.connect():
                    return None
            
            # Find or create vendor
            partner_id = self._get_or_create_partner(data.get('vendor_name', 'Unknown Vendor'))
            
            # Prepare invoice lines
            invoice_lines = []
            for line in data.get('invoice_lines', []):
                # Find or create product
                product_id = self._get_or_create_product(line.get('label', 'Unknown Product'))
                
                # Get expense account
                account_id = self._get_expense_account()
                
                invoice_lines.append((0, 0, {
                    'product_id': product_id,
                    'name': line.get('label', ''),
                    'quantity': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', 0),
                    'account_id': account_id,
                }))
            
            # Get currency ID
            currency_id = self._get_currency_id(data.get('currency', 'USD'))
            
            # Create bill - FIXED: Added invoice_line_ids back
            bill_vals = {
                'partner_id': partner_id,
                'invoice_date': data.get('bill_date', datetime.now().strftime('%Y-%m-%d')),
                'invoice_date_due': data.get('due_date', datetime.now().strftime('%Y-%m-%d')),
                'invoice_line_ids': invoice_lines,  # ← This was missing!
                'move_type': 'in_invoice',
                'currency_id': currency_id,
                'invoice_payment_term_id': False,
            }
            
            logger.info(f"Creating bill with values: {bill_vals}")
            
            bill_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'create',
                [bill_vals]
            )
            
            if bill_id:
                # Get bill number
                bill_data = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'account.move', 'read',
                    [bill_id], {'fields': ['name']}
                )
                
                bill_number = bill_data[0]['name'] if bill_data else f"BILL{str(bill_id).zfill(5)}"
                
                return {
                    'id': bill_id,
                    'number': bill_number,
                    'url': f"{self.url}/web#id={bill_id}&model=account.move"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating bill: {e}")
            return None
    
    def attach_receipt_to_bill(self, bill_id, receipt_image_base64):
        """Attach receipt image to the bill"""
        try:
            if not self.models:
                return False
            
            # Clean base64
            if 'base64,' in receipt_image_base64:
                receipt_image_base64 = receipt_image_base64.split('base64,')[1]
            
            # Create attachment
            attachment_vals = {
                'name': f'receipt_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg',
                'datas': receipt_image_base64,
                'res_model': 'account.move',
                'res_id': bill_id,
                'type': 'binary',
            }
            
            attachment_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'ir.attachment', 'create',
                [attachment_vals]
            )
            
            return bool(attachment_id)
            
        except Exception as e:
            logger.error(f"Error attaching receipt: {e}")
            return False
    
    def _get_or_create_partner(self, name):
        """Find or create a vendor partner"""
        try:
            # Search for existing partner
            partner_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'search',
                [[('name', '=', name), ('supplier_rank', '>', 0)]]
            )
            
            if partner_ids:
                return partner_ids[0]
            
            # Create new partner
            partner_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'create',
                [{
                    'name': name,
                    'supplier_rank': 1,
                    'customer_rank': 0,
                    'company_type': 'company'
                }]
            )
            
            return partner_id
            
        except Exception as e:
            logger.error(f"Error creating partner: {e}")
            # Return default partner (ID 1 is usually the main company)
            return 1
    
    def _get_or_create_product(self, name):
        """Find or create a product"""
        try:
            # Search for existing product
            product_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'product.product', 'search',
                [[('name', '=', name)]]
            )
            
            if product_ids:
                return product_ids[0]
            
            # Create new product
            product_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'product.product', 'create',
                [{
                    'name': name,
                    'type': 'consu',
                    'purchase_ok': True,
                    'sale_ok': False
                }]
            )
            
            return product_id
            
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            # Return default product
            return False
    
    def _get_expense_account(self):
        """Get default expense account"""
        try:
            # Search for expense account
            account_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.account', 'search',
                [[('account_type', '=', 'expense')]], {'limit': 1}
            )
            
            if account_ids:
                return account_ids[0]
            
            # Try alternative account type
            account_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.account', 'search',
                [[('internal_type', '=', 'expense')]], {'limit': 1}
            )
            
            if account_ids:
                return account_ids[0]
            
            logger.error("No expense account found")
            return False
            
        except Exception as e:
            logger.error(f"Error getting expense account: {e}")
            return False
    
    def _get_currency_id(self, currency_code):
        """Get currency ID by code"""
        try:
            currency_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.currency', 'search',
                [[('name', '=', currency_code)]]
            )
            
            if currency_ids:
                return currency_ids[0]
            
            # Return company currency (usually ID 1)
            return 1
            
        except Exception as e:
            logger.error(f"Error getting currency: {e}")
            return 1