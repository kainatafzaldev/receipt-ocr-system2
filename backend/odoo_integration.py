# odoo_integration.py - 100% DYNAMIC - NO HARDCODING
import xmlrpc.client
import logging
from datetime import datetime, timedelta
import os
import traceback
import re
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OdooConnector:
    def __init__(self):
        self.url = os.getenv('ODOO_URL', 'http://localhost:8069')
        self.db = os.getenv('ODOO_DB', 'odoo')
        self.username = os.getenv('ODOO_USERNAME', 'admin')
        self.password = os.getenv('ODOO_PASSWORD', 'admin')
        
        self.uid = None
        self.models = None
        self.connected = False
        
        # Dynamic caches
        self.account_cache = {}
        self.journal_cache = {}
        self.currency_cache = {}
        self.tax_cache = {}
        self.partner_cache = {}
        
    def connect(self):
        """Connect to Odoo dynamically"""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                self.connected = True
                logger.info(f"✅ Connected to Odoo as {self.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False
    
    def _get_any_account(self, account_type=None):
        """DYNAMIC: Get ANY account from Odoo"""
        cache_key = account_type or 'any'
        if cache_key in self.account_cache:
            return self.account_cache[cache_key]
        
        try:
            domain = []
            if account_type:
                domain.append(['account_type', '=', account_type])
            
            account_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.account', 'search',
                [domain], {'limit': 1}
            )
            
            if account_ids:
                self.account_cache[cache_key] = account_ids[0]
                return account_ids[0]
            
            # Get any account
            account_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.account', 'search',
                [[]], {'limit': 1}
            )
            
            if account_ids:
                self.account_cache[cache_key] = account_ids[0]
                return account_ids[0]
            
            return False
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return False
    
    def _get_any_journal(self, journal_type=None):
        """DYNAMIC: Get ANY journal from Odoo"""
        cache_key = journal_type or 'any'
        if cache_key in self.journal_cache:
            return self.journal_cache[cache_key]
        
        try:
            domain = []
            if journal_type:
                domain.append(['type', '=', journal_type])
            
            journal_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.journal', 'search',
                [domain], {'limit': 1}
            )
            
            if journal_ids:
                self.journal_cache[cache_key] = journal_ids[0]
                return journal_ids[0]
            
            # Get any journal
            journal_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.journal', 'search',
                [[]], {'limit': 1}
            )
            
            if journal_ids:
                self.journal_cache[cache_key] = journal_ids[0]
                return journal_ids[0]
            
            return False
        except Exception as e:
            logger.error(f"Error getting journal: {e}")
            return False
    
    def _get_currency_id(self, currency_code):
        """DYNAMIC: Get ANY currency ID"""
        if not currency_code:
            return False
        
        currency_code = currency_code.upper()
        if currency_code in self.currency_cache:
            return self.currency_cache[currency_code]
        
        try:
            currency_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.currency', 'search',
                [[['name', '=', currency_code]]], {'limit': 1}
            )
            
            if currency_ids:
                self.currency_cache[currency_code] = currency_ids[0]
                return currency_ids[0]
            
            # Get company currency
            company = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.company', 'search_read',
                [[]], {'fields': ['currency_id'], 'limit': 1}
            )
            
            if company and company[0].get('currency_id'):
                currency_id = company[0]['currency_id'][0]
                self.currency_cache[currency_code] = currency_id
                logger.warning(f"⚠️ Currency {currency_code} not found, using company currency")
                return currency_id
            
            return False
        except Exception as e:
            logger.error(f"Error getting currency: {e}")
            return False
    
    def search_vendor(self, vendor_name):
        """DYNAMIC: Search ANY vendor"""
        try:
            partner_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'search',
                [[
                    ['name', 'ilike', vendor_name],
                    ['supplier_rank', '>', 0]
                ]]
            )
            
            if partner_ids:
                partners = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'res.partner', 'read',
                    [partner_ids[0]], {'fields': ['id', 'name']}
                )
                return partners[0] if partners else None
            return None
        except Exception as e:
            logger.error(f"Error searching vendor: {e}")
            return None
    
    def create_vendor(self, vendor_name):
        """Create ANY vendor"""
        try:
            partner_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'create',
                [{
                    'name': vendor_name,
                    'supplier_rank': 1,
                    'customer_rank': 0,
                }]
            )
            logger.info(f"✅ Created vendor: {vendor_name}")
            return partner_id
        except Exception as e:
            logger.error(f"Error creating vendor: {e}")
            return None
    
    def create_vendor_bill(self, bill_data):
        """Create vendor bill with EXACT receipt tax amount (appears once)"""
        try:
            if not self.connect():
                return None
            
            logger.info("=" * 60)
            logger.info("📄 CREATING VENDOR BILL - TAX APPEARS ONCE")
            logger.info("=" * 60)
            
            # ============ 1. VENDOR ============
            vendor_name = bill_data.get('vendor_name')
            if not vendor_name or vendor_name == 'Unknown Vendor':
                # Try to get from bill_data or use default
                vendor_name = "Unknown Vendor"
                logger.warning(f"⚠️ Using default vendor: {vendor_name}")
            
            vendor = self.search_vendor(vendor_name)
            vendor_id = vendor['id'] if vendor else self.create_vendor(vendor_name)
            if not vendor_id:
                logger.error("❌ Could not get/create vendor")
                return None
            
            # ============ 2. DATES ============
            bill_date = bill_data.get('bill_date') or datetime.now().strftime('%Y-%m-%d')
            due_date = bill_data.get('due_date') or bill_date
            
            # ============ 3. CURRENCY ============
            currency_code = bill_data.get('currency', 'USD')
            currency_id = self._get_currency_id(currency_code)
            
            # ============ 4. JOURNAL & ACCOUNT ============
            journal_id = self._get_any_journal('purchase')
            account_id = self._get_any_account('expense')
            tax_account_id = self._get_any_account('tax') or account_id
            
            # ============ 5. GET EXACT RECEIPT TAX AMOUNT ============
            receipt_tax_amount = float(bill_data.get('tax_amount', 0))
            receipt_tax_text = bill_data.get('tax_text', '')
            subtotal = float(bill_data.get('subtotal', 0))
            total = float(bill_data.get('total_amount', 0))
            
            logger.info(f"💰 RECEIPT TAX AMOUNT: {receipt_tax_amount} {currency_code} (will appear ONCE)")
            
            # ============ 6. CREATE INVOICE LINES (NO TAX ON LINES) ============
            invoice_lines = []
            items = bill_data.get('invoice_lines', [])
            
            logger.info(f"📦 Items ({len(items)}):")
            
            for idx, item in enumerate(items):
                label = item.get('label', 'Item')
                quantity = float(item.get('quantity', 1))
                price_unit = float(item.get('price_unit', 0))
                
                logger.info(f"   {idx+1}. {label[:30]}... | Qty: {quantity} | Price: {price_unit:.2f}")
                
                # NO tax on individual lines
                line_vals = {
                    'name': label[:100],
                    'account_id': account_id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'product_id': False,
                    'sequence': (idx + 1) * 10,
                }
                invoice_lines.append((0, 0, line_vals))
            
            # ============ 7. CREATE SEPARATE TAX LINE (ONLY ONCE) ============
            if receipt_tax_amount > 0:
                tax_line_name = "Tax"
                if receipt_tax_text:
                    # Clean up tax text for display
                    clean_tax_text = receipt_tax_text.replace('$', '').strip()
                    tax_line_name = f"Tax ({clean_tax_text[:50]})"
                
                tax_line = (0, 0, {
                    'name': tax_line_name[:100],
                    'account_id': tax_account_id,
                    'quantity': 1,
                    'price_unit': receipt_tax_amount,
                    'product_id': False,
                    'sequence': len(invoice_lines) * 10 + 10,
                })
                invoice_lines.append(tax_line)
                logger.info(f"   ✅ Added SINGLE tax line: {receipt_tax_amount} {currency_code}")
            
            # ============ 8. CREATE BILL ============
            bill_reference = bill_data.get('bill_reference', '') or f"BILL/{datetime.now().strftime('%Y%m%d/%H%M%S')}"
            
            # Create narration with receipt info
            narration = f"Imported from receipt via OCR on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            if receipt_tax_text:
                narration += f"Original tax line: {receipt_tax_text}"
            
            bill_vals = {
                'move_type': 'in_invoice',
                'partner_id': vendor_id,
                'journal_id': journal_id,
                'invoice_date': bill_date,
                'date': bill_date,
                'invoice_date_due': due_date,
                'ref': bill_reference,
                'payment_reference': bill_reference,
                'currency_id': currency_id,
                'invoice_line_ids': invoice_lines,
                'narration': narration,
                'state': 'draft',
            }
            
            logger.info(f"📝 Creating bill in Odoo...")
            
            bill_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'create',
                [bill_vals]
            )
            
            # ============ 9. VERIFY AND RETURN ============
            bill_info = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'read',
                [bill_id], {'fields': ['name', 'amount_untaxed', 'amount_tax', 'amount_total']}
            )
            
            if bill_info:
                bill_number = bill_info[0]['name']
                amount_untaxed = bill_info[0]['amount_untaxed']
                amount_tax = bill_info[0]['amount_tax']
                amount_total = bill_info[0]['amount_total']
                
                logger.info(f"✅ BILL CREATED: {bill_number}")
                logger.info(f"   Untaxed: {amount_untaxed:.2f} {currency_code}")
                logger.info(f"   Tax: {amount_tax:.2f} {currency_code}")
                logger.info(f"   Total: {amount_total:.2f} {currency_code}")
                
                # Verify tax matches receipt
                if abs(amount_tax - receipt_tax_amount) < 0.01:
                    logger.info(f"✅ Tax matches receipt exactly!")
                else:
                    logger.warning(f"⚠️ Tax differs from receipt by {abs(amount_tax - receipt_tax_amount):.2f}")
            else:
                bill_number = 'N/A'
                amount_total = total
                amount_tax = receipt_tax_amount
            
            logger.info(f"🔗 View: {self.url}/web#id={bill_id}&model=account.move")
            
            return {
                'id': bill_id,
                'number': bill_number,
                'vendor': vendor_name,
                'amount': amount_total,
                'tax_amount': amount_tax,
                'receipt_tax': receipt_tax_amount,
                'url': f"{self.url}/web#id={bill_id}&model=account.move"
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating vendor bill: {e}")
            traceback.print_exc()
            return None