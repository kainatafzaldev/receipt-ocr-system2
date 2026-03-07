import xmlrpc.client
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class OdooConnector:
    def __init__(self, url=None, db=None, username=None, password=None):
        # Clean up URL to ensure it has no trailing slash
        self.url = (url or os.getenv('ODOO_URL', 'https://kainatcecos4.odoo.com')).rstrip('/')
        self.db = db or os.getenv('ODOO_DB', 'kainatcecos4')
        self.username = username or os.getenv('ODOO_USERNAME', 'kainatcecos17@gmail.com')
        self.password = password or os.getenv('ODOO_PASSWORD', '41680a891e21db977c4ecb432b42600faffa4c8')
        self.uid = None
        self.models = None

    def connect(self):
        """Authenticates using the official XML-RPC common service."""
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                logger.info(f"✅ Odoo authenticated. UID: {self.uid}")
                # Initialize the object proxy for making data calls
                self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
                return True
            else:
                logger.error("❌ Odoo Auth Failed: Access Denied. Check if user has API access.")
                return False
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False

    def _call_kw(self, model, method, args, kwargs=None):
        """Standard method to call Odoo functions."""
        if not self.uid and not self.connect():
            raise Exception("Authentication failed.")
        
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs or {}
        )

    def create_vendor_bill(self, data):
        """Creates a vendor bill (account.move) in Odoo."""
        try:
            # 1. Get/Create Partner
            partner_id = self._get_or_create_partner(data.get('vendor_name'))
            
            # 2. Find Purchase Journal
            journal_ids = self._call_kw('account.journal', 'search', [[('type', '=', 'purchase')]], {"limit": 1})
            if not journal_ids:
                raise Exception("No purchase journal found in Odoo.")
            journal_id = journal_ids[0]

            # 3. Build Invoice Lines
            invoice_lines = []
            for line in data.get('invoice_lines', []):
                product_id = self._get_or_create_product(line.get('label'))
                invoice_lines.append((0, 0, {
                    'product_id': product_id,
                    'name': line.get('label'),
                    'quantity': float(line.get('quantity', 1)),
                    'price_unit': float(line.get('price_unit', 0)),
                }))

            # 4. Create the Move
            bill_vals = {
                'partner_id': partner_id,
                'journal_id': journal_id,
                'move_type': 'in_invoice', # Standard Odoo technical name for Vendor Bill
                'invoice_date': data.get('bill_date', datetime.now().strftime('%Y-%m-%d')),
                'invoice_line_ids': invoice_lines,
            }

            bill_id = self._call_kw('account.move', 'create', [bill_vals])
            logger.info(f"✅ Bill created successfully! ID: {bill_id}")
            return {'id': bill_id}
        except Exception as e:
            logger.error(f"❌ Failed to create bill: {e}")
            return None

    def _get_or_create_partner(self, name):
        search = self._call_kw('res.partner', 'search', [[('name', '=', name)]])
        if search: return search[0]
        return self._call_kw('res.partner', 'create', [{'name': name}])

    def _get_or_create_product(self, name):
        search = self._call_kw('product.product', 'search', [[('name', '=', name)]])
        if search: return search[0]
        return self._call_kw('product.product', 'create', [{'name': name, 'type': 'consu'}])