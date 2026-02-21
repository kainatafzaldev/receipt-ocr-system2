"""
Odoo-Optimized Receipt Parser
Converts extracted receipt text to Odoo-compatible format
"""

import json
import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OdooReceiptParser:
    """
    Parser optimized for Odoo ERP integration
    """
    
    def __init__(self):
        # Odoo-specific field mappings
        self.odoo_fields = {
            'vendor_name': 'partner_id',
            'bill_date': 'invoice_date',
            'due_date': 'invoice_date_due',
            'bill_reference': 'name',
            'total_amount': 'amount_total',
            'subtotal': 'amount_untaxed',
            'tax_amount': 'amount_tax',
            'currency': 'currency_id'
        }
        
    def parse_for_odoo(self, structured_data: Dict) -> Dict:
        """
        Convert extracted data to Odoo-compatible format
        
        Args:
            structured_data: Data from OCR extraction
            
        Returns:
            Odoo-compatible invoice data
        """
        try:
            if not structured_data:
                return self._empty_odoo_response()
            
            # Basic invoice header
            odoo_invoice = {
                'move_type': 'in_invoice',  # Vendor Bill
                'partner_id': self._get_partner_id(structured_data),
                'invoice_date': structured_data.get('bill_date'),
                'invoice_date_due': structured_data.get('due_date'),
                'name': structured_data.get('bill_reference', ''),
                'ref': structured_data.get('bill_reference', ''),
                'currency_id': self._get_currency_id(structured_data.get('currency', 'USD')),
                'invoice_line_ids': [],
                'amount_untaxed': structured_data.get('subtotal', 0),
                'amount_tax': structured_data.get('tax_amount', 0),
                'amount_total': structured_data.get('total_amount', 0),
                'invoice_origin': 'OCR_Extraction',
                'state': 'draft'
            }
            
            # Add invoice lines
            invoice_lines = structured_data.get('items', []) or structured_data.get('invoice_lines', [])
            for idx, line in enumerate(invoice_lines):
                odoo_line = {
                    'sequence': idx + 10,
                    'name': line.get('description', line.get('label', '')),
                    'quantity': line.get('quantity', 1),
                    'price_unit': abs(float(line.get('price', line.get('price_unit', 0)))),
                    'discount': self._calculate_discount_percentage(line),
                    'price_subtotal': float(line.get('line_total', line.get('line_subtotal', 0))),
                    'tax_ids': self._get_tax_ids(structured_data)
                }
                
                odoo_invoice['invoice_line_ids'].append((0, 0, odoo_line))
            
            # Add shipping as separate line if exists
            shipping = structured_data.get('shipping_amount', 0)
            if shipping > 0:
                odoo_invoice['invoice_line_ids'].append((0, 0, {
                    'sequence': len(odoo_invoice['invoice_line_ids']) * 10 + 10,
                    'name': 'Shipping & Handling',
                    'quantity': 1,
                    'price_unit': shipping,
                    'price_subtotal': shipping,
                    'tax_ids': self._get_tax_ids(structured_data)
                }))
            
            # Add additional charges
            additional_charges = structured_data.get('additional_charges', [])
            for charge in additional_charges:
                odoo_invoice['invoice_line_ids'].append((0, 0, {
                    'sequence': len(odoo_invoice['invoice_line_ids']) * 10 + 10,
                    'name': charge.get('charge_name', 'Additional Charge'),
                    'quantity': 1,
                    'price_unit': charge.get('charge_amount', 0),
                    'price_subtotal': charge.get('charge_amount', 0),
                    'tax_ids': self._get_tax_ids(structured_data)
                }))
            
            # Add taxes information
            taxes = structured_data.get('taxes', [])
            if taxes:
                odoo_invoice['tax_info'] = taxes
                odoo_invoice['tax_rate'] = structured_data.get('tax_rate')
            
            return odoo_invoice
            
        except Exception as e:
            logger.error(f"Error parsing for Odoo: {str(e)}")
            return self._empty_odoo_response()
    
    def _get_partner_id(self, data: Dict) -> Optional[int]:
        """Get or create partner ID from vendor name"""
        vendor = data.get('vendor_name', '')
        if not vendor:
            return None
        
        # In real implementation, this would search Odoo database
        # For now, return a mock ID
        vendor_lower = vendor.lower()
        
        # Common vendor mappings (extend as needed)
        vendor_mappings = {
            'walmart': 1,
            'target': 2,
            'amazon': 3,
            'costco': 4,
            'starbucks': 5,
            'mcdonald': 6,
            'tesco': 7,
            'carrefour': 8,
            'shell': 9,
            'bp': 10,
            'albetos': 11  # Added your vendor
        }
        
        for key, vendor_id in vendor_mappings.items():
            if key in vendor_lower:
                return vendor_id
        
        # Return a default ID for unknown vendors
        return 99
    
    def _get_currency_id(self, currency_code: str) -> int:
        """Get Odoo currency ID from currency code"""
        currency_mapping = {
            'USD': 1,   # US Dollar
            'EUR': 2,   # Euro
            'GBP': 3,   # British Pound
            'PKR': 4,   # Pakistani Rupee
            'INR': 5,   # Indian Rupee
            'AED': 6,   # UAE Dirham
            'SAR': 7,   # Saudi Riyal
            'CAD': 8,   # Canadian Dollar
            'AUD': 9,   # Australian Dollar
        }
        return currency_mapping.get(currency_code.upper(), 1)  # Default to USD
    
    def _calculate_discount_percentage(self, line: Dict) -> float:
        """Calculate discount percentage from line data"""
        price_unit = float(line.get('price_unit', line.get('price', 0)))
        discount_amount = float(line.get('discount', 0))
        
        if price_unit > 0 and discount_amount > 0:
            return (discount_amount / price_unit) * 100
        
        return 0.0
    
    def _get_tax_ids(self, data: Dict) -> List:
        """Get Odoo tax IDs based on extracted tax data"""
        tax_rate = data.get('tax_rate')
        if not tax_rate:
            return []
        
        # Map tax rates to Odoo tax IDs (configure in your Odoo)
        tax_mappings = {
            5: [(6, 0, [1])],   # 5% tax
            8: [(6, 0, [2])],   # 8% tax
            10: [(6, 0, [3])],  # 10% tax
            15: [(6, 0, [4])],  # 15% tax
            17.5: [(6, 0, [5])], # 17.5% tax
            20: [(6, 0, [6])],  # 20% tax
        }
        
        return tax_mappings.get(tax_rate, [])
    
    def _empty_odoo_response(self) -> Dict:
        """Return empty Odoo-compatible response"""
        return {
            'move_type': 'in_invoice',
            'invoice_line_ids': [],
            'amount_untaxed': 0,
            'amount_tax': 0,
            'amount_total': 0,
            'state': 'draft'
        }
    
    def validate_extraction(self, structured_data: Dict) -> Dict:
        """
        Validate extracted data and calculate any missing values
        
        Args:
            structured_data: Extracted data
            
        Returns:
            Validated and completed data
        """
        validated = structured_data.copy()
        
        # Ensure required fields exist
        validated.setdefault('vendor_name', 'Unknown Vendor')
        validated.setdefault('bill_reference', '')
        validated.setdefault('bill_date', '')
        validated.setdefault('currency', 'USD')
        validated.setdefault('items', [])
        validated.setdefault('invoice_lines', [])
        validated.setdefault('taxes', [])
        validated.setdefault('additional_charges', [])
        
        # Handle both 'items' and 'invoice_lines' keys
        if 'items' in validated and not validated.get('invoice_lines'):
            validated['invoice_lines'] = validated['items']
        
        # Calculate subtotal from invoice lines if missing
        if 'subtotal' not in validated or not validated['subtotal']:
            lines = validated.get('invoice_lines', [])
            subtotal = sum(float(line.get('line_subtotal', line.get('price', 0))) for line in lines)
            validated['subtotal'] = subtotal
        
        # Calculate total if missing
        if 'total_amount' not in validated or not validated['total_amount']:
            subtotal = validated.get('subtotal', 0)
            tax_amount = validated.get('tax_amount', 0)
            shipping = validated.get('shipping_amount', 0)
            validated['total_amount'] = subtotal + tax_amount + shipping
        
        return validated
    
    def generate_odoo_xmlrpc_data(self, odoo_data: Dict) -> Dict:
        """
        Prepare data for Odoo XML-RPC API call
        
        Args:
            odoo_data: Odoo-compatible data
            
        Returns:
            Data ready for XML-RPC
        """
        xmlrpc_data = {
            'model': 'account.move',
            'method': 'create',
            'args': [odoo_data],
            'kwargs': {}
        }
        
        return xmlrpc_data


# Main function for compatibility
def parse_receipt_text(raw_text: str) -> Dict[str, Any]:
    """
    Main function to parse receipt text (for backward compatibility)
    
    Args:
        raw_text: Raw OCR text
        
    Returns:
        Parsed receipt data
    """
    parser = OdooReceiptParser()
    
    # Try to parse as JSON first (from structured extraction)
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and 'vendor_name' in data:
            # This is already structured data
            return parser.validate_extraction(data)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Fallback to basic text parsing
    return _parse_basic_receipt(raw_text)


def _parse_basic_receipt(raw_text: str) -> Dict[str, Any]:
    """Basic fallback parser for raw text"""
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    result = {
        'vendor_name': _extract_vendor(lines),
        'bill_date': _extract_date(lines),
        'invoice_lines': _extract_basic_items(lines),
        'items': _extract_basic_items(lines),  # Added for compatibility
        'total_amount': _extract_total(lines),
        'subtotal': _extract_subtotal(lines),
        'tax_amount': _extract_tax(lines),
        'currency': 'USD'
    }
    
    return result


def _extract_vendor(lines):
    """Basic vendor extraction"""
    if lines:
        return lines[0]
    return "Unknown"


def _extract_date(lines):
    """Basic date extraction"""
    for line in lines:
        match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
        if match:
            return match.group(1)
    return ""


def _extract_basic_items(lines):
    """Basic item extraction"""
    items = []
    for line in lines:
        # Simple pattern for "Qty Item $Price"
        match = re.search(r'(\d+)\s+(.+?)\s+[\$]?\s*(\d+\.\d{2})', line)
        if match:
            items.append({
                'label': match.group(2).strip(),
                'description': match.group(2).strip(),
                'quantity': int(match.group(1)),
                'price_unit': float(match.group(3)),
                'price': float(match.group(3)),
                'line_subtotal': float(match.group(3)) * int(match.group(1)),
                'line_total': float(match.group(3)) * int(match.group(1))
            })
    return items


def _extract_total(lines):
    """Basic total extraction"""
    for line in lines:
        if 'TOTAL' in line.upper():
            match = re.search(r'[\$]?\s*(\d+\.\d{2})', line)
            if match:
                return float(match.group(1))
    return 0


def _extract_subtotal(lines):
    """Basic subtotal extraction"""
    for line in lines:
        if 'SUBTOTAL' in line.upper():
            match = re.search(r'[\$]?\s*(\d+\.\d{2})', line)
            if match:
                return float(match.group(1))
    return 0


def _extract_tax(lines):
    """Basic tax extraction"""
    for line in lines:
        if 'TAX' in line.upper():
            match = re.search(r'[\$]?\s*(\d+\.\d{2})', line)
            if match:
                return float(match.group(1))
    return 0


# Test function
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 ODOO RECEIPT PARSER TEST")
    print("=" * 70)
    
    # Test with sample receipt data from your actual receipt
    test_data = {
        "vendor_name": "ALBETOS",
        "bill_reference": "01029",
        "currency": "USD",
        "items": [
            {"description": "ASADA TACO", "quantity": 3, "price": 8.10, "line_total": 8.10},
            {"description": "ATM CHARGE", "quantity": 1, "price": 0.75, "line_total": 0.75}
        ],
        "subtotal": 8.85,
        "tax_amount": 0.73,
        "total_amount": 9.58
    }
    
    parser = OdooReceiptParser()
    
    print("\n1. Validating extraction...")
    validated = parser.validate_extraction(test_data)
    print(f"   ✅ Validated data: ${validated.get('total_amount', 0):.2f}")
    
    print("\n2. Converting to Odoo format...")
    odoo_format = parser.parse_for_odoo(validated)
    print(f"   ✅ Odoo invoice created with {len(odoo_format.get('invoice_line_ids', []))} lines")
    print(f"   ✅ Total amount: ${odoo_format.get('amount_total', 0):.2f}")
    
    print("\n3. Sample Odoo invoice data:")
    print(json.dumps(odoo_format, indent=2))
    
    print("\n" + "=" * 70)
    print("✅ Parser test complete!")
    print("=" * 70)