"""
Main Parser Orchestrator

This is the main entry point that:
1. Classifies the PDF to identify the bank
2. Selects the appropriate parser
3. Extracts transactions
4. Returns clean data for storage

Usage:
    parser = Parser()
    transactions = parser.parse("statement.pdf")
    df = parser.to_dataframe()
"""

from pathlib import Path
from typing import List, Dict, Type, Optional
import pandas as pd

from src.classifier import BankClassifier
from src.parsers.base import BaseBankParser
from src.models.transaction import Transaction


class Parser:
    """
    Main parser that auto-selects the right bank parser.
    
    Flow:
        PDF → Classifier → Select Parser → Extract → Return Transactions
    
    Usage:
        parser = Parser()
        
        # Parse single file
        transactions = parser.parse("statement.pdf")
        
        # Parse multiple files
        all_transactions = parser.parse_directory("./statements/")
        
        # Export
        parser.export_csv("output.csv")
    """
    
    def __init__(self):
        self.classifier = BankClassifier()
        self.parsers: Dict[str, Type[BaseBankParser]] = {}
        self.transactions: List[Transaction] = []
        
        # Register available parsers
        self._register_parsers()
    
    def _register_parsers(self):
        """
        Register all available bank parsers.
        
        When you create a new parser, add it here!
        """
        # Import parsers here to avoid circular imports
        # Example:
        # from src.parsers.cimb import CIMBParser
        # self.parsers["cimb"] = CIMBParser
        
        # For now, we'll register them as they're created
        pass
    
    def register_parser(self, bank_code: str, parser_class: Type[BaseBankParser]):
        """
        Register a new parser.
        
        Args:
            bank_code: Code matching classifier output (e.g., "cimb")
            parser_class: The parser class (not instance)
        """
        self.parsers[bank_code] = parser_class
    
    def parse(self, pdf_path: str) -> List[Transaction]:
        """
        Parse a single PDF file.
        
        Automatically identifies the bank and uses the correct parser.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {pdf_path}")
        
        # Classify the PDF
        bank_code, confidence = self.classifier.identify_with_confidence(pdf_path)
        print(f"📄 {path.name}")
        print(f"   Bank: {bank_code.upper()} (confidence: {confidence:.0%})")
        
        # Get the parser
        if bank_code not in self.parsers:
            raise ValueError(f"No parser registered for bank: {bank_code}")
        
        parser_class = self.parsers[bank_code]
        parser = parser_class()
        
        # Parse and store
        transactions = parser.parse(pdf_path)
        self.transactions.extend(transactions)
        
        print(f"   Extracted: {len(transactions)} transactions")
        return transactions
    
    def parse_directory(self, directory: str) -> List[Transaction]:
        """
        Parse all PDFs in a directory.
        """
        path = Path(directory)
        if not path.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        pdf_files = list(path.glob("*.pdf")) + list(path.glob("*.PDF"))
        
        print(f"Found {len(pdf_files)} PDF files\n")
        
        for pdf_file in sorted(pdf_files):
            try:
                self.parse(str(pdf_file))
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print(f"\n✅ Total: {len(self.transactions)} transactions extracted")
        return self.transactions
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert all transactions to DataFrame."""
        if not self.transactions:
            return pd.DataFrame()
        return pd.DataFrame([t.to_dict() for t in self.transactions])
    
    def to_records(self) -> List[dict]:
        """Get transactions as list of dicts for DB insert."""
        return [t.to_dict() for t in self.transactions]
    
    def export_csv(self, output_path: str) -> str:
        """Export all transactions to CSV."""
        df = self.to_dataframe()
        df.to_csv(output_path, index=False)
        print(f"📁 Exported to: {output_path}")
        return output_path
    
    def clear(self):
        """Clear stored transactions."""
        self.transactions = []
    
    def get_supported_banks(self) -> List[str]:
        """List supported bank codes."""
        return list(self.parsers.keys())


# Convenience function
def parse(pdf_path: str) -> List[Transaction]:
    """Quick parse function."""
    parser = Parser()
    return parser.parse(pdf_path)
