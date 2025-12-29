"""
PDF to Excel Converter for CASA Bank Statements (CIMB/OCTO)
Extracts ALL transaction data from multiple bank statement PDFs into a single Excel file
Includes Private/Company fund classification for audit purposes
"""

import pdfplumber
import pandas as pd
from pathlib import Path
import re
from datetime import datetime


# Keywords for classification
COMPANY_KEYWORDS = [
    'atk', 'kantor', 'office', 'printer', 'komputer', 'laptop',
    'kamus', 'buku', 'cetak', 'plakat', 'spanduk', 'banner', 'percetakan',
    'grafika', 'advertising', 'kbbi', 'peribahasa', 'idiom',
    'jaspro', 'jasapro', 'jasa profesional', 'konsultan', 'notaris',
    'dpr', 'badan bahasa', 'korpri', 'juknis', 'kuliah umum', 'kul umum',
    'hari guru', 'hut', 'seminar', 'workshop',
    'garuda', 'tiket', 'palu', 'aceh', 'jateng', 'flight',
    'apar', 'cv ', 'pt ', 'ud ', 'toko', 'supplier',
    'honor', 'gaji', 'pulang', 'perjalanan', 'dinas',
    'signage', 'kebersihan', 'catering', 'katering',
]

PRIVATE_KEYWORDS = [
    'traveloka', 'agoda', 'hotel', 'liburan', 'vacation',
    'malaysia', 'pribadi', 'personal', 'uh ',
    'netflix', 'spotify', 'youtube', 'game',
    'makan', 'resto', 'cafe', 'belanja',
    'jajan', 'jemputan', 'nisan', 'rumput',
]

COMPANY_RECIPIENTS = [
    'cv ', 'pt ', 'ud ', 'toko', 'grafika', 'advertising',
    'premier', 'perkasa', 'indonesia tbk', 'astra',
]

PRIVATE_RECIPIENTS = [
    'traveloka', 'agoda', 'shopee', 'tokopedia', 'lazada',
    'gopay', 'ovo', 'dana',
]

# Bank code to name mapping
BANK_CODE_MAP = {
    'BNINIDJA': 'BNI',
    'CENAIDJA': 'BCA',
    'BRINIDJA': 'BRI',
    'BMRIIDJA': 'Mandiri',
    'PDJBIDJA': 'BJB',
    'JSABIDJ1': 'Jasa Arta',
    'SYABORJJ': 'Bank Syariah',
    'PERMIDJX': 'Permata',
    'BCA': 'BCA',
    'BNI': 'BNI',
    'BRI': 'BRI',
    'MANDIRI': 'Mandiri',
    'PERMATA': 'Permata',
    'CIMB': 'CIMB',
}

# E-wallet patterns (order matters - check longer patterns first)
EWALLET_PATTERNS = {
    'SHOPEEPAY': 'ShopeePay',
    'SHOPEE PAY': 'ShopeePay',
    'TOP UP SHOPEE': 'ShopeePay',
    'SHOPEE': 'ShopeePay',
    'GOPAY': 'GoPay',
    'GO-PAY': 'GoPay',
    'OVO': 'OVO',
    'DANA': 'DANA',
    'LINKAJA': 'LinkAja',
    'LINK AJA': 'LinkAja',
    'FLIP': 'Flip',
}


def classify_transaction(row: dict) -> str:
    """Classify a transaction as 'Company', 'Private', or 'Review'."""
    keterangan = str(row.get('Keterangan', '')).lower()
    penerima = str(row.get('Penerima', '')).lower()
    tipe = str(row.get('Tipe_Transaksi', '')).lower()
    
    company_score = 0
    private_score = 0
    
    for keyword in COMPANY_KEYWORDS:
        if keyword in keterangan:
            company_score += 2
    
    for keyword in PRIVATE_KEYWORDS:
        if keyword in keterangan:
            private_score += 2
    
    for keyword in COMPANY_RECIPIENTS:
        if keyword in penerima:
            company_score += 1
    
    for keyword in PRIVATE_RECIPIENTS:
        if keyword in penerima:
            private_score += 1
    
    if 'fee charge' in tipe or 'debit card charges' in tipe:
        company_score += 0.5
    
    if 'bifast' in tipe and not any(k in keterangan for k in COMPANY_KEYWORDS):
        private_score += 0.5
    
    if 'overbooking' in tipe and 'traveloka' in penerima.lower():
        private_score += 2
    
    if company_score > private_score and company_score >= 1:
        return 'Company'
    elif private_score > company_score and private_score >= 1:
        return 'Private'
    else:
        return 'Review'


def audit_transaction(row: dict) -> tuple:
    """
    Audit a transaction for suspicious patterns.
    Returns: (Audit_Flag, Audit_Notes)
    
    Audit_Flag values:
    - OK: Clearly legitimate company expense
    - SUSPICIOUS: Likely personal expense, needs investigation
    - NEEDS_JUSTIFICATION: Large amount or unclear purpose
    """
    keterangan = str(row.get('Keterangan', '')).lower()
    penerima = str(row.get('Penerima', '')).lower()
    tipe = str(row.get('Tipe_Transaksi', '')).lower()
    ewallet = str(row.get('E_Wallet', '')).lower()
    debit_str = str(row.get('Debit', ''))
    
    # Parse debit amount
    try:
        debit = abs(float(debit_str.replace(',', '').replace('-', '') or 0))
    except:
        debit = 0
    
    notes = []
    flag = 'OK'
    
    # === SUSPICIOUS PATTERNS (Personal Expenses) ===
    
    # 1. E-wallet top-ups to personal account
    if ewallet and ('indah' in penerima or 'rosalia' in penerima or 'desya' in penerima):
        flag = 'SUSPICIOUS'
        notes.append(f'E-wallet ({ewallet}) top-up to personal account')
    
    # 2. E-wallet without clear business purpose
    if ewallet and not any(k in keterangan for k in ['kantor', 'office', 'meeting', 'client']):
        if flag != 'SUSPICIOUS':
            flag = 'SUSPICIOUS'
        notes.append(f'E-wallet ({ewallet}) without business justification')
    
    # 3. "Jajan" (snacks) - personal expense
    if 'jajan' in keterangan:
        flag = 'SUSPICIOUS'
        notes.append('Personal snacks/meals (jajan)')
    
    # 4. Child-related expenses (jemputan = school pickup)
    if 'jemputan' in keterangan or 'deniza' in keterangan:
        flag = 'SUSPICIOUS'
        notes.append('Child-related expense (jemputan/deniza)')
    
    # 5. Personal items (nisan = gravestone, porselen/porsaina)
    if 'nisan' in keterangan or 'porsaina' in keterangan or 'porselen' in keterangan:
        flag = 'SUSPICIOUS'
        notes.append('Personal item purchase')
    
    # 6. TRAVELOKA without keterangan (could be personal travel)
    if 'traveloka' in tipe.lower() or 'traveloka' in penerima:
        if not keterangan or keterangan == 'nan' or len(keterangan) < 3:
            flag = 'SUSPICIOUS'
            notes.append('TRAVELOKA payment without business justification')
        elif any(k in keterangan for k in ['pribadi', 'liburan', 'vacation']):
            flag = 'SUSPICIOUS'
            notes.append('TRAVELOKA for personal trip')
    
    # 7. Personal transfer keywords
    if 'malaysia' in keterangan and 'dinas' not in keterangan:
        flag = 'SUSPICIOUS'
        notes.append('Transfer to Malaysia (possibly personal)')
    
    # === OK PATTERNS (Clear Company Expenses) ===
    
    # Business travel with context
    business_travel_keywords = ['perjadin', 'skbd', 'manca', 'dinas', 'pusbang', 'pusbanglin', 
                                'narsum', 'seminar', 'workshop', 'rapat', 'meeting']
    if any(k in keterangan for k in business_travel_keywords):
        flag = 'OK'
        notes = ['Business travel/activity']
    
    # Office supplies
    office_keywords = ['atk', 'kamus', 'kbbi', 'spanduk', 'plakat', 'banner', 'cetak', 
                      'percetakan', 'signage', 'alat kebersihan', 'tong sampah']
    if any(k in keterangan for k in office_keywords):
        flag = 'OK'
        notes = ['Office supplies/equipment']
    
    # Professional services
    if any(k in keterangan for k in ['jaspro', 'honor', 'konsultan', 'notaris']):
        flag = 'OK'
        notes = ['Professional services']
    
    # Government/institutional payments
    if any(k in keterangan for k in ['dpr', 'badan bahasa', 'korpri', 'juknis']):
        flag = 'OK'
        notes = ['Government/institutional payment']
    
    # Business catering with context
    if any(k in keterangan for k in ['katering', 'catering', 'nasi box']) and debit > 500000:
        flag = 'OK'
        notes = ['Business catering']
    
    # Flights/hotels with employee names
    if any(k in keterangan for k in ['tiket', 'hotel', 'pesawat', 'flight']):
        # Check if it has business context
        if any(k in keterangan for k in ['dinas', 'skbd', 'pusbang', 'narsum', 'manca', 
                                          'papua', 'bengkulu', 'medan', 'bali', 'jogja', 
                                          'surabaya', 'aceh', 'riau', 'jambi']):
            flag = 'OK'
            notes = ['Business travel (flight/hotel)']
        else:
            if flag != 'SUSPICIOUS':
                flag = 'NEEDS_JUSTIFICATION'
            notes.append('Flight/hotel - verify business purpose')
    
    # === NEEDS JUSTIFICATION ===
    
    # Large transfers without keterangan
    if debit > 5000000 and (not keterangan or keterangan == 'nan' or len(keterangan) < 3):
        if flag != 'SUSPICIOUS':
            flag = 'NEEDS_JUSTIFICATION'
        notes.append(f'Large transfer (Rp {debit:,.0f}) without description')
    
    # Credit card payments without context
    if 'billpayment' in tipe or 'ccard' in tipe:
        if not any(k in keterangan for k in ['kantor', 'office', 'bisnis', 'business']):
            if flag == 'OK':
                flag = 'NEEDS_JUSTIFICATION'
            notes.append('Credit card payment - verify business use')
    
    # ATM withdrawal
    if 'atm' in tipe and 'withdrawal' in tipe:
        flag = 'NEEDS_JUSTIFICATION'
        notes = ['Cash withdrawal - needs documentation']
    
    # Default for transactions with no notes
    if not notes:
        if flag == 'OK':
            notes = ['Standard transaction']
        else:
            notes = ['Review required']
    
    return (flag, '; '.join(notes))


def extract_account_info(pdf_path: str) -> dict:
    """Extract account information from the PDF header."""
    info = {
        'No_Rekening': '',
        'Jenis_Produk': '',
        'Nama': '',
        'Mata_Uang': '',
        'Periode': ''
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text()
            if text:
                rekening_match = re.search(r'No\.\s*Rekening\s*:\s*(\d+)', text)
                if rekening_match:
                    info['No_Rekening'] = rekening_match.group(1)
                
                produk_match = re.search(r'Jenis\s*Produk\s*:\s*(.+?)(?:\n|$)', text)
                if produk_match:
                    info['Jenis_Produk'] = produk_match.group(1).strip()
                
                nama_match = re.search(r'Nama\s*:\s*(.+?)(?:\n|$)', text)
                if nama_match:
                    info['Nama'] = nama_match.group(1).strip()
                
                currency_match = re.search(r'Mata\s*Uang\s*:\s*(\w+)', text)
                if currency_match:
                    info['Mata_Uang'] = currency_match.group(1)
                
                periode_match = re.search(r'Periode\s*:\s*(.+?)(?:\n|$)', text)
                if periode_match:
                    info['Periode'] = periode_match.group(1).strip()
    
    return info


def extract_bank_name(text: str) -> str:
    """Extract bank name from text."""
    text_upper = text.upper()
    
    # Check for bank codes
    for code, name in BANK_CODE_MAP.items():
        if code in text_upper:
            return name
    
    return ''


def extract_ewallet(text: str) -> str:
    """Extract e-wallet name from text."""
    text_upper = text.upper()
    
    for pattern, name in EWALLET_PATTERNS.items():
        if pattern in text_upper:
            return name
    
    return ''


def parse_transaction_from_text(text_block: str) -> dict:
    """
    Parse a transaction text block into structured data with expanded description fields.
    """
    lines = [l.strip() for l in text_block.strip().split('\n') if l.strip()]
    
    if not lines:
        return None
    
    result = {
        'Tanggal': '',
        'Waktu': '',
        'Tipe_Transaksi': '',
        'Metode': '',
        'Penerima': '',
        'No_Referensi': '',
        'Bank_Tujuan_Code': '',
        'Bank_Tujuan': '',
        'E_Wallet': '',
        'No_Akun_Tujuan': '',
        'No_Kartu': '',
        'Keterangan': '',
        'Deskripsi_Lengkap': '',
        'Debit': '',
        'Kredit': '',
        'Saldo': ''
    }
    
    # Store full description
    result['Deskripsi_Lengkap'] = ' | '.join(lines)
    
    # First line contains date, transaction type, and amounts
    first_line = lines[0]
    
    # Extract date (DD MMM YYYY format)
    date_match = re.match(r'^(\d{2}\s+\w{3}\s+\d{4})\s+(.*)$', first_line)
    if not date_match:
        return None
    
    result['Tanggal'] = date_match.group(1)
    rest = date_match.group(2)
    
    # Extract amounts from the end of the line
    amounts = re.findall(r'(-?[\d,]+\.\d{2})', rest)
    
    # Remove amounts from description
    desc_part = re.sub(r'\s*-?[\d,]+\.\d{2}', '', rest).strip()
    result['Tipe_Transaksi'] = desc_part
    
    # Assign amounts
    if len(amounts) >= 1:
        result['Saldo'] = amounts[-1]
    if len(amounts) >= 2:
        amt = amounts[-2]
        if amt.startswith('-'):
            result['Debit'] = amt
        else:
            result['Kredit'] = amt
    if len(amounts) >= 3:
        result['Debit'] = amounts[0] if amounts[0].startswith('-') else ''
        result['Kredit'] = amounts[1] if not amounts[1].startswith('-') and amounts[1] != amounts[-1] else ''
        result['Saldo'] = amounts[-1]
    
    # Parse remaining lines for details
    all_description_lines = lines[1:]
    keterangan_candidates = []
    
    for line in all_description_lines:
        line_upper = line.upper()
        
        # Check for time pattern (HH:MM:SS)
        time_match = re.match(r'^(\d{2}:\d{2}:\d{2})$', line)
        if time_match:
            result['Waktu'] = line
            continue
        
        # Check for card number pattern (masked card)
        card_match = re.match(r'^(\d{6}\*+\d{4})$', line)
        if card_match:
            result['No_Kartu'] = line
            continue
        
        # Check for bank transfer reference and bank code (e.g., "000618958816 PDJBIDJA")
        ref_bank_match = re.match(r'^(\d{10,})\s+([A-Z]{6,10})$', line)
        if ref_bank_match:
            result['No_Referensi'] = ref_bank_match.group(1)
            result['Bank_Tujuan_Code'] = ref_bank_match.group(2)
            result['Bank_Tujuan'] = BANK_CODE_MAP.get(ref_bank_match.group(2), ref_bank_match.group(2))
            continue
        
        # Check for just reference number
        ref_match = re.match(r'^(\d{10,})$', line)
        if ref_match:
            result['No_Referensi'] = line
            continue
        
        # Check for account number with bank (e.g., "95956285217675118 BCA")
        acct_bank_match = re.match(r'^(\d+)\s+(BCA|BNI|BRI|MANDIRI|CIMB)$', line, re.IGNORECASE)
        if acct_bank_match:
            result['No_Akun_Tujuan'] = acct_bank_match.group(1)
            result['Bank_Tujuan'] = acct_bank_match.group(2).upper()
            continue
        
        # Check for BIFAST reference
        if 'BIFAST' in line_upper or line.startswith('BFS '):
            result['No_Referensi'] = line
            # Extract source bank from BIFAST
            bifast_bank = re.search(r'(BNINIDJA|CENAIDJA|BRINIDJA|BMRIIDJA)', line)
            if bifast_bank and not result['Bank_Tujuan']:
                result['Bank_Tujuan_Code'] = bifast_bank.group(1)
                result['Bank_Tujuan'] = BANK_CODE_MAP.get(bifast_bank.group(1), '')
            continue
        
        # Check for e-wallet patterns (GOPAY, OVO, SHOPEE, etc.)
        ewallet = extract_ewallet(line)
        if ewallet:
            if not result['E_Wallet']:  # Don't overwrite if already set
                result['E_Wallet'] = ewallet
            # Try to extract account number/phone
            ewallet_acct = re.search(r'(\d{10,})', line)
            if ewallet_acct and not result['No_Akun_Tujuan']:
                result['No_Akun_Tujuan'] = ewallet_acct.group(1)
            # Also check for phone number pattern in e-wallet
            phone_match = re.search(r'(08\d{9,})', line)
            if phone_match and not result['No_Akun_Tujuan']:
                result['No_Akun_Tujuan'] = phone_match.group(1)
        
        # Also check for account numbers with short bank names (95956285217675118 BCA)
        short_bank_match = re.search(r'(\d{10,})\s+(BCA|BNI|BRI|MANDIRI|CIMB)', line, re.IGNORECASE)
        if short_bank_match:
            if not result['No_Akun_Tujuan']:
                result['No_Akun_Tujuan'] = short_bank_match.group(1)
            if not result['Bank_Tujuan']:
                result['Bank_Tujuan'] = short_bank_match.group(2).upper()
                
        # Check for TOP UP patterns (ShopeePay, etc.)
        if 'TOP UP' in line_upper:
            topup_ewallet = extract_ewallet(line)
            if topup_ewallet and not result['E_Wallet']:
                result['E_Wallet'] = topup_ewallet
            topup_acct = re.search(r'(\d{10,})', line)
            if topup_acct and not result['No_Akun_Tujuan']:
                result['No_Akun_Tujuan'] = topup_acct.group(1)
        
        # Check for "TRF TO" pattern (transfer destination)
        trf_match = re.search(r'TRF\s+TO\s+(.+)', line, re.IGNORECASE)
        if trf_match:
            recipient = trf_match.group(1).strip()
            # Check if it's an e-wallet
            if any(ew in recipient.upper() for ew in EWALLET_PATTERNS.keys()):
                ewallet = extract_ewallet(recipient)
                if ewallet:
                    result['E_Wallet'] = ewallet
            else:
                if not result['Penerima']:
                    result['Penerima'] = recipient
            continue
        
        # Check for "TO " pattern (recipient) - OCTOmobile TO NAME
        if ' TO ' in line:
            parts = line.split(' TO ', 1)
            if len(parts) == 2:
                result['Metode'] = parts[0].strip()
                result['Penerima'] = parts[1].strip()
            continue
        
        # Check for bank code at the end (standalone)
        if re.match(r'^[A-Z]{6,10}$', line):
            result['Bank_Tujuan_Code'] = line
            result['Bank_Tujuan'] = BANK_CODE_MAP.get(line, line)
            continue
        
        # Check for QR Purchase details
        if 'QR Purchase' in line or 'QRS' in line:
            result['Metode'] = 'QR Payment'
            keterangan_candidates.append(line)
            continue
        
        # Check for BILL payment details
        if 'BILL' in line_upper or 'PAYMENT' in line_upper:
            bill_acct = re.search(r'(\d{16})', line)  # Credit card number
            if bill_acct:
                result['No_Akun_Tujuan'] = bill_acct.group(1)
            continue
        
        # It's likely a name continuation or keterangan
        if line.isupper() and result['Penerima'] and len(line) > 2 and len(line) < 30:
            # Looks like name continuation
            result['Penerima'] += ' ' + line
        else:
            # Likely keterangan
            keterangan_candidates.append(line)
    
    # Determine keterangan - usually the last non-technical line
    for candidate in reversed(keterangan_candidates):
        # Skip technical lines
        if re.match(r'^[A-Z0-9]{10,}$', candidate):
            continue
        if 'Page ' in candidate or 'GMB' in candidate:
            continue
        if not candidate.isupper() or len(candidate) > 50:
            result['Keterangan'] = candidate
            break
    
    # If no keterangan found but we have candidates
    if not result['Keterangan'] and keterangan_candidates:
        # Filter out technical entries
        filtered = [c for c in keterangan_candidates 
                   if not re.match(r'^[A-Z0-9]{10,}$', c) 
                   and 'Page ' not in c
                   and 'GMB' not in c]
        if filtered:
            result['Keterangan'] = filtered[-1]
    
    # Extract bank from description if not found elsewhere
    if not result['Bank_Tujuan']:
        for line in all_description_lines:
            bank = extract_bank_name(line)
            if bank:
                result['Bank_Tujuan'] = bank
                break
    
    return result


def extract_transactions_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Extract ALL transaction data from a CASA bank statement PDF using text parsing."""
    pdf_path = Path(pdf_path)
    account_info = extract_account_info(str(pdf_path))
    
    all_transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            date_pattern = re.compile(r'^\d{2}\s+\w{3}\s+\d{4}\s+')
            
            current_block = []
            
            for line in lines:
                # Skip header/footer lines
                if any(skip in line for skip in [
                    'Laporan Rekening', 'Statement of Account', 'Periode:',
                    'No. Rekening', 'Jenis Produk', 'Nama :', 'Mata Uang',
                    'Tanggal Deskripsi Debit Kredit Saldo',
                    'Page ', 'IMPORTANT', 'User ID', 'Your User ID',
                    'Saldo Awal', 'Total Kredit', 'Total Debit', 'Saldo Akhir',
                    'www.', 'CIMB'
                ]):
                    continue
                
                if date_pattern.match(line):
                    if current_block:
                        block_text = '\n'.join(current_block)
                        txn = parse_transaction_from_text(block_text)
                        if txn and txn['Tanggal']:
                            all_transactions.append(txn)
                    current_block = [line]
                else:
                    if current_block:
                        current_block.append(line)
            
            if current_block:
                block_text = '\n'.join(current_block)
                txn = parse_transaction_from_text(block_text)
                if txn and txn['Tanggal']:
                    all_transactions.append(txn)
    
    if not all_transactions:
        return pd.DataFrame()
    
    # Add account info, classification and audit flags
    for txn in all_transactions:
        txn['No_Rekening'] = account_info['No_Rekening']
        txn['Nama'] = account_info['Nama']
        txn['Jenis_Produk'] = account_info['Jenis_Produk']
        txn['Mata_Uang'] = account_info['Mata_Uang']
        txn['Periode'] = account_info['Periode']
        txn['Klasifikasi'] = classify_transaction(txn)
        
        # Add audit classification
        audit_flag, audit_notes = audit_transaction(txn)
        txn['Audit_Flag'] = audit_flag
        txn['Audit_Notes'] = audit_notes
    
    df = pd.DataFrame(all_transactions)
    df['Source_File'] = pdf_path.name
    
    month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})', pdf_path.name)
    if month_match:
        df['Month'] = month_match.group(1)
        df['Year'] = month_match.group(2)
    
    return df


def parse_amount(value: str) -> float:
    """Parse Indonesian formatted amount to float."""
    if not value or value.strip() == '':
        return 0.0
    cleaned = value.strip().replace(',', '').replace(' ', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def compile_all_pdfs(pdf_dir: str, output_file: str = None) -> str:
    """Compile all PDF bank statements in a directory into a single Excel file."""
    pdf_path = Path(pdf_dir)
    
    pdf_files = list(pdf_path.glob('*.pdf')) + list(pdf_path.glob('*.pdf.pdf'))
    pdf_files = list(set(pdf_files))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {pdf_dir}")
        return None
    
    month_order = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                   'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    def get_month_sort_key(f):
        match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})', f.name)
        if match:
            return (int(match.group(2)), month_order.get(match.group(1), 0))
        return (9999, 99)
    
    pdf_files.sort(key=get_month_sort_key)
    
    print(f"📂 Found {len(pdf_files)} PDF file(s)")
    print("=" * 60)
    
    all_dataframes = []
    
    for pdf_file in pdf_files:
        print(f"  📄 Processing: {pdf_file.name}...", end=' ')
        try:
            df = extract_transactions_from_pdf(str(pdf_file))
            if not df.empty:
                all_dataframes.append(df)
                print(f"✓ {len(df)} transactions")
            else:
                print("⚠ No data extracted")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    if not all_dataframes:
        print("❌ No data extracted from any files")
        return None
    
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    combined_df['Debit_Value'] = combined_df['Debit'].apply(parse_amount)
    combined_df['Kredit_Value'] = combined_df['Kredit'].apply(parse_amount)
    combined_df['Saldo_Value'] = combined_df['Saldo'].apply(parse_amount)
    
    if not output_file:
        output_file = pdf_path.parent / 'CASA_Combined_Statements.xlsx'
    
    print("\n" + "=" * 60)
    print(f"💾 Saving to: {output_file}")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main sheet with all expanded columns including audit
        column_order = [
            'Audit_Flag', 'Audit_Notes',  # Audit columns first for easy review
            'Klasifikasi',
            'No_Rekening', 'Nama', 'Jenis_Produk', 'Mata_Uang', 'Periode',
            'Tanggal', 'Waktu', 
            'Tipe_Transaksi', 'Metode', 
            'Penerima', 'Bank_Tujuan', 'E_Wallet',
            'No_Referensi', 'No_Akun_Tujuan', 'No_Kartu',
            'Keterangan', 
            'Debit', 'Kredit', 'Saldo',
            'Deskripsi_Lengkap',
            'Month', 'Year'
        ]
        
        existing_cols = [c for c in column_order if c in combined_df.columns]
        combined_df[existing_cols].to_excel(writer, index=False, sheet_name='All_Transactions')
        
        # Summary calculations
        company_total = combined_df[combined_df['Klasifikasi'] == 'Company']['Debit_Value'].sum()
        private_total = combined_df[combined_df['Klasifikasi'] == 'Private']['Debit_Value'].sum()
        review_total = combined_df[combined_df['Klasifikasi'] == 'Review']['Debit_Value'].sum()
        
        # Audit flag calculations
        suspicious_count = (combined_df['Audit_Flag'] == 'SUSPICIOUS').sum()
        suspicious_total = combined_df[combined_df['Audit_Flag'] == 'SUSPICIOUS']['Debit_Value'].sum()
        needs_justification_count = (combined_df['Audit_Flag'] == 'NEEDS_JUSTIFICATION').sum()
        needs_justification_total = combined_df[combined_df['Audit_Flag'] == 'NEEDS_JUSTIFICATION']['Debit_Value'].sum()
        ok_count = (combined_df['Audit_Flag'] == 'OK').sum()
        ok_total = combined_df[combined_df['Audit_Flag'] == 'OK']['Debit_Value'].sum()
        
        # Count by bank/ewallet
        bank_counts = combined_df['Bank_Tujuan'].value_counts().head(10)
        ewallet_counts = combined_df['E_Wallet'].value_counts()
        
        summary_data = {
            'Metric': [
                '=== ACCOUNT INFO ===', 
                'No Rekening', 'Nama Pemilik', 'Jenis Produk', 'Mata Uang',
                '',
                '=== AUDIT SUMMARY (FOR REVIEW) ===',
                '🔴 SUSPICIOUS Transactions', '🔴 SUSPICIOUS Total Debit',
                '⚠️ NEEDS JUSTIFICATION Transactions', '⚠️ NEEDS JUSTIFICATION Total Debit',
                '✅ OK Transactions', '✅ OK Total Debit',
                '',
                '=== CLASSIFICATION SUMMARY ===',
                'Company Transactions', 'Company Total Debit',
                'Private Transactions', 'Private Total Debit',
                'Needs Review', 'Review Total Debit',
                '',
                '=== DESTINATION SUMMARY ===',
            ] + [f'Bank: {bank}' for bank in bank_counts.index[:5]] +
            [f'E-Wallet: {ew}' for ew in ewallet_counts.index if ew] + [
                '',
                '=== OVERALL SUMMARY ===',
                'Total Transactions', 'Total Debit', 'Total Credit', 
                'Net Flow', 'First Date', 'Last Date', 'Files Processed',
                'Unique Recipients', 'With Keterangan'
            ],
            'Value': [
                '',
                combined_df['No_Rekening'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Nama'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Jenis_Produk'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Mata_Uang'].iloc[0] if len(combined_df) > 0 else 'N/A',
                '',
                '',
                suspicious_count,
                f"{suspicious_total:,.2f}",
                needs_justification_count,
                f"{needs_justification_total:,.2f}",
                ok_count,
                f"{ok_total:,.2f}",
                '',
                '',
                (combined_df['Klasifikasi'] == 'Company').sum(),
                f"{company_total:,.2f}",
                (combined_df['Klasifikasi'] == 'Private').sum(),
                f"{private_total:,.2f}",
                (combined_df['Klasifikasi'] == 'Review').sum(),
                f"{review_total:,.2f}",
                '',
                '',
            ] + [f"{count} transactions" for count in bank_counts.values[:5]] +
            [f"{ewallet_counts[ew]} transactions" for ew in ewallet_counts.index if ew] + [
                '',
                '',
                len(combined_df),
                f"{combined_df['Debit_Value'].sum():,.2f}",
                f"{combined_df['Kredit_Value'].sum():,.2f}",
                f"{combined_df['Kredit_Value'].sum() - abs(combined_df['Debit_Value'].sum()):,.2f}",
                combined_df['Tanggal'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Tanggal'].iloc[-1] if len(combined_df) > 0 else 'N/A',
                len(pdf_files),
                combined_df['Penerima'].nunique(),
                (combined_df['Keterangan'] != '').sum()
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, index=False, sheet_name='Summary')
        
        # SUSPICIOUS transactions sheet (for auditor focus)
        suspicious_df = combined_df[combined_df['Audit_Flag'] == 'SUSPICIOUS'].copy()
        if not suspicious_df.empty:
            susp_cols = [c for c in ['Audit_Notes', 'Tanggal', 'Waktu', 'Tipe_Transaksi', 'Penerima', 
                                     'Bank_Tujuan', 'E_Wallet', 'Keterangan', 
                                     'Debit', 'Kredit', 'Saldo'] if c in suspicious_df.columns]
            suspicious_df[susp_cols].to_excel(writer, index=False, sheet_name='SUSPICIOUS')
        
        # NEEDS_JUSTIFICATION sheet
        needs_just_df = combined_df[combined_df['Audit_Flag'] == 'NEEDS_JUSTIFICATION'].copy()
        if not needs_just_df.empty:
            just_cols = [c for c in ['Audit_Notes', 'Tanggal', 'Waktu', 'Tipe_Transaksi', 'Penerima', 
                                     'Bank_Tujuan', 'E_Wallet', 'Keterangan', 
                                     'Debit', 'Kredit', 'Saldo'] if c in needs_just_df.columns]
            needs_just_df[just_cols].to_excel(writer, index=False, sheet_name='NEEDS_JUSTIFICATION')
        
        # Classification sheets
        for classification in ['Company', 'Private', 'Review']:
            class_df = combined_df[combined_df['Klasifikasi'] == classification].copy()
            if not class_df.empty:
                class_cols = [c for c in ['Audit_Flag', 'Audit_Notes', 'Tanggal', 'Waktu', 'Tipe_Transaksi', 'Penerima', 
                                          'Bank_Tujuan', 'E_Wallet', 'Keterangan', 
                                          'Debit', 'Kredit', 'Saldo'] if c in class_df.columns]
                class_df[class_cols].to_excel(writer, index=False, sheet_name=classification)
        
        # Monthly sheets with audit flags
        if 'Month' in combined_df.columns:
            for month in month_order.keys():
                if month in combined_df['Month'].values:
                    month_df = combined_df[combined_df['Month'] == month].copy()
                    month_cols = [c for c in ['Audit_Flag', 'Audit_Notes', 'Klasifikasi', 'Tanggal', 'Waktu', 'Tipe_Transaksi', 
                                              'Penerima', 'Bank_Tujuan', 'E_Wallet',
                                              'Keterangan', 'Debit', 'Kredit', 'Saldo'] if c in month_df.columns]
                    month_df[month_cols].to_excel(writer, index=False, sheet_name=f'{month}')
        
        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col_idx, column in enumerate(worksheet.columns, 1):
                max_length = 0
                col_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                worksheet.column_dimensions[col_letter].width = min(max_length + 2, 60)
    
    # Print summary
    print(f"✨ Successfully compiled {len(combined_df)} transactions from {len(pdf_files)} files!")
    print(f"\n📊 Account Info:")
    print(f"   No Rekening:   {combined_df['No_Rekening'].iloc[0] if len(combined_df) > 0 else 'N/A'}")
    print(f"   Nama:          {combined_df['Nama'].iloc[0] if len(combined_df) > 0 else 'N/A'}")
    
    print(f"\n� Transfer Destinations:")
    for bank, count in bank_counts.head(5).items():
        if bank:
            print(f"   {bank:15} {count:>5} transactions")
    
    print(f"\n💳 E-Wallets:")
    for ew, count in ewallet_counts.items():
        if ew:
            print(f"   {ew:15} {count:>5} transactions")
    
    print(f"\n�🏢 Classification Summary (for Audit):")
    print(f"   Company:       {(combined_df['Klasifikasi'] == 'Company').sum():>5} txns  |  Debit: {company_total:>18,.2f}")
    print(f"   Private:       {(combined_df['Klasifikasi'] == 'Private').sum():>5} txns  |  Debit: {private_total:>18,.2f}")
    print(f"   Needs Review:  {(combined_df['Klasifikasi'] == 'Review').sum():>5} txns  |  Debit: {review_total:>18,.2f}")
    
    return str(output_file)


if __name__ == "__main__":
    import sys
    
    script_dir = Path(__file__).parent.parent
    pdf_dir = script_dir / 'pdf' / 'casa'
    output_file = script_dir / 'excel' / 'CASA_Combined_Statements.xlsx'
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n🔍 PDF to Excel Converter for CASA Bank Statements")
    print("   With Expanded Description & Classification")
    print("=" * 60)
    
    result = compile_all_pdfs(str(pdf_dir), str(output_file))
    
    if result:
        print(f"\n📁 Output saved to: {result}")
        print("\n⚠️  Note: 'Review' items need manual classification")
