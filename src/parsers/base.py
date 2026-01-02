"""
Abstract Base Parser (Simplified)

Blueprint for all bank parsers - no audit logic.
Focus: Extract → Store → Summarize later
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
import pandas as pd

from src.models.transaction import Transaction, AccountInfo, TransactionType


class BaseBankParser(ABC):
    """
    Abstract base class for all bank statement parsers.
    
    Each bank has a different PDF format, but they all:
    1. Extract transactions into the same Transaction format
    2. Can export to DataFrame/Excel/CSV
    
    To add a new bank:
        class BCAParser(BaseBankParser):
            bank_name = "BCA"
            
            def extract_transactions(self, pdf_path):
                # Your BCA-specific logic
                return [Transaction(...), ...]
    """
    
    # Override these in child classes
    bank_name: str = "Unknown"
    bank_code: str = "unknown"  # Used by classifier
    
    def __init__(self):
        self.transactions: List[Transaction] = []
        self.account_info: Optional[AccountInfo] = None
    
    # ==================== ABSTRACT METHODS ====================
    # Child classes MUST implement these
    
    @abstractmethod
    def extract_transactions(self, pdf_path: str) -> List[Transaction]:
        """
        Extract transactions from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of Transaction objects
        """
        pass
    
    @abstractmethod
    def extract_account_info(self, pdf_path: str) -> AccountInfo:
        """
        Extract account information from the PDF header.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            AccountInfo object
        """
        pass
    
    # ==================== SHARED METHODS ====================
    
    def parse(self, pdf_path: str) -> List[Transaction]:
        """
        Main entry point - parse a PDF and return transactions.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Extract data
        self.account_info = self.extract_account_info(pdf_path)
        self.transactions = self.extract_transactions(pdf_path)
        
        # Add metadata to all transactions
        for txn in self.transactions:
            txn.source_file = path.name
            txn.source_bank = self.bank_name
        
        return self.transactions
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert transactions to pandas DataFrame for DB insert."""
        if not self.transactions:
            return pd.DataFrame()
        
        data = [txn.to_dict() for txn in self.transactions]
        return pd.DataFrame(data)
    
    def to_records(self) -> List[dict]:
        """Convert to list of dicts for easy DB insert."""
        return [txn.to_dict() for txn in self.transactions]
    
    def export_csv(self, output_path: str) -> str:
        """Export transactions to CSV."""
        df = self.to_dataframe()
        df.to_csv(output_path, index=False)
        return output_path
    
    def export_excel(self, output_path: str) -> str:
        """Export transactions to Excel."""
        df = self.to_dataframe()
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Summary
            if self.account_info:
                summary = pd.DataFrame([{
                    'Bank': self.bank_name,
                    'Account': self.account_info.account_number,
                    'Period': self.account_info.statement_period,
                    'Opening Balance': self.account_info.opening_balance,
                    'Closing Balance': self.account_info.closing_balance,
                    'Total Transactions': len(df),
                }])
                summary.to_excel(writer, sheet_name='Summary', index=False)
        
        return output_path
    
    def __repr__(self):
        return f"{self.__class__.__name__}(bank={self.bank_name}, txns={len(self.transactions)})"
