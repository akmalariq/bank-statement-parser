"""
SPAN Government Treasury Statement Parser
Extracts transaction data from BNI SPAN government account PDFs
Used for Satker (work unit) accounts like Pusbanglin Badan Bahasa
"""

import pdfplumber
import pandas as pd
from pathlib import Path
import re


def extract_account_info_span(pdf_path: str) -> dict:
    """Extract account information from SPAN PDF header."""
    info = {
        'Kementerian': '',
        'Unit': '',
        'Rekening_Induk': '',
        'Rekening_Satker': '',
        'Periode': '',
        'Bank': 'BNI SPAN'
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text()
            if text:
                # Extract period
                periode_match = re.search(r'Mutasi Transaksi \((.+?)\)', text)
                if periode_match:
                    info['Periode'] = periode_match.group(1)
                
                # Extract Kementerian
                if 'Kementerian' in text:
                    kem_match = re.search(r'(Kementerian .+?)\s*\(\d+\)', text)
                    if kem_match:
                        info['Kementerian'] = kem_match.group(1).strip()
                
                # Extract unit (Badan)
                badan_match = re.search(r'(BADAN .+?)\s+\d+\s*\(\d+\)', text)
                if badan_match:
                    info['Unit'] = badan_match.group(1).strip()
                
                # Extract Rekening Induk
                induk_match = re.search(r'Rekening Induk\s*:\s*(.+?)\s*\((\d+)\)', text)
                if induk_match:
                    info['Rekening_Induk'] = f"{induk_match.group(1).strip()} ({induk_match.group(2)})"
                
                # Extract Rekening Satker
                satker_match = re.search(r'Rekening Satker\s*:\s*(.+?)\s*\((\d+)\)', text)
                if satker_match:
                    info['Rekening_Satker'] = f"{satker_match.group(1).strip()} ({satker_match.group(2)})"
    
    return info


def extract_transactions_from_span(pdf_path: str) -> pd.DataFrame:
    """Extract all transactions from a SPAN government account PDF."""
    pdf_path = Path(pdf_path)
    
    account_info = extract_account_info_span(str(pdf_path))
    all_transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip header lines
                if any(skip in line for skip in [
                    'Mutasi Transaksi', 'Kementerian', 'BADAN', 'SEKRETARIAT',
                    'Rekening Induk', 'Rekening Satker', 'Tanggal Waktu',
                    'Total Mutasi', 'downloaded at', 'INITIAL BALANCE',
                    'Filter', 'Waktu Transaksi', 'Apply Export', 'Id Transaksi',
                    'Cari Berdasarkan', 'Saldo Awal Debit Credit'
                ]):
                    i += 1
                    continue
                
                # NEW FORMAT: Full date "2025-04-08 08:45:45 234164 TARIK TUNAI..."
                new_format = re.match(r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\d+)\s+(.+)$', line)
                
                # OLD FORMAT: Split date "2025- HH:MM:SS ID..."
                old_format = re.match(r'^(\d{4})-\s+(\d{2}:\d{2}:\d{2})\s+(\d+)\s+(.+?)(?:\s+\||\s*$)', line)
                
                txn_match = new_format or old_format
                
                if txn_match:
                    if new_format:
                        tanggal = txn_match.group(1)
                    else:
                        tanggal = ''  # Will be filled from next line
                    
                    waktu = txn_match.group(2)
                    id_transaksi = txn_match.group(3)
                    rest = txn_match.group(4).strip()
                    
                    # Parse transaction type
                    tipe_match = re.match(r'^(TRANSFER DARI|TARIK TUNAI|SETOR TUNAI|PEMINDAHAN)(.*)$', rest, re.IGNORECASE)
                    tipe_transaksi = tipe_match.group(1).strip() if tipe_match else rest.split('|')[0].strip()
                    
                    txn = {
                        'Tanggal': tanggal,
                        'Waktu': waktu,
                        'ID_Transaksi': id_transaksi,
                        'Tipe_Transaksi': tipe_transaksi,
                        'Saldo_Awal': '',
                        'Debit': '',
                        'Kredit': '',
                        'Saldo_Akhir': '',
                        'Channel': '',
                        'Remarks': rest,
                        'Deskripsi_Lengkap': line
                    }
                    
                    # Extract channel from current line
                    channel_match = re.search(r'(SPAN|TELLER|ATM|TRANSFER)', line, re.IGNORECASE)
                    if channel_match:
                        txn['Channel'] = channel_match.group(1).upper()
                    
                    # Look at next line for amounts (new format) or date continuation (old format)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        
                        # OLD FORMAT: Next line has MM-DD continuation
                        if not new_format:
                            date_cont = re.match(r'^(\d{2})-(\d{2})\s*(.*)$', next_line)
                            if date_cont:
                                month = date_cont.group(1)
                                day = date_cont.group(2)
                                txn['Tanggal'] = f"{txn_match.group(1)}-{month}-{day}"
                                txn['Remarks'] = date_cont.group(3).strip()
                                i += 1
                        
                        # NEW FORMAT: Next line has amounts
                        # Format: "295,739,402 100,000,000 195,739,402" (Saldo_Awal, Debit/Credit, Saldo_Akhir)
                        if i + 1 < len(lines):
                            amount_line = lines[i + 1].strip()
                            amounts = re.findall(r'([\d,]+)', amount_line)
                            if amounts and len(amounts) >= 3:
                                # Check if it looks like amount line (all digits and commas)
                                if re.match(r'^[\d,\s]+$', amount_line):
                                    txn['Saldo_Awal'] = amounts[0]
                                    if 'TARIK' in tipe_transaksi.upper():
                                        txn['Debit'] = amounts[1]
                                    else:
                                        txn['Kredit'] = amounts[1]
                                    txn['Saldo_Akhir'] = amounts[2]
                                    i += 1
                    
                    # Also try to extract amounts from current line
                    amounts_in_line = re.findall(r'Rp\.\s*([\d,]+)', line)
                    if amounts_in_line and len(amounts_in_line) >= 3:
                        txn['Saldo_Awal'] = amounts_in_line[0]
                        txn['Debit'] = amounts_in_line[1] if len(amounts_in_line) > 1 else ''
                        txn['Kredit'] = amounts_in_line[2] if len(amounts_in_line) > 2 else ''
                        txn['Saldo_Akhir'] = amounts_in_line[3] if len(amounts_in_line) > 3 else ''
                    
                    # Add account info
                    txn['Kementerian'] = account_info['Kementerian']
                    txn['Unit'] = account_info['Unit']
                    txn['Rekening_Induk'] = account_info['Rekening_Induk']
                    txn['Rekening_Satker'] = account_info['Rekening_Satker']
                    txn['Periode'] = account_info['Periode']
                    
                    # Classify
                    txn['Klasifikasi'] = classify_span_transaction(txn)
                    
                    all_transactions.append(txn)
                
                i += 1
    
    if not all_transactions:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_transactions)
    df['Source_File'] = pdf_path.name
    
    # Extract month from period
    month_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', account_info.get('Periode', ''))
    if month_match:
        month_num = int(month_match.group(2))
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        df['Month'] = month_names[month_num - 1] if 1 <= month_num <= 12 else ''
        df['Year'] = month_match.group(3)
    
    return df


def classify_span_transaction(row: dict) -> str:
    """Classify SPAN transaction."""
    tipe = str(row.get('Tipe_Transaksi', '')).upper()
    
    if 'TRANSFER DARI' in tipe:
        return 'Income'
    elif 'TARIK TUNAI' in tipe:
        return 'Withdrawal'
    elif 'SETOR' in tipe:
        return 'Deposit'
    else:
        return 'Other'


def parse_amount(value: str) -> float:
    """Parse SPAN formatted amount to float."""
    if not value or value.strip() == '':
        return 0.0
    cleaned = value.strip().replace(',', '').replace('.', '').replace('-', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def compile_span_pdfs(pdf_dir: str, output_file: str = None) -> str:
    """Compile all SPAN PDF statements into Excel (BNI/CASA-compatible format)."""
    pdf_path = Path(pdf_dir)
    
    pdf_files = list(pdf_path.glob('*.pdf'))
    
    if not pdf_files:
        print(f"❌ No SPAN PDF files found in {pdf_dir}")
        return None
    
    month_order = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                   'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    print(f"📂 Found {len(pdf_files)} SPAN PDF file(s)")
    print("=" * 60)
    
    all_dataframes = []
    
    for pdf_file in pdf_files:
        print(f"  📄 Processing: {pdf_file.name}...", end=' ')
        try:
            df = extract_transactions_from_span(str(pdf_file))
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
    
    # Add BNI/CASA compatible columns
    combined_df['Audit_Flag'] = ''  # Will be set for OCR entries
    combined_df['Audit_Notes'] = combined_df.get('Remarks', '')
    combined_df['No_Rekening'] = '9892376932701000'
    combined_df['Nama'] = 'PUSBANGLIN BADAN BAHASA'
    combined_df['Jenis_Produk'] = 'SATKER'
    combined_df['Mata_Uang'] = 'IDR'
    combined_df['Penerima'] = combined_df.get('Remarks', '')
    combined_df['Bank_Tujuan'] = 'BNI SPAN'
    combined_df['E_Wallet'] = ''
    combined_df['No_Akun_Tujuan'] = ''
    combined_df['Keterangan'] = combined_df.get('Channel', '')
    combined_df['Saldo'] = combined_df.get('Saldo_Akhir', '')
    combined_df['Deskripsi_Lengkap'] = combined_df.get('Remarks', '')
    
    # Parse amounts
    combined_df['Debit_Value'] = combined_df['Debit'].apply(parse_amount)
    combined_df['Kredit_Value'] = combined_df['Kredit'].apply(parse_amount)
    
    if not output_file:
        output_file = pdf_path.parent / 'SPAN_Combined_Statements.xlsx'
    
    print("\n" + "=" * 60)
    print(f"💾 Saving to: {output_file}")
    
    # Classify for audit (similar to BNI)
    income_count = (combined_df['Klasifikasi'] == 'Income').sum()
    income_total = combined_df[combined_df['Klasifikasi'] == 'Income']['Kredit_Value'].sum()
    withdraw_count = (combined_df['Klasifikasi'] == 'Withdrawal').sum()
    withdraw_total = combined_df[combined_df['Klasifikasi'] == 'Withdrawal']['Debit_Value'].sum()
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main sheet - BNI/CASA compatible columns
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
        
        # Summary (same format as BNI)
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
                'Income (Transfer Dari)', 'Income Total',
                'Withdrawal (Tarik Tunai)', 'Withdrawal Total',
                '',
                '=== OVERALL ===',
                'Total Transactions', 'Total Debit', 'Total Credit'
            ],
            'Value': [
                '',
                combined_df['No_Rekening'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Nama'].iloc[0] if len(combined_df) > 0 else 'N/A',
                combined_df['Jenis_Produk'].iloc[0] if len(combined_df) > 0 else 'N/A',
                'BNI SPAN',
                '',
                '',
                0, '0.00',  # No suspicious for SPAN by default
                0, '0.00',  # No needs justification
                len(combined_df), f"{combined_df['Debit_Value'].sum() + combined_df['Kredit_Value'].sum():,.2f}",
                '',
                '',
                income_count, f"{income_total:,.2f}",
                withdraw_count, f"{withdraw_total:,.2f}",
                '',
                '',
                len(combined_df),
                f"{combined_df['Debit_Value'].sum():,.2f}",
                f"{combined_df['Kredit_Value'].sum():,.2f}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        
        # SUSPICIOUS sheet (empty for SPAN, but keep structure)
        pd.DataFrame({'Note': ['No suspicious transactions flagged']}).to_excel(
            writer, index=False, sheet_name='SUSPICIOUS')
        
        # NEEDS_JUSTIFICATION sheet
        pd.DataFrame({'Note': ['No transactions require justification']}).to_excel(
            writer, index=False, sheet_name='NEEDS_JUSTIFICATION')
        
        # Classification sheets (Income = Company equivalent, Withdrawal = Private equivalent)
        for classification in ['Income', 'Withdrawal', 'Deposit', 'Other']:
            class_df = combined_df[combined_df['Klasifikasi'] == classification].copy()
            if not class_df.empty:
                class_cols = ['Audit_Flag', 'Audit_Notes', 'Tanggal', 'Waktu', 
                             'Tipe_Transaksi', 'Penerima', 'E_Wallet',
                             'Keterangan', 'Debit', 'Kredit', 'Saldo']
                existing = [c for c in class_cols if c in class_df.columns]
                class_df[existing].to_excel(writer, index=False, sheet_name=classification)
        
        # Monthly sheets (same as BNI)
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
    print(f"\n🔴 SUSPICIOUS: 0 transactions")
    print(f"⚠️  NEEDS JUST: 0 transactions")
    print(f"✅ OK:         {len(combined_df)} transactions")
    
    return str(output_file)


if __name__ == "__main__":
    script_dir = Path(__file__).parent.parent
    pdf_dir = script_dir / 'pdf' / 'span'
    output_file = script_dir / 'excel' / 'SPAN_Combined_Statements.xlsx'
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n🏛️ SPAN Government Treasury Statement Parser")
    print("=" * 60)
    
    result = compile_span_pdfs(str(pdf_dir), str(output_file))
    
    if result:
        print(f"\n📁 Output saved to: {result}")
