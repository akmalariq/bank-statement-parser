"""
CIMB Parser (Enhanced v2)

Parses CIMB Niaga / OCTO Mobile bank statements with TYPE-SPECIFIC extraction.

Handles 12 transaction types:
- TR TO REMITT (transfers)
- OVERBOOKING (e-wallet)
- REMITTANCE CR (incoming)
- CDM CASH DEPOSIT
- ATM WITHDRAWAL
- BILL PAYMENT
- BILLPAYMENT TO CCARD
- CREDIT INTEREST
- WITHHOLDING TAX
- DEBIT CARD CHARGES
- CASH BACK
"""

import re
import pdfplumber
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.parsers.base import BaseBankParser
from src.models.transaction import (
    Transaction, AccountInfo, TransactionType, TransactionCategory
)


class CIMBParser(BaseBankParser):
    """
    Parser for CIMB Niaga / OCTO Mobile statements.
    
    Uses type-specific extraction for accurate field parsing.
    """
    
    bank_name = "CIMB"
    bank_code = "cimb"
    
    # Base patterns
    DATE_PATTERN = r'(\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})'
    AMOUNT_PATTERN = r'(-?[\d,]+\.\d{2})'
    TIME_PATTERN = r'(\d{2}:\d{2}:\d{2})'
    
    # Bank code mapping (expanded)
    BANK_CODES = {
        'CENAIDJA': 'BCA',
        'BRINIDJA': 'BRI',
        'BNINIDJA': 'BNI',
        'BMRIIDJA': 'Mandiri',
        'CABORELA': 'CIMB',
        'PERMIDJA': 'Permata',
        'BDKIIDJA': 'Bank DKI',
        'DKI': 'Bank DKI',  # Short form
        'SYABOREK': 'CIMB Syariah',
        'PDJBIDJA': 'BJB',  # Bank Jabar Banten
        'BABORELO': 'Bank Jatim',
        'BABORELB': 'Bank Jateng',
        'BTPNIDJA': 'BTPN',
        'MEGAIDJA': 'Bank Mega',
        'BABORELC': 'Bank Kalbar',
        'BSSNIDJA': 'BSI',  # Bank Syariah Indonesia
        'BDINIDJA': 'Danamon',
        'BBTNIDJA': 'BTN',
        'ABORELXD': 'Bank Aceh',
    }
    
    # E-wallet patterns
    EWALLET_PATTERNS = {
        'GOPAY': 'GoPay',
        'GP-': 'GoPay',
        'OVO': 'OVO',
        'DANA': 'DANA',
        'SHOPEE': 'ShopeePay',
        'LINKAJA': 'LinkAja',
    }
    
    def extract_account_info(self, pdf_path: str) -> AccountInfo:
        """Extract account info from CIMB statement header."""
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
        
        info = AccountInfo(bank_name=self.bank_name)
        
        match = re.search(r'No\.\s*Rekening\s*:\s*(\d+)', text)
        if match:
            info.account_number = match.group(1)
        
        match = re.search(r'Nama\s*:\s*(.+?)(?:\n|Mata)', text)
        if match:
            info.account_name = match.group(1).strip()
        
        match = re.search(r'Periode:\s*(.+?)(?:\n|$)', text)
        if match:
            info.statement_period = match.group(1).strip()
        
        return info
    
    def extract_transactions(self, pdf_path: str) -> List[Transaction]:
        """Extract all transactions from CIMB PDF."""
        transactions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
        
        blocks = self._split_into_blocks(full_text)
        
        for block in blocks:
            txn = self._parse_transaction_block(block)
            if txn:
                transactions.append(txn)
        
        return transactions
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """Split full text into transaction blocks."""
        lines = text.split('\n')
        blocks = []
        current_block = []
        
        STOP_MARKERS = [
            'Saldo Awal', 'Saldo Akhir', 'Total Kredit', 'Total Debit',
            'IMPORTANT', 'Page ', 'User ID, Password', 'bersifat rahasia',
        ]
        
        for line in lines:
            line_stripped = line.strip()
            
            if any(marker in line_stripped for marker in STOP_MARKERS):
                if current_block:
                    blocks.append('\n'.join(current_block))
                    current_block = []
                continue
            
            if re.match(self.DATE_PATTERN, line_stripped):
                if current_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
            elif current_block:
                current_block.append(line)
        
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _parse_transaction_block(self, block: str) -> Optional[Transaction]:
        """Parse a transaction block with type-specific extraction."""
        lines = block.strip().split('\n')
        if not lines:
            return None
        
        first_line = lines[0]
        
        # Extract date
        date_match = re.match(self.DATE_PATTERN, first_line)
        if not date_match:
            return None
        
        try:
            date_str = date_match.group(1)
            txn_date = datetime.strptime(date_str, '%d %b %Y').date()
        except ValueError:
            return None
        
        # Extract amounts
        amounts = re.findall(self.AMOUNT_PATTERN, first_line)
        if not amounts:
            return None
        
        amount_str = amounts[0].replace(',', '')
        amount = float(amount_str)
        txn_type = TransactionType.DEBIT if amount < 0 else TransactionType.CREDIT
        
        balance = None
        if len(amounts) > 1:
            balance = float(amounts[-1].replace(',', ''))
        
        # Build full description
        desc_part = first_line[date_match.end():].strip()
        for amt in amounts:
            desc_part = desc_part.replace(amt, '').strip()
        
        remaining_lines = [l.strip() for l in lines[1:] if l.strip()]
        full_text = desc_part + ' ' + ' '.join(remaining_lines)
        full_text = ' '.join(full_text.split())
        
        # Detect transaction type and parse accordingly
        parsed = self._parse_by_type(block, full_text)
        
        return Transaction(
            date=txn_date,
            description=parsed.get('description', full_text),
            amount=abs(amount),
            transaction_type=txn_type,
            balance=balance,
            category=parsed.get('category', TransactionCategory.OTHER),
            channel=parsed.get('channel'),
            txn_time=parsed.get('time'),
            reference=parsed.get('reference'),
            counterparty=parsed.get('counterparty'),
            counterparty_bank=parsed.get('counterparty_bank'),
            counterparty_account=parsed.get('counterparty_account'),
            notes=parsed.get('notes'),
            raw_text=block,
        )
    
    def _parse_by_type(self, block: str, text: str) -> Dict[str, Any]:
        """Route to type-specific parser based on transaction type."""
        text_upper = text.upper()
        
        if 'TR TO REMITT' in text_upper:
            return self._parse_transfer(block, text)
        elif 'REMITTANCE CR' in text_upper:
            return self._parse_incoming_transfer(block, text)
        elif 'OVERBOOKING' in text_upper and 'KWIK' in text_upper:
            return self._parse_ewallet_topup(block, text)
        elif 'OVERBOOKING' in text_upper:
            return self._parse_overbooking(block, text)
        elif 'CDM CASH DEPOSIT' in text_upper:
            return self._parse_cash_deposit(block, text)
        elif 'ATM WITHDRAWAL' in text_upper:
            return self._parse_atm_withdrawal(block, text)
        elif 'BILL PAYMENT' in text_upper or 'BILLPAYMENT' in text_upper:
            return self._parse_bill_payment(block, text)
        elif 'CREDIT INTEREST' in text_upper:
            return self._parse_interest(block, text)
        elif 'WITHHOLDING TAX' in text_upper:
            return self._parse_tax(block, text)
        elif 'DEBIT CARD CHARGE' in text_upper:
            return self._parse_card_charge(block, text)
        elif 'CASH BACK' in text_upper:
            return self._parse_cashback(block, text)
        else:
            return self._parse_generic(block, text)
    
    # ==================== TYPE-SPECIFIC PARSERS ====================
    
    def _parse_transfer(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse: TR TO REMITT OCTOmobile TO [NAME] [TIME] [NAME2] [REF] [BANK] [notes]
        """
        result = {
            'category': TransactionCategory.TRANSFER,
            'channel': 'OCTO Mobile',
            'description': text,
        }
        
        # Time
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Counterparty name (after "TO")
        name_match = re.search(r'TO\s+([A-Z][A-Z\s\.\-]+?)(?:\s+\d{2}:|\s+\d{9,})', block)
        if name_match:
            result['counterparty'] = name_match.group(1).strip()
        
        # Reference (12-digit number after time, not card number)
        refs = re.findall(r'(?<!\d)(\d{12})(?!\d)', block)
        for ref in refs:
            if not ref.startswith('5576') and not ref.startswith('5289'):
                result['reference'] = ref
                break
        
        # Bank code (no account number in CIMB statements, only reference)
        for code, bank in self.BANK_CODES.items():
            if code in block:
                result['counterparty_bank'] = bank
                break
        
        # Notes (lowercase text at end)
        lines = block.split('\n')
        last_line = lines[-1].strip() if lines else ""
        words = last_line.split()
        for i, word in enumerate(words):
            if word and len(word) > 2 and word[0].islower():
                result['notes'] = ' '.join(words[i:])
                break
        
        return result
    
    def _parse_incoming_transfer(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse: REMITTANCE CR - BIFAST [TXN_ID] [TIME] BFS FR [BANK] [SENDER] [notes]
        """
        result = {
            'category': TransactionCategory.TRANSFER,
            'channel': 'BI-FAST',
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Transaction ID (long alphanumeric after BIFAST)
        txn_match = re.search(r'BIFAST\s+(\w{20,})', block)
        if txn_match:
            result['reference'] = txn_match.group(1)
        
        # Sender bank (after "FR")
        for code, bank in self.BANK_CODES.items():
            if code in block:
                result['counterparty_bank'] = bank
                break
        
        # Sender name (after bank code, often uppercase)
        sender_match = re.search(r'(?:FR\s+\w+\s+)([A-Z][A-Z\s]+)(?:\s+\d|$)', block)
        if sender_match:
            result['counterparty'] = sender_match.group(1).strip()
        
        return result
    
    def _parse_overbooking(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse: OVERBOOKING OCTOmobile TRF TO - [NAME] [TIME] [ALIAS] [REF]
        """
        result = {
            'category': TransactionCategory.TRANSFER,
            'channel': 'OCTO Mobile',
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Name after "TO -" or "TO"
        name_match = re.search(r'TO\s*-?\s*([A-Z][A-Z\s]+?)(?:\s+\d{2}:)', block)
        if name_match:
            result['counterparty'] = name_match.group(1).strip()
        
        # Reference
        refs = re.findall(r'(?<!\d)(\d{12,16})(?!\d)', block)
        if refs:
            result['reference'] = refs[0]
        
        return result
    
    def _parse_ewallet_topup(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse: OVERBOOKING TO KWIK ... TRF TO [EWALLET] [PHONE] [TIME]
        """
        result = {
            'category': TransactionCategory.E_WALLET,
            'channel': 'E-Wallet',
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # E-wallet type
        for pattern, wallet in self.EWALLET_PATTERNS.items():
            if pattern in block.upper():
                result['counterparty'] = wallet
                break
        
        # Phone number
        phone_match = re.search(r'(08\d{9,11})', block)
        if phone_match:
            result['counterparty_account'] = phone_match.group(1)
        
        # Reference
        refs = re.findall(r'(?<!\d)(\d{12,16})(?!\d)', block)
        if refs:
            result['reference'] = refs[0]
        
        return result
    
    def _parse_cash_deposit(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse: CDM CASH DEPOSIT ATM/CDM [TIME] [TERMINAL] [CARD]
        """
        result = {
            'category': TransactionCategory.CASH_DEPOSIT,
            'channel': 'ATM/CDM',
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Terminal ID (4-digit number after time)
        terminal_match = re.search(r'\d{2}:\d{2}:\d{2}\s+(\d{4})\s', block)
        if terminal_match:
            result['reference'] = terminal_match.group(1)
        
        return result
    
    def _parse_atm_withdrawal(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse: ATM WITHDRAWAL ATM/CDM [TIME] [CARD]
        """
        result = {
            'category': TransactionCategory.CASH_WITHDRAWAL,
            'channel': 'ATM/CDM',
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        return result
    
    def _parse_bill_payment(self, block: str, text: str) -> Dict[str, Any]:
        """
        Parse bill payments including credit card payments and QR
        """
        result = {
            'category': TransactionCategory.BILL_PAYMENT,
            'channel': 'OCTO Mobile',
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Credit card number (masked or partial)
        card_match = re.search(r'(528\d{13})', block)
        if card_match:
            result['counterparty_account'] = card_match.group(1)
            result['counterparty'] = 'Credit Card'
        
        # QR merchant
        if 'QR' in block.upper():
            result['channel'] = 'QR Payment'
            merchant_match = re.search(r'QR Purchase\s+(\w+)', block)
            if merchant_match:
                result['counterparty'] = merchant_match.group(1)
        
        # Reference
        refs = re.findall(r'(?<!\d)(\d{12,16})(?!\d)', block)
        if refs:
            result['reference'] = refs[0]
        
        return result
    
    def _parse_interest(self, block: str, text: str) -> Dict[str, Any]:
        """Parse: CREDIT INTEREST [TIME]"""
        return {
            'category': TransactionCategory.INTEREST,
            'channel': 'System',
            'description': 'Monthly Interest',
            'time': re.search(self.TIME_PATTERN, block).group(1) if re.search(self.TIME_PATTERN, block) else None,
        }
    
    def _parse_tax(self, block: str, text: str) -> Dict[str, Any]:
        """Parse: WITHHOLDING TAX [TIME]"""
        return {
            'category': TransactionCategory.FEE,
            'channel': 'System',
            'description': 'Interest Withholding Tax',
            'time': re.search(self.TIME_PATTERN, block).group(1) if re.search(self.TIME_PATTERN, block) else None,
        }
    
    def _parse_card_charge(self, block: str, text: str) -> Dict[str, Any]:
        """Parse: DEBIT CARD CHARGES [TIME] [MASKED_CARD]"""
        result = {
            'category': TransactionCategory.CARD_CHARGE,
            'channel': 'Debit Card',
            'description': 'Monthly Card Fee',
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Masked card
        card_match = re.search(r'(\d{6}\*+\d{4})', block)
        if card_match:
            result['reference'] = card_match.group(1)
        
        return result
    
    def _parse_cashback(self, block: str, text: str) -> Dict[str, Any]:
        """Parse: CASH BACK [REF] [SOURCE] [TIME]"""
        result = {
            'category': TransactionCategory.CASHBACK,
            'channel': 'System',
            'description': 'Cashback Reward',
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Source (e.g., OVO, GoPay)
        for pattern, wallet in self.EWALLET_PATTERNS.items():
            if pattern in block.upper():
                result['counterparty'] = wallet
                break
        
        return result
    
    def _parse_generic(self, block: str, text: str) -> Dict[str, Any]:
        """Fallback parser for unknown transaction types."""
        result = {
            'category': TransactionCategory.OTHER,
            'description': text,
        }
        
        time_match = re.search(self.TIME_PATTERN, block)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Bank
        for code, bank in self.BANK_CODES.items():
            if code in block:
                result['counterparty_bank'] = bank
                break
        
        return result


# Quick test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cimb.py <pdf_path>")
        sys.exit(1)
    
    parser = CIMBParser()
    transactions = parser.parse(sys.argv[1])
    
    print(f"\nExtracted {len(transactions)} transactions:\n")
    for txn in transactions[:10]:
        print(f"{txn.date} {txn.txn_time or ''} | {txn.category.value}")
        print(f"  To: {txn.counterparty} @ {txn.counterparty_bank}")
        print(f"  Ref: {txn.reference} | Notes: {txn.notes}")
        print()
