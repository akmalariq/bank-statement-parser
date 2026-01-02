"""
Bank Classifier

Identifies which bank a PDF statement is from by analyzing the content.
This allows automatic parser selection.
"""

import pdfplumber
from pathlib import Path
from typing import Optional, Tuple


class BankClassifier:
    """
    Classifies PDF bank statements by analyzing text patterns.
    
    Usage:
        classifier = BankClassifier()
        bank_code = classifier.identify("statement.pdf")
        # Returns: "cimb", "bni", "bca", "mandiri", "bri", or "unknown"
    """
    
    # Bank identification patterns
    # Format: (bank_code, list of patterns to match)
    BANK_PATTERNS = {
        "cimb": [
            "CIMB NIAGA",
            "OCTO",
            "PT BANK CIMB NIAGA",
        ],
        "bni": [
            "PT BANK NEGARA INDONESIA",
            "BNI",
            "MUTASI REKENING",
        ],
        "bca": [
            "PT BANK CENTRAL ASIA",
            "BCA",
            "TAHAPAN",
        ],
        "mandiri": [
            "PT BANK MANDIRI",
            "MANDIRI",
            "LIVIN",
        ],
        "bri": [
            "PT BANK RAKYAT INDONESIA",
            "BRI",
            "BRITAMA",
        ],
    }
    
    def identify(self, pdf_path: str) -> str:
        """
        Identify the bank from a PDF statement.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Bank code (e.g., "cimb", "bni") or "unknown"
        """
        text = self._extract_first_page(pdf_path)
        
        if not text:
            return "unknown"
        
        text_upper = text.upper()
        
        # Check each bank's patterns
        for bank_code, patterns in self.BANK_PATTERNS.items():
            for pattern in patterns:
                if pattern.upper() in text_upper:
                    return bank_code
        
        return "unknown"
    
    def identify_with_confidence(self, pdf_path: str) -> Tuple[str, float]:
        """
        Identify bank with confidence score.
        
        Returns:
            Tuple of (bank_code, confidence 0.0-1.0)
        """
        text = self._extract_first_page(pdf_path)
        
        if not text:
            # Fallback: Check filename
            filename = Path(pdf_path).name.upper()
            
            if 'BNI' in filename:
                return ('bni', 0.8)
            elif 'CIMB' in filename or 'OCTO' in filename:
                return ('cimb', 0.8)
            elif 'BCA' in filename:
                return ('bca', 0.8)
            elif 'MANDIRI' in filename:
                return ('mandiri', 0.8)
                
            return ("unknown", 0.0)
        
        text_upper = text.upper()
        
        # Count matches for each bank
        scores = {}
        for bank_code, patterns in self.BANK_PATTERNS.items():
            matches = sum(1 for p in patterns if p.upper() in text_upper)
            if matches > 0:
                scores[bank_code] = matches / len(patterns)
        
        if not scores:
            return ("unknown", 0.0)
        
        # Return highest scoring bank
        best_bank = max(scores, key=scores.get)
        return (best_bank, scores[best_bank])
    
    def _extract_first_page(self, pdf_path: str) -> Optional[str]:
        """Extract text from the first page of a PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    return pdf.pages[0].extract_text() or ""
        except Exception:
             # Try BNI default password
             try:
                 with pdfplumber.open(pdf_path, password='02121979') as pdf:
                     if pdf.pages:
                         return pdf.pages[0].extract_text() or ""
             except Exception:
                 pass
        return None
    
    def get_supported_banks(self) -> list:
        """Return list of supported bank codes."""
        return list(self.BANK_PATTERNS.keys())
