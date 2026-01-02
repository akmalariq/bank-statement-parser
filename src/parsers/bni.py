"""
BNI Parser (Wrapper)

Wraps the existing parsers/bni_parser.py to match the BaseBankParser interface.
"""

from typing import List, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path

from src.parsers.base import BaseBankParser
from src.models.transaction import (
    Transaction, AccountInfo, TransactionType, TransactionCategory
)
from src.parsers.bni_impl import extract_transactions_from_bni, extract_account_info_bni

class BNIParser(BaseBankParser):
    """
    Parser for BNI bank statements.
    Wraps existing logic from parsers/bni_parser.py
    """
    
    bank_name = "BNI"
    bank_code = "bni"
    
    def __init__(self, password: str = None):
        super().__init__()
        self.password = password
        self._account_info = None

    def extract_account_info(self, pdf_path: str) -> AccountInfo:
        """Extract account info from header."""
        data = extract_account_info_bni(pdf_path, self.password)
        
        return AccountInfo(
            account_number=data.get('No_Rekening', ''),
            account_name=data.get('Nama', ''),
            bank_name='BNI',
            currency=data.get('Mata_Uang', 'IDR'),
            statement_period=data.get('Periode', ''),
        )

    def extract_transactions(self, pdf_path: str) -> List[Transaction]:
        """Extract all transactions from PDF."""
        # Use existing parser which returns a DataFrame
        df = extract_transactions_from_bni(pdf_path, self.password)
        
        if df.empty:
            return []
            
        transactions = []
        
        for _, row in df.iterrows():
            # Parse date (Format: 01 Apr 2025)
            date_str = row['Tanggal']
            try:
                # Convert Indonesian month names if needed, though parser seems to output English short months?
                # The existing parser outputs "01 Apr 2025" based on my test run.
                txn_date = datetime.strptime(date_str, '%d %b %Y').date()
            except ValueError:
                # Fallback or skip
                continue
                
            # Parse amount and type
            debit = self._parse_amount(row.get('Debit', '0'))
            credit = self._parse_amount(row.get('Kredit', '0'))
            
            if debit > 0:
                amount = debit
                txn_type = TransactionType.DEBIT
            else:
                amount = credit
                txn_type = TransactionType.CREDIT
            
            # Map category
            # We can use the 'Tipe_Transaksi' or 'Klasifikasi' to help
            category = self._map_category(row)
            
            t = Transaction(
                date=txn_date,
                description=row.get('Deskripsi', ''),
                amount=amount,
                transaction_type=txn_type,
                balance=self._parse_amount(row.get('Saldo', '0')),
                category=category,
                channel=self._infer_channel(row),
                txn_time=row.get('Waktu'),
                
                # Extended fields from BNI parser
                counterparty=row.get('Penerima'),
                counterparty_bank=row.get('Bank_Tujuan'),
                counterparty_account=row.get('No_Akun_Tujuan'),
                notes=row.get('Keterangan'),
                
                source_bank=self.bank_name,
                raw_text=row.get('Deskripsi_Lengkap', '')
            )
            transactions.append(t)
            
        return transactions

    def _parse_amount(self, val) -> float:
        """Parse string amount to float."""
        if isinstance(val, (int, float)):
            return abs(float(val))
        if not val:
            return 0.0
        # Remove currency symbols, commas, etc
        clean = str(val).replace(',', '').replace('+', '').replace('-', '').strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def _map_category(self, row) -> TransactionCategory:
        """Map BNI transaction types to standard categories."""
        tipe = str(row.get('Tipe_Transaksi', '')).upper()
        desc = str(row.get('Deskripsi', '')).upper()
        
        if 'TRANSFER' in tipe or 'TRF' in desc:
            return TransactionCategory.TRANSFER
        if 'QRIS' in tipe or 'PEMBAYARAN' in tipe:
            return TransactionCategory.BILL_PAYMENT # OR OTHER?
        if 'SETOR TUNAI' in tipe or 'DEPOSIT' in tipe:
            return TransactionCategory.CASH_DEPOSIT
        if 'TARIK TUNAI' in tipe or 'WITHDRAWAL' in tipe:
            return TransactionCategory.CASH_WITHDRAWAL
        if 'BIAYA' in tipe or 'ADM' in desc:
            return TransactionCategory.FEE
        if 'BUNGA' in tipe or 'INTEREST' in desc:
            return TransactionCategory.INTEREST
        
        # Check e-wallets
        ewallet = row.get('E_Wallet', '')
        if ewallet:
            return TransactionCategory.E_WALLET
            
        return TransactionCategory.OTHER

    def _infer_channel(self, row) -> str:
        """Infer channel from transaction type."""
        tipe = str(row.get('Tipe_Transaksi', '')).upper()
        
        if 'MOBILE' in tipe or 'MBANK' in tipe:
            return 'Mobile Banking'
        if 'ATM' in tipe:
            return 'ATM'
        if 'QRIS' in tipe:
            return 'QRIS'
        if 'TELLER' in tipe:
            return 'Branch'
            
        return 'Unknown'
