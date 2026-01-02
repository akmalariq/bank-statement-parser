"""
BNI Bank Statement Parser
Extracts transaction data from BNI personal bank statement PDFs
Password protected PDFs are supported
Format aligned with CASA parser for consistency
"""

import pdfplumber
import pandas as pd
from pathlib import Path
import re


# Default password for BNI PDFs
BNI_PASSWORD = '02121979'

# E-wallet patterns
EWALLET_PATTERNS = {
    'SHOPEEPAY': 'ShopeePay',
    'SHOPEE PAY': 'ShopeePay',
    'TOP UP SHOPEE': 'ShopeePay',
    'GOPAY': 'GoPay',
    'GO-PAY': 'GoPay',
    'TOP UP GOPAY': 'GoPay',
    'OVO': 'OVO',
    'DANA': 'DANA',
    'LINKAJA': 'LinkAja',
}


def extract_ewallet(text: str) -> str:
    """Extract e-wallet name from text."""
    text_upper = text.upper()
    for pattern, name in EWALLET_PATTERNS.items():
        if pattern in text_upper:
            return name
    return ''


def extract_account_info_bni(pdf_path: str, password: str = None) -> dict:
    """Extract account information from BNI PDF header."""
    info = {
        'No_Rekening': '',
        'Jenis_Produk': '',
        'Nama': '',
        'Mata_Uang': 'IDR',
        'Periode': '',
        'Bank': 'BNI'
    }
    
    pw = password or BNI_PASSWORD
    
    with pdfplumber.open(pdf_path, password=pw) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text()
            if text:
                name_acct = re.search(r'^([A-Z\s]+)\s+(TAPLUS|TAPENAS|BNI Giro|[A-Za-z]+)\s*-\s*(\d+)', text, re.MULTILINE)
                if name_acct:
                    info['Nama'] = name_acct.group(1).strip()
                    info['Jenis_Produk'] = name_acct.group(2).strip()
                    info['No_Rekening'] = name_acct.group(3).strip()
                
                periode_match = re.search(r'Periode:\s*(.+?)(?:\n|$)', text)
                if periode_match:
                    info['Periode'] = periode_match.group(1).strip()
    
    return info


def parse_bni_description(tipe: str, desc: str) -> dict:
    """Parse BNI transaction type and description to extract structured fields."""
    result = {
        'Penerima': '',
        'Bank_Tujuan': '',
        'E_Wallet': '',
        'No_Akun_Tujuan': '',
        'Keterangan': desc
    }
    
    combined = f"{tipe} {desc}".upper()
    
    # E-wallet detection
    ewallet = extract_ewallet(combined)
    if ewallet:
        result['E_Wallet'] = ewallet
        # Extract phone number for e-wallet
        phone_match = re.search(r'(62\d{9,}|08\d{9,})', combined)
        if phone_match:
            result['No_Akun_Tujuan'] = phone_match.group(1)
    
    # Transfer recipient extraction
    if 'TRANSFER' in tipe.upper():
        # Format: "BNI - RECIPIENT NAME" or "BANK - RECIPIENT NAME"
        transfer_match = re.match(r'^(BNI|BCA|BRI|MANDIRI|CIMB)\s*[-]\s*(.+)$', desc, re.IGNORECASE)
        if transfer_match:
            result['Bank_Tujuan'] = transfer_match.group(1).upper()
            result['Penerima'] = transfer_match.group(2).strip()
        else:
            result['Penerima'] = desc
    
    # QRIS payment - merchant name is the recipient
    if 'QRIS' in tipe.upper() or 'PEMBAYARAN QRIS' in tipe.upper():
        # Extract merchant name (before location)
        merchant_match = re.match(r'^([A-Z0-9\s]+?)(?:\s*[-]\s*|\s+(?:JAKARTA|KOTA|BANDUNG|SURABAYA))', desc, re.IGNORECASE)
        if merchant_match:
            result['Penerima'] = merchant_match.group(1).strip()
        else:
            result['Penerima'] = desc.split(' - ')[0] if ' - ' in desc else desc
    
    # Virtual Account
    if 'VIRTUAL ACCOUNT' in tipe.upper():
        result['Penerima'] = desc
    
    # Setor/Tarik Tunai
    if 'SETOR TUNAI' in tipe.upper() or 'TARIK TUNAI' in tipe.upper():
        result['Penerima'] = desc
        result['Bank_Tujuan'] = 'BNI'
    
    return result


def extract_transactions_from_bni(pdf_path: str, password: str = None) -> pd.DataFrame:
    """Extract all transactions from a BNI bank statement PDF."""
    pdf_path = Path(pdf_path)
    pw = password or BNI_PASSWORD
    
    account_info = extract_account_info_bni(str(pdf_path), pw)
    all_transactions = []
    
    with pdfplumber.open(pdf_path, password=pw) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            date_pattern = re.compile(r'^\d{2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}\s+')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if any(skip in line for skip in [
                    'Laporan Mutasi', 'Periode:', 'Saldo Awal', 'Total Pemasukan',
                    'Total Pengeluaran', 'Saldo Akhir', 'Tanggal & Waktu',
                    'Rincian Transaksi', 'Nominal (IDR)', 'Saldo (IDR)',
                    'PT Bank Negara Indonesia', 'berizin dan diawasi',
                    'peserta penjaminan', 'dari 7', 'dari 6', 'dari 5', 'dari 8'
                ]):
                    i += 1
                    continue
                
                if date_pattern.match(line):
                    parts = line.split(maxsplit=4)
                    
                    if len(parts) >= 4:
                        tipe_transaksi = ' '.join(parts[3:]) if len(parts) > 3 else ''
                        
                        txn = {
                            'Tanggal': f"{parts[0]} {parts[1]} {parts[2]}",
                            'Tipe_Transaksi': tipe_transaksi,
                            'Waktu': '',
                            'Deskripsi': '',
                            'Debit': '',
                            'Kredit': '',
                            'Saldo': '',
                            'Deskripsi_Lengkap': line
                        }
                        
                        j = i + 1
                        desc_lines = []
                        while j < len(lines) and j < i + 4:
                            next_line = lines[j].strip()
                            
                            if date_pattern.match(next_line):
                                break
                            
                            amount_match = re.match(r'^([+-][\d,]+)\s+([\d,]+)$', next_line)
                            if amount_match:
                                amount = amount_match.group(1)
                                if amount.startswith('-'):
                                    txn['Debit'] = amount
                                else:
                                    txn['Kredit'] = amount.replace('+', '')
                                txn['Saldo'] = amount_match.group(2)
                                j += 1
                                continue
                            
                            time_match = re.match(r'^(\d{2}:\d{2}:\d{2})\s+WIB\s*(.*)$', next_line)
                            if time_match:
                                txn['Waktu'] = time_match.group(1)
                                if time_match.group(2):
                                    desc_lines.append(time_match.group(2).strip())
                                j += 1
                                continue
                            
                            j += 1
                        
                        txn['Deskripsi'] = ' '.join(desc_lines) if desc_lines else ''
                        txn['Deskripsi_Lengkap'] += ' | ' + txn['Deskripsi'] if txn['Deskripsi'] else ''
                        
                        # Parse description for structured fields
                        parsed = parse_bni_description(tipe_transaksi, txn['Deskripsi'])
                        txn['Penerima'] = parsed['Penerima']
                        txn['Bank_Tujuan'] = parsed['Bank_Tujuan']
                        txn['E_Wallet'] = parsed['E_Wallet']
                        txn['No_Akun_Tujuan'] = parsed['No_Akun_Tujuan']
                        txn['Keterangan'] = parsed['Keterangan']
                        
                        # Add account info
                        txn['No_Rekening'] = account_info['No_Rekening']
                        txn['Nama'] = account_info['Nama']
                        txn['Jenis_Produk'] = account_info['Jenis_Produk']
                        txn['Mata_Uang'] = account_info['Mata_Uang']
                        txn['Periode'] = account_info['Periode']
                        
                        # Classify transaction
                        txn['Klasifikasi'] = classify_bni_transaction(txn)
                        audit_flag, audit_notes = audit_bni_transaction(txn)
                        txn['Audit_Flag'] = audit_flag
                        txn['Audit_Notes'] = audit_notes
                        
                        all_transactions.append(txn)
                
                i += 1
    
    if not all_transactions:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_transactions)
    df['Source_File'] = pdf_path.name
    
    month_map = {
        'Januari': 'Jan', 'Februari': 'Feb', 'Maret': 'Mar', 'April': 'Apr',
        'Mei': 'May', 'Juni': 'Jun', 'Juli': 'Jul', 'Agustus': 'Aug',
        'September': 'Sep', 'Oktober': 'Oct', 'November': 'Nov', 'Desember': 'Dec'
    }
    
    for indo, eng in month_map.items():
        if indo in pdf_path.name:
            df['Month'] = eng
            break
    
    year_match = re.search(r'_(\d{4})\.pdf', pdf_path.name)
    if year_match:
        df['Year'] = year_match.group(1)
    
    return df


def classify_bni_transaction(row: dict) -> str:
    """Classify BNI transaction as Company, Private, or Review."""
    tipe = str(row.get('Tipe_Transaksi', '')).lower()
    desc = str(row.get('Deskripsi', '')).lower()
    penerima = str(row.get('Penerima', '')).lower()
    
    personal_keywords = [
        'gokana', 'burger king', 'mcd', 'kfc', 'starbucks', 'coffee',
        'transmart', 'superindo', 'alfamart', 'indomaret',
        'holland bakery', 'breadtalk', 'jco', 'es teh',
        'gopay', 'ovo', 'dana', 'shopeepay',
        'netflix', 'spotify', 'youtube',
        'grab', 'gojek', 'warung', 'nasi goreng'
    ]
    
    company_keywords = [
        'pemerintah', 'ditjen', 'perbendaharaan', 'depkeu',
        'virtual account', 'pusbanglin', 'badan bahasa',
        'kantor', 'office', 'monami'
    ]
    
    combined = (tipe + ' ' + desc + ' ' + penerima).lower()
    
    for kw in company_keywords:
        if kw in combined:
            return 'Company'
    
    for kw in personal_keywords:
        if kw in combined:
            return 'Private'
    
    return 'Review'


def audit_bni_transaction(row: dict) -> tuple:
    """Audit BNI transaction for suspicious patterns."""
    tipe = str(row.get('Tipe_Transaksi', '')).lower()
    desc = str(row.get('Deskripsi', '')).lower()
    penerima = str(row.get('Penerima', '')).lower()
    ewallet = str(row.get('E_Wallet', '')).lower()
    debit = str(row.get('Debit', ''))
    
    try:
        debit_val = abs(float(debit.replace(',', '').replace('-', '').replace('+', '') or 0))
    except:
        debit_val = 0
    
    notes = []
    flag = 'OK'
    
    combined = (tipe + ' ' + desc + ' ' + penerima).lower()
    
    # E-wallet top-ups
    if ewallet or 'ewallet' in tipe.lower() or 'gopay' in combined or 'shopeepay' in combined:
        flag = 'SUSPICIOUS'
        notes.append(f'E-wallet top-up ({ewallet or "unknown"})')
    
    # QRIS payments at personal locations
    if 'qris' in tipe.lower():
        personal_places = ['gokana', 'burger', 'mcd', 'kfc', 'starbucks', 'bakery', 
                          'coffee', 'resto', 'cafe', 'warung', 'nasi goreng', 'es teh']
        if any(p in combined for p in personal_places):
            flag = 'SUSPICIOUS'
            notes.append('Restaurant/food purchase')
    
    # Government transfers are OK
    if 'pemerintah' in combined or 'ditjen' in combined:
        flag = 'OK'
        notes = ['Government transfer']
    
    # Virtual Account to Pusbanglin is OK
    if 'virtual account' in tipe.lower() and 'pusbanglin' in combined:
        flag = 'OK'
        notes = ['Office virtual account']
    
    # Large cash deposits/withdrawals
    if 'setor tunai' in tipe.lower() or 'tarik tunai' in tipe.lower():
        flag = 'NEEDS_JUSTIFICATION'
        notes = [f'Cash transaction (Rp {debit_val:,.0f})']
    
    # Biaya / Fees (usually OK)
    if 'biaya' in tipe.lower():
        flag = 'OK'
        notes = ['Bank fee']
    
    if not notes:
        notes = ['Standard transaction']
    
    return (flag, '; '.join(notes))


def parse_amount(value: str) -> float:
    """Parse BNI formatted amount to float."""
    if not value or value.strip() == '':
        return 0.0
    cleaned = value.strip().replace(',', '').replace('+', '').replace('-', '')
    try:
        val = float(cleaned)
        if value.strip().startswith('-'):
            return -val
        return val
    except ValueError:
        return 0.0


def compile_bni_pdfs(pdf_dir: str, output_file: str = None, password: str = None) -> str:
    """Compile all BNI PDF statements into Excel (CASA-compatible format)."""
    pdf_path = Path(pdf_dir)
    pw = password or BNI_PASSWORD
    
    pdf_files = list(pdf_path.glob('BNI_*.pdf'))
    
    if not pdf_files:
        print(f"❌ No BNI PDF files found in {pdf_dir}")
        return None
    
    month_order = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                   'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    month_indo = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                  'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    def get_month_sort_key(f):
        for i, month in enumerate(month_indo):
            if month in f.name:
                return i
        return 99
    
    pdf_files.sort(key=get_month_sort_key)
    
    print(f"📂 Found {len(pdf_files)} BNI PDF file(s)")
    print("=" * 60)
    
    all_dataframes = []
    
    for pdf_file in pdf_files:
        print(f"  📄 Processing: {pdf_file.name}...", end=' ')
        try:
            df = extract_transactions_from_bni(str(pdf_file), pw)
            if not df.empty:
                all_dataframes.append(df)
                print(f"✓ {len(df)} transactions")
            else:
                print("⚠ No data extracted")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if not all_dataframes:
        print("❌ No data extracted from any files")
        return None
    
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    combined_df['Debit_Value'] = combined_df['Debit'].apply(parse_amount)
    combined_df['Kredit_Value'] = combined_df['Kredit'].apply(parse_amount)
    combined_df['Saldo_Value'] = combined_df['Saldo'].apply(parse_amount)
    
    if not output_file:
        output_file = pdf_path.parent / 'BNI_Combined_Statements.xlsx'
    
    print("\n" + "=" * 60)
    print(f"💾 Saving to: {output_file}")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main sheet - CASA compatible columns
        column_order = [
            'Audit_Flag', 'Audit_Notes', 'Klasifikasi',
            'No_Rekening', 'Nama', 'Jenis_Produk', 'Mata_Uang', 'Periode',
            'Tanggal', 'Waktu', 
            'Tipe_Transaksi',
            'Penerima', 'Bank_Tujuan', 'E_Wallet',
            'No_Akun_Tujuan', 'Keterangan',
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
        
        suspicious_count = (combined_df['Audit_Flag'] == 'SUSPICIOUS').sum()
        suspicious_total = combined_df[combined_df['Audit_Flag'] == 'SUSPICIOUS']['Debit_Value'].sum()
        needs_just_count = (combined_df['Audit_Flag'] == 'NEEDS_JUSTIFICATION').sum()
        needs_just_total = combined_df[combined_df['Audit_Flag'] == 'NEEDS_JUSTIFICATION']['Debit_Value'].sum()
        ok_count = (combined_df['Audit_Flag'] == 'OK').sum()
        ok_total = combined_df[combined_df['Audit_Flag'] == 'OK']['Debit_Value'].sum()
        
        summary_data = {
            'Metric': [
                '=== ACCOUNT INFO ===',
                'No Rekening', 'Nama Pemilik', 'Jenis Produk', 'Bank',
                '',
                '=== AUDIT SUMMARY ===',
                '🔴 SUSPICIOUS', '🔴 SUSPICIOUS Total',
                '⚠️ NEEDS JUSTIFICATION', '⚠️ NEEDS JUSTIFICATION Total',
                '✅ OK', '✅ OK Total',
                '',
                '=== CLASSIFICATION ===',
                'Company', 'Company Total',
                'Private', 'Private Total',
                'Review', 'Review Total',
                '',
                '=== OVERALL ===',
                'Total Transactions', 'Total Debit', 'Total Credit'
            ],
            'Value': [
                '',
                combined_df['No_Rekening'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Nama'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Jenis_Produk'].iloc[0] if len(combined_df) > 0 else 'N/A',
                'BNI',
                '',
                '',
                suspicious_count, f"{suspicious_total:,.2f}",
                needs_just_count, f"{needs_just_total:,.2f}",
                ok_count, f"{ok_total:,.2f}",
                '',
                '',
                (combined_df['Klasifikasi'] == 'Company').sum(), f"{company_total:,.2f}",
                (combined_df['Klasifikasi'] == 'Private').sum(), f"{private_total:,.2f}",
                (combined_df['Klasifikasi'] == 'Review').sum(), f"{review_total:,.2f}",
                '',
                '',
                len(combined_df),
                f"{combined_df['Debit_Value'].sum():,.2f}",
                f"{combined_df['Kredit_Value'].sum():,.2f}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        
        # SUSPICIOUS sheet
        suspicious_df = combined_df[combined_df['Audit_Flag'] == 'SUSPICIOUS'].copy()
        if not suspicious_df.empty:
            susp_cols = ['Audit_Notes', 'Tanggal', 'Waktu', 'Tipe_Transaksi', 'Penerima', 
                        'E_Wallet', 'Keterangan', 'Debit', 'Saldo']
            existing = [c for c in susp_cols if c in suspicious_df.columns]
            suspicious_df[existing].to_excel(writer, index=False, sheet_name='SUSPICIOUS')
        
        # NEEDS_JUSTIFICATION sheet
        needs_just_df = combined_df[combined_df['Audit_Flag'] == 'NEEDS_JUSTIFICATION'].copy()
        if not needs_just_df.empty:
            just_cols = ['Audit_Notes', 'Tanggal', 'Waktu', 'Tipe_Transaksi', 'Penerima', 
                        'Keterangan', 'Debit', 'Kredit', 'Saldo']
            existing = [c for c in just_cols if c in needs_just_df.columns]
            needs_just_df[existing].to_excel(writer, index=False, sheet_name='NEEDS_JUSTIFICATION')
        
        # Classification sheets
        for classification in ['Company', 'Private', 'Review']:
            class_df = combined_df[combined_df['Klasifikasi'] == classification].copy()
            if not class_df.empty:
                class_cols = ['Audit_Flag', 'Audit_Notes', 'Tanggal', 'Waktu', 
                             'Tipe_Transaksi', 'Penerima', 'E_Wallet',
                             'Keterangan', 'Debit', 'Kredit', 'Saldo']
                existing = [c for c in class_cols if c in class_df.columns]
                class_df[existing].to_excel(writer, index=False, sheet_name=classification)
        
        # Monthly sheets
        if 'Month' in combined_df.columns:
            for month in month_order.keys():
                if month in combined_df['Month'].values:
                    month_df = combined_df[combined_df['Month'] == month].copy()
                    month_cols = ['Audit_Flag', 'Audit_Notes', 'Klasifikasi', 'Tanggal', 'Waktu',
                                 'Tipe_Transaksi', 'Penerima', 'E_Wallet',
                                 'Keterangan', 'Debit', 'Kredit', 'Saldo']
                    existing = [c for c in month_cols if c in month_df.columns]
                    month_df[existing].to_excel(writer, index=False, sheet_name=month)
        
        # Auto-adjust columns
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = max(len(str(cell.value or '')) for cell in column)
                worksheet.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    print(f"✨ Successfully compiled {len(combined_df)} transactions from {len(pdf_files)} files!")
    print(f"\n📊 Account: {combined_df['Nama'].iloc[0]} ({combined_df['No_Rekening'].iloc[0]})")
    print(f"\n🔴 SUSPICIOUS: {suspicious_count} transactions ({suspicious_total:,.2f})")
    print(f"⚠️  NEEDS JUST: {needs_just_count} transactions")
    print(f"✅ OK:         {ok_count} transactions")
    
    return str(output_file)


if __name__ == "__main__":
    script_dir = Path(__file__).parent.parent
    pdf_dir = script_dir / 'pdf' / 'bni'
    output_file = script_dir / 'excel' / 'BNI_Combined_Statements.xlsx'
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n🏦 BNI Bank Statement Parser")
    print("=" * 60)
    
    result = compile_bni_pdfs(str(pdf_dir), str(output_file))
    
    if result:
        print(f"\n📁 Output saved to: {result}")
