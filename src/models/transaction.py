"""
Transaction Model (Enhanced)

Standard structure for ALL bank transactions.
Includes detailed extraction fields from descriptions.
"""

from dataclasses import dataclass
from datetime import date, time
from typing import Optional
from enum import Enum


class TransactionType(Enum):
    """Types of transactions"""
    CREDIT = "credit"       # Money coming IN
    DEBIT = "debit"         # Money going OUT


class TransactionCategory(Enum):
    """Categories of transactions derived from description"""
    TRANSFER = "transfer"           # Bank transfers (BI-FAST, RTGS)
    CASH_DEPOSIT = "cash_deposit"   # ATM/CDM deposits
    CASH_WITHDRAWAL = "cash_withdrawal"
    BILL_PAYMENT = "bill_payment"   # Bills, top-ups
    CARD_CHARGE = "card_charge"     # Debit/credit card fees
    E_WALLET = "e_wallet"           # OVO, GoPay, ShopeePay
    CASHBACK = "cashback"           # Rewards
    INTEREST = "interest"           # Bank interest
    FEE = "fee"                     # Bank fees
    OTHER = "other"


@dataclass
class Transaction:
    """
    Standard transaction object that ALL parsers must produce.
    
    Enhanced with detailed fields extracted from descriptions.
    """
    
    # Core fields - every transaction must have these
    date: date
    description: str
    amount: float
    transaction_type: TransactionType
    
    # Balance after transaction
    balance: Optional[float] = None
    
    # Category & Channel
    category: TransactionCategory = TransactionCategory.OTHER
    channel: Optional[str] = None  # OCTOmobile, ATM/CDM, Debit Card, etc.
    
    # Transfer details
    counterparty: Optional[str] = None        # Recipient/sender name
    counterparty_bank: Optional[str] = None   # Bank name (BCA, BNI, etc.)
    counterparty_account: Optional[str] = None  # Account number
    
    # Reference & Time
    reference: Optional[str] = None   # Transaction reference number
    txn_time: Optional[str] = None    # Time of transaction (HH:MM:SS)
    
    # User notes/remarks
    notes: Optional[str] = None       # User's memo/description
    
    # Metadata
    source_file: str = ""
    source_bank: str = ""
    raw_text: str = ""  # Original text for debugging
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame/DB insert"""
        return {
            "date": self.date,
            "time": self.txn_time,
            "description": self.description,
            "amount": self.amount,
            "type": self.transaction_type.value,
            "category": self.category.value,
            "channel": self.channel,
            "balance": self.balance,
            "counterparty": self.counterparty,
            "counterparty_bank": self.counterparty_bank,
            "reference": self.reference,
            "notes": self.notes,
            "source_file": self.source_file,
        }


@dataclass 
class AccountInfo:
    """Account information extracted from statement header"""
    account_number: str = ""
    account_name: str = ""
    bank_name: str = ""
    currency: str = "IDR"
    statement_period: str = ""
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
