"""
Bank Statement Parser - Web Interface

A Streamlit app to parse and export bank statements.
Supports multi-file upload (max 10 files) with validation:
- All files must be same bank type
- All files must be same account number
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import io

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers.cimb import CIMBParser
from src.parsers.bni import BNIParser
from src.classifier import BankClassifier


st.set_page_config(
    page_title="Bank Statement Parser",
    page_icon="🏦",
    layout="wide"
)

# Initialize session state
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None
if 'all_account_info' not in st.session_state:
    st.session_state.all_account_info = []

# Light minimalistic theme colors (Updated to Dark)
bg_color = "#0d1117"
card_color = "#161b22"
text_color = "#c9d1d9"
muted_color = "#8b949e"
income_color = "#3fb950"
expense_color = "#f85149"
border_color = "#30363d"

# Simple CSS for clean look
st.markdown("""
<style>
    /* === GLOBAL TYPOGRAPHY & RESET === */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .stApp {
        background-color: #0d1117; /* GitHub Dark Dimmed Background */
    }

    /* === CLEAN HEADERS === */
    h1 {
        font-weight: 700 !important;
        color: #f0f6fc !important;
        font-size: 2.25rem !important;
        letter-spacing: -0.025em !important;
    }
    
    h2, h3 {
        font-weight: 600 !important;
        color: #c9d1d9 !important;
        letter-spacing: -0.015em !important;
    }
    
    p, li, span {
        color: #8b949e;
    }

    /* === CARDS & CONTAINERS === */
    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.875rem !important; }
    [data-testid="stMetricValue"] { color: #f0f6fc !important; font-weight: 600 !important; }

    /* Expanders (Accordions) */
    .stExpander {
        background-color: #161b22;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
    }
    
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        color: #c9d1d9 !important;
        font-weight: 500;
    }
    
    /* Expander Content */
    .streamlit-expanderContent {
        color: #c9d1d9 !important;
    }

    /* === FILE UPLOADER === */
    [data-testid="stFileUploader"] {
        background-color: #161b22;
        border: 1px dashed #30363d;
        border-radius: 12px;
        padding: 1.5rem;
    }
    
    [data-testid="stFileUploader"] small {
        color: #8b949e !important;
    }

    /* === BUTTONS === */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        border-color: #8b949e !important;
        background-color: #30363d !important;
        color: #ffffff !important;
    }

    /* === TABLES === */
    /* Enhance Streamlit's dark table look */
    .stDataFrame, .stDataEditor {
        border: 1px solid #30363d;
        border-radius: 8px;
        overflow: hidden;
        background: #161b22;
    }

    /* Adjust Streamlit's default padding */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 5rem !important;
    }
    
    /* Hide Streamlit Boilerplate */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: transparent !important; }

</style>
""", unsafe_allow_html=True)

# Plotly theme configuration
plotly_theme = {
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'font': {'color': text_color},
    'xaxis': {'color': text_color, 'gridcolor': '#30363d'},
    'yaxis': {'color': text_color, 'gridcolor': '#30363d'},
}

# Header
st.markdown("<h1 style='color: #f0f6fc; margin-bottom: 0;'>🏦 Bank Statement Parser</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8b949e; margin-top: 0;'>Upload PDF statements to extract & analyze transactions</p>", unsafe_allow_html=True)

st.divider()

# Multi-file uploader
uploaded_files = st.file_uploader(
    "Drop PDF files here (max 10)", 
    type=['pdf'], 
    accept_multiple_files=True
)

with st.sidebar:
    st.header("⚙️ Settings")
    pdf_password = st.text_input(
        "PDF Password", 
        type="password", 
        help="Required for BNI statements. leave empty to use default (02121979)."
    )

if uploaded_files:
    # Limit to 10 files
    if len(uploaded_files) > 10:
        st.warning(f"⚠️ Maximum 10 files allowed. Only first 10 will be processed.")
        uploaded_files = uploaded_files[:10]
    
    st.success(f"📄 Uploaded: {len(uploaded_files)} file(s)")
    
    # Show file list
    with st.expander("📁 Uploaded files", expanded=False):
        for f in uploaded_files:
            st.text(f"• {f.name}")
    
    # Parse button
    if st.button("🚀 Parse Statements", type="primary"):
        classifier = BankClassifier()
        temp_paths = []
        
        # Step 1: Save all files temporarily and classify them
        st.info("📋 Step 1: Validating files...")
        
        file_info = []
        for uploaded_file in uploaded_files:
            temp_path = Path(f"/tmp/{uploaded_file.name}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            temp_paths.append(temp_path)
            
            # Classify
            bank_code, confidence = classifier.identify_with_confidence(str(temp_path))
            file_info.append({
                'name': uploaded_file.name,
                'bank_code': bank_code,
                'confidence': confidence,
                'path': temp_path,
            })
        
        # Step 2: Validate all files are same bank type
        bank_types = set(f['bank_code'] for f in file_info)
        
        if len(bank_types) > 1:
            st.error(f"❌ **Mixed bank types detected!**")
            st.markdown("All files must be from the same bank to merge.")
            
            # Show breakdown
            breakdown = pd.DataFrame([
                {'File': f['name'], 'Detected Bank': f['bank_code'].upper(), 'Confidence': f"{f['confidence']:.0%}"}
                for f in file_info
            ])
            st.dataframe(breakdown, use_container_width=True)
            
            # Cleanup
            for p in temp_paths:
                if p.exists():
                    p.unlink()
            st.stop()
        
        bank_code = list(bank_types)[0]
        st.success(f"✅ All files are **{bank_code.upper()}** format")
        
        # Check if parser exists
        if bank_code not in ["cimb", "bni"]:
            st.error(f"❌ Parser for {bank_code.upper()} not implemented yet!")
            for p in temp_paths:
                if p.exists():
                    p.unlink()
            st.stop()
        
        # Step 3: Parse all files and extract account info
        st.info("📋 Step 2: Extracting account information...")
        
        all_dfs = []
        all_account_info = []
        account_numbers = set()
        
        progress_bar = st.progress(0)
        
        for idx, info in enumerate(file_info):
            try:
                if bank_code == 'bni':
                    parser = BNIParser(password=pdf_password if pdf_password else None)
                else:
                    parser = CIMBParser()
                transactions = parser.parse(str(info['path']))
                account_info = parser.account_info
                
                # Track account number
                account_numbers.add(account_info.account_number)
                
                # Set source_file
                for txn in transactions:
                    txn.source_file = info['name']
                
                # Get DataFrame
                df = parser.to_dataframe()
                df.insert(0, 'account_number', account_info.account_number)
                df.insert(1, 'account_name', account_info.account_name)
                df.insert(2, 'bank', account_info.bank_name)
                df.insert(3, 'period', account_info.statement_period)
                
                all_dfs.append(df)
                all_account_info.append({
                    'file': info['name'],
                    'bank': account_info.bank_name,
                    'account_number': account_info.account_number,
                    'account_name': account_info.account_name,
                    'period': account_info.statement_period,
                    'transactions': len(transactions),
                })
                
            except Exception as e:
                st.error(f"❌ Error parsing {info['name']}: {e}")
            
            progress_bar.progress((idx + 1) / len(file_info))
        
        # Cleanup temp files
        for p in temp_paths:
            if p.exists():
                p.unlink()
        
        # Step 4: Validate all files are same account
        if len(account_numbers) > 1:
            st.error(f"❌ **Multiple accounts detected!**")
            st.markdown("All files must be from the same account to merge into one export.")
            st.markdown("Please upload statements for one account at a time.")
            
            # Show breakdown
            account_df = pd.DataFrame(all_account_info)
            st.dataframe(account_df[['file', 'account_number', 'account_name', 'period']], use_container_width=True)
            
            # Still store in session but warn user
            st.warning("⚠️ Data is shown below but export may have inconsistent data.")
        else:
            st.success(f"✅ All files are from account **{list(account_numbers)[0]}**")
        
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            # Sort by date and time
            combined_df = combined_df.sort_values(['date', 'time'], ascending=[True, True]).reset_index(drop=True)
            
            # Auto-predict sub-categories
            def predict_subcategory(row):
                text = f"{row.get('description', '')} {row.get('notes', '')} {row.get('counterparty', '')}".lower()
                txn_type = row.get('type', '')
                
                income_patterns = {
                    'salary': ['gaji', 'salary', 'payroll', 'thr', 'bonus'],
                    'business_income': ['pembayaran', 'payment from', 'invoice', 'client', 'project'],
                    'freelance': ['freelance', 'jasa', 'fee', 'honorarium'],
                    'investment_return': ['dividen', 'dividend', 'bunga deposito', 'return', 'profit'],
                    'refund': ['refund', 'pengembalian', 'cashback', 'reimburse'],
                    'gift_received': ['hadiah', 'gift', 'kado', 'ultah', 'birthday'],
                    'family_support': ['mama', 'papa', 'ibu', 'bapak', 'ortu'],
                    'loan_received': ['pinjaman', 'loan', 'hutang'],
                }
                spending_patterns = {
                    'electricity': ['pln', 'listrik', 'token'],
                    'water': ['pdam', 'air bersih'],
                    'internet': ['indihome', 'biznet', 'firstmedia', 'wifi', 'internet'],
                    'phone': ['telkomsel', 'xl', 'indosat', 'pulsa', 'paket data'],
                    'insurance': ['asuransi', 'bpjs', 'prudential', 'allianz'],
                    'subscription': ['netflix', 'spotify', 'youtube', 'disney'],
                    'groceries': ['supermarket', 'indomaret', 'alfamart', 'giant'],
                    'dining': ['restaurant', 'restoran', 'cafe', 'starbucks', 'mcd', 'kfc', 'warung', 'makan'],
                    'food_delivery': ['gofood', 'grabfood', 'shopeefood'],
                    'ride_hailing': ['gojek', 'grab', 'gocar', 'goride'],
                    'fuel': ['pertamina', 'shell', 'spbu', 'bensin'],
                    'transport': ['mrt', 'lrt', 'krl', 'transjakarta', 'tol', 'parkir'],
                    'travel': ['hotel', 'traveloka', 'tiket', 'pesawat', 'garuda', 'lion'],
                    'online_shopping': ['shopee', 'tokopedia', 'lazada', 'blibli'],
                    'shopping': ['mall', 'uniqlo', 'zara', 'nike'],
                    'ewallet_topup': ['top up', 'topup', 'isi saldo', 'dana', 'ovo', 'gopay'],
                    'healthcare': ['rumah sakit', 'klinik', 'apotek', 'dokter'],
                    'education': ['sekolah', 'universitas', 'kuliah', 'kursus', 'spp'],
                    'entertainment': ['bioskop', 'cinema', 'xxi', 'cgv', 'konser'],
                    'investment': ['investasi', 'saham', 'reksadana', 'crypto', 'bibit'],
                    'loan_payment': ['cicilan', 'kredit', 'angsuran', 'kpr'],
                    'family_support': ['mama', 'papa', 'ibu', 'bapak', 'adik', 'kakak', 'keluarga'],
                    'friend': ['teman', 'kawan', 'patungan'],
                    'rent': ['sewa', 'kost', 'kontrakan', 'apartment'],
                    'charity': ['donasi', 'sedekah', 'zakat', 'infaq'],
                }
                patterns = income_patterns if txn_type == 'credit' else spending_patterns
                for subcat, keywords in patterns.items():
                    for keyword in keywords:
                        if keyword in text:
                            return subcat
                return ''
            
            # Add sub_category column with predictions
            cat_idx = combined_df.columns.get_loc('category')
            predicted = combined_df.apply(predict_subcategory, axis=1)
            combined_df.insert(cat_idx + 1, 'sub_category', predicted)
            
            st.session_state.parsed_data = combined_df
            st.session_state.all_account_info = all_account_info
            st.session_state.validation_passed = len(account_numbers) == 1
    
    # Display results if available
    if st.session_state.parsed_data is not None:
        df = st.session_state.parsed_data
        all_account_info = st.session_state.all_account_info
        
        # Summary by file (collapsible)
        with st.expander("📋 Files Processed", expanded=False):
            summary_df = pd.DataFrame(all_account_info)
            st.dataframe(summary_df, use_container_width=True)
        
        # Overall summary with custom cards
        credits = df[df['type'] == 'credit']['amount'].sum()
        debits = df[df['type'] == 'debit']['amount'].sum()
        net = credits - debits
        
        def format_amount(val):
            if abs(val) >= 1_000_000_000:
                return f"Rp {val/1_000_000_000:.1f}B"
            elif abs(val) >= 1_000_000:
                return f"Rp {val/1_000_000:.1f}M"
            elif abs(val) >= 1_000:
                return f"Rp {val/1_000:.0f}K"
            return f"Rp {val:,.0f}"
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Total Income</h3>
                <div class="value income">{format_amount(credits)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Total Expense</h3>
                <div class="value expense">{format_amount(debits)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            net_class = "net-positive" if net >= 0 else "net-negative"
            net_sign = "+" if net >= 0 else ""
            st.markdown(f"""
            <div class="metric-card">
                <h3>Net Flow</h3>
                <div class="value {net_class}">{net_sign}{format_amount(net)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Transactions</h3>
                <div class="value">{len(df)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Visualization section
        st.subheader("📈 Transaction Flow Visualization")
        
        try:
            import plotly.express as px
            import plotly.graph_objects as go
            
            # Tab layout for different visualizations
            viz_tab1, viz_tab2, viz_tab3 = st.tabs(["💸 Money Flow", "📊 Category Breakdown", "📅 Timeline"])
            
            with viz_tab1:
                # Sankey diagram showing money flow
                # Layout: Income Sub-cats → Income Cats → Account → Expense Cats → Expense Sub-cats
                st.markdown("**Money Flow: Income Sub-categories → Categories → Account → Categories → Expense Sub-categories**")
                
                # Get category totals
                debit_by_cat = df[df['type'] == 'debit'].groupby('category')['amount'].sum().to_dict()
                credit_by_cat = df[df['type'] == 'credit'].groupby('category')['amount'].sum().to_dict()
                
                # Get sub-category totals (combined by sub_category name, not by category)
                income_subcat_data = {}  # {subcat: {cat: amount}}
                expense_subcat_data = {}  # {subcat: {cat: amount}}
                if 'sub_category' in df.columns:
                    # Income sub-categories
                    credit_df = df[df['type'] == 'credit'].copy()
                    # Replace empty sub-categories with "(Uncategorized)"
                    credit_df['sub_category'] = credit_df['sub_category'].fillna('(Uncategorized)')
                    credit_df.loc[credit_df['sub_category'] == '', 'sub_category'] = '(Uncategorized)'
                    
                    for (cat, subcat), group in credit_df.groupby(['category', 'sub_category']):
                        if subcat not in income_subcat_data:
                            income_subcat_data[subcat] = {}
                        income_subcat_data[subcat][cat] = group['amount'].sum()
                    
                    # Expense sub-categories
                    debit_df = df[df['type'] == 'debit'].copy()
                    # Replace empty sub-categories with "(Uncategorized)"
                    debit_df['sub_category'] = debit_df['sub_category'].fillna('(Uncategorized)')
                    debit_df.loc[debit_df['sub_category'] == '', 'sub_category'] = '(Uncategorized)'
                    
                    for (cat, subcat), group in debit_df.groupby(['category', 'sub_category']):
                        if subcat not in expense_subcat_data:
                            expense_subcat_data[subcat] = {}
                        expense_subcat_data[subcat][cat] = group['amount'].sum()
                
                # Calculate totals
                total_credit = sum(credit_by_cat.values()) if credit_by_cat else 1
                total_debit = sum(debit_by_cat.values()) if debit_by_cat else 1
                
                def fmt_amount(val):
                    if val >= 1_000_000_000:
                        return f"Rp {val/1_000_000_000:.1f}B"
                    elif val >= 1_000_000:
                        return f"Rp {val/1_000_000:.1f}M"
                    elif val >= 1_000:
                        return f"Rp {val/1_000:.0f}K"
                    return f"Rp {val:,.0f}"
                
                # Build nodes and track indices
                nodes = []
                node_colors = []
                hover_texts = []
                
                # Layer 0: Income sub-categories (far left, combined)
                income_subcat_indices = {}
                for subcat, cat_amounts in income_subcat_data.items():
                    total = sum(cat_amounts.values())
                    label = f"{subcat.replace('_', ' ').title()}<br>{fmt_amount(total)}"
                    income_subcat_indices[subcat] = len(nodes)
                    nodes.append(label)
                    node_colors.append("#81c784")  # Light green
                    hover_texts.append(f"{subcat.replace('_', ' ').title()}<br>Rp {total:,.0f}")
                
                # Layer 1: Income categories
                credit_cats = list(credit_by_cat.keys())
                credit_cat_indices = {}
                for cat in credit_cats:
                    amt = credit_by_cat[cat]
                    pct = (amt / total_credit) * 100
                    label = f"{cat.replace('_', ' ').title()}<br>{fmt_amount(amt)} ({pct:.0f}%)"
                    credit_cat_indices[cat] = len(nodes)
                    nodes.append(label)
                    node_colors.append("#66bb6a")
                    hover_texts.append(f"{cat.replace('_', ' ').title()}<br>Rp {amt:,.0f}")
                
                # Layer 2: Account node
                account_idx = len(nodes)
                account_label = f"Account<br>In: {fmt_amount(total_credit)}<br>Out: {fmt_amount(total_debit)}"
                nodes.append(account_label)
                node_colors.append("#90a4ae")
                hover_texts.append(f"Account<br>Total In: Rp {total_credit:,.0f}<br>Total Out: Rp {total_debit:,.0f}")
                
                # Layer 3: Expense categories
                debit_cats = list(debit_by_cat.keys())
                debit_cat_indices = {}
                for cat in debit_cats:
                    amt = debit_by_cat[cat]
                    pct = (amt / total_debit) * 100
                    label = f"{cat.replace('_', ' ').title()}<br>{fmt_amount(amt)} ({pct:.0f}%)"
                    debit_cat_indices[cat] = len(nodes)
                    nodes.append(label)
                    node_colors.append("#ef5350")
                    hover_texts.append(f"{cat.replace('_', ' ').title()}<br>Rp {amt:,.0f}")
                
                # Layer 4: Expense sub-categories (far right, combined)
                expense_subcat_indices = {}
                for subcat, cat_amounts in expense_subcat_data.items():
                    total = sum(cat_amounts.values())
                    label = f"{subcat.replace('_', ' ').title()}<br>{fmt_amount(total)}"
                    expense_subcat_indices[subcat] = len(nodes)
                    nodes.append(label)
                    node_colors.append("#ffab91")  # Light orange
                    hover_texts.append(f"{subcat.replace('_', ' ').title()}<br>Rp {total:,.0f}")
                
                # Build links
                sources = []
                targets = []
                values = []
                link_colors = []
                
                # Link: Income sub-cats → Income cats
                for subcat, cat_amounts in income_subcat_data.items():
                    for cat, amt in cat_amounts.items():
                        sources.append(income_subcat_indices[subcat])
                        targets.append(credit_cat_indices[cat])
                        values.append(amt)
                        link_colors.append("rgba(129, 199, 132, 0.4)")
                
                # Link: Income cats → Account
                for cat, amount in credit_by_cat.items():
                    sources.append(credit_cat_indices[cat])
                    targets.append(account_idx)
                    values.append(amount)
                    link_colors.append("rgba(102, 187, 106, 0.4)")
                
                # Link: Account → Expense cats
                for cat, amount in debit_by_cat.items():
                    sources.append(account_idx)
                    targets.append(debit_cat_indices[cat])
                    values.append(amount)
                    link_colors.append("rgba(239, 83, 80, 0.4)")
                
                # Link: Expense cats → Expense sub-cats
                for subcat, cat_amounts in expense_subcat_data.items():
                    for cat, amt in cat_amounts.items():
                        sources.append(debit_cat_indices[cat])
                        targets.append(expense_subcat_indices[subcat])
                        values.append(amt)
                        link_colors.append("rgba(255, 171, 145, 0.5)")
                
                if sources:
                    # Calculate x positions for 5 layers
                    has_income_subcat = bool(income_subcat_data)
                    has_expense_subcat = bool(expense_subcat_data)
                    
                    x_positions = []
                    # Income sub-cats at 0.0
                    for _ in income_subcat_data:
                        x_positions.append(0.0)
                    # Income cats at 0.2 or 0.0
                    for _ in credit_cats:
                        x_positions.append(0.2 if has_income_subcat else 0.0)
                    # Account at center
                    x_positions.append(0.5)
                    # Expense cats at 0.8 or 1.0
                    for _ in debit_cats:
                        x_positions.append(0.8 if has_expense_subcat else 1.0)
                    # Expense sub-cats at 1.0
                    for _ in expense_subcat_data:
                        x_positions.append(1.0)
                    
                    # Calculate spacing
                    max_nodes = max(len(income_subcat_data), len(credit_cats), len(debit_cats), len(expense_subcat_data), 1)
                    pad_value = max(20, min(60, 120 // max_nodes))
                    chart_height = 500 + (max_nodes * 45)
                    
                    fig_sankey = go.Figure(data=[go.Sankey(
                        arrangement='snap',
                        node=dict(
                            pad=pad_value,
                            thickness=22,
                            line=dict(color="white", width=2),
                            label=nodes,
                            color=node_colors,
                            customdata=hover_texts,
                            hovertemplate='%{customdata}<extra></extra>',
                            x=x_positions,
                            y=None
                        ),
                        link=dict(
                            source=sources,
                            target=targets,
                            value=values,
                            color=link_colors,
                            hovertemplate='%{source.label} → %{target.label}<br>Rp %{value:,.0f}<extra></extra>'
                        )
                    )])
                    
                    fig_sankey.update_layout(
                        title_text="",
                        font_size=10,
                        height=chart_height,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=10, r=10, t=20, b=20)
                    )
                    
                    st.plotly_chart(fig_sankey, use_container_width=True)
                    
                    # Legend
                    st.caption("🟢 Income Sub-cats → 🟢 Income Cats → ⚪ Account → 🔴 Expense Cats → 🟠 Expense Sub-cats")
                else:
                    st.info("No transaction data for Sankey diagram")
            
            with viz_tab2:
                # Category breakdown charts
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Outflow by Category (Debits)**")
                    debit_df = df[df['type'] == 'debit'].groupby('category')['amount'].sum().reset_index()
                    if not debit_df.empty:
                        fig_debit = px.pie(
                            debit_df, 
                            values='amount', 
                            names='category',
                            color_discrete_sequence=px.colors.sequential.Reds_r
                        )
                        fig_debit.update_layout(height=400, **plotly_theme)
                        st.plotly_chart(fig_debit, use_container_width=True)
                    else:
                        st.info("No debit transactions")
                
                with col2:
                    st.markdown("**Inflow by Category (Credits)**")
                    credit_df = df[df['type'] == 'credit'].groupby('category')['amount'].sum().reset_index()
                    if not credit_df.empty:
                        fig_credit = px.pie(
                            credit_df, 
                            values='amount', 
                            names='category',
                            color_discrete_sequence=px.colors.sequential.Greens_r
                        )
                        fig_credit.update_layout(height=400, **plotly_theme)
                        st.plotly_chart(fig_credit, use_container_width=True)
                    else:
                        st.info("No credit transactions")
                
                # Bar chart of all categories
                st.markdown("**Transaction Count by Category**")
                cat_counts = df.groupby(['category', 'type']).size().reset_index(name='count')
                fig_bar = px.bar(
                    cat_counts,
                    x='category',
                    y='count',
                    color='type',
                    barmode='group',
                    color_discrete_map={'credit': income_color, 'debit': expense_color}
                )
                fig_bar.update_layout(height=400, **plotly_theme)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with viz_tab3:
                # Timeline of transactions
                st.markdown("**Daily Transaction Volume**")
                
                # Aggregate by date
                daily_df = df.groupby(['date', 'type'])['amount'].sum().reset_index()
                
                fig_timeline = px.bar(
                    daily_df,
                    x='date',
                    y='amount',
                    color='type',
                    barmode='group',
                    color_discrete_map={'credit': income_color, 'debit': expense_color},
                    labels={'amount': 'Amount (Rp)', 'date': 'Date'}
                )
                fig_timeline.update_layout(height=400, **plotly_theme)
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                # Running balance chart
                st.markdown("**Running Balance**")
                df_sorted = df.sort_values(['date', 'time'])
                df_sorted['flow'] = df_sorted.apply(
                    lambda x: x['amount'] if x['type'] == 'credit' else -x['amount'], 
                    axis=1
                )
                df_sorted['cumulative'] = df_sorted['flow'].cumsum()
                
                fig_balance = px.line(
                    df_sorted,
                    x='date',
                    y='cumulative',
                    title='Cumulative Cash Flow',
                    labels={'cumulative': 'Cumulative (Rp)', 'date': 'Date'}
                )
                fig_balance.update_traces(line_color=income_color)
                fig_balance.update_layout(height=400, **plotly_theme)
                st.plotly_chart(fig_balance, use_container_width=True)
        
        except ImportError:
            st.warning("📊 Install plotly for visualizations: `pip install plotly`")
        
        # Data table with editable sub_category
        st.subheader("📊 All Transactions")
        st.markdown("*Sub-categories are auto-predicted. You can edit them in the **sub_category** column.*")
        
        # === FILTERS ===
        st.markdown("##### 🔍 Filters")
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            type_options = ['All', 'credit', 'debit']
            selected_type = st.selectbox("Transaction Type", type_options, index=0)
        
        with filter_col2:
            category_list = ['All'] + sorted(df['category'].dropna().unique().tolist())
            selected_category = st.selectbox("Category", category_list, index=0)
        
        with filter_col3:
            # Include Empty option and dynamically get sub-cats from current data
            if 'sub_category' in df.columns:
                existing_subcats = sorted([s for s in df['sub_category'].dropna().unique().tolist() if s != ''])
                subcat_list = ['All', '(Empty)'] + existing_subcats
            else:
                subcat_list = ['All']
            selected_subcat = st.selectbox("Sub-Category", subcat_list, index=0)
        
        # Apply filters
        filtered_df = df.copy()
        if selected_type != 'All':
            filtered_df = filtered_df[filtered_df['type'] == selected_type]
        if selected_category != 'All':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        if selected_subcat == '(Empty)':
            filtered_df = filtered_df[(filtered_df['sub_category'] == '') | (filtered_df['sub_category'].isna())]
        elif selected_subcat != 'All':
            filtered_df = filtered_df[filtered_df['sub_category'] == selected_subcat]
        
        # Show filter stats
        st.caption(f"Showing {len(filtered_df)} of {len(df)} transactions")
        
        # Available sub-categories for dropdown (combined income + spending)
        income_subcategories = [
            'salary', 'business_income', 'freelance', 'investment_return', 
            'refund', 'gift_received', 'family_support', 'loan_received', 'sale'
        ]
        spending_subcategories = [
            'groceries', 'dining', 'food_delivery', 'coffee',
            'electricity', 'water', 'internet', 'phone', 'insurance', 'subscription',
            'ride_hailing', 'fuel', 'transport', 'travel', 'parking',
            'online_shopping', 'shopping', 'fashion', 'electronics',
            'ewallet_topup', 'games', 'entertainment',
            'healthcare', 'education', 'charity',
            'rent', 'loan_payment', 'credit_card', 'investment', 'savings',
            'family_support', 'friend', 'gift_given',
            'admin_fee', 'transfer_fee'
        ]
        subcategory_options = [''] + sorted(set(income_subcategories + spending_subcategories))
        
        # Editable table using Streamlit's native data_editor
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "type": st.column_config.TextColumn("Type"),
                "sub_category": st.column_config.SelectboxColumn(
                    "Sub Category",
                    options=subcategory_options,
                    help="Select a sub-category"
                ),
                "amount": st.column_config.NumberColumn("Amount", format="Rp %.0f"),
                "date": st.column_config.DateColumn("Date"),
            },
            disabled=[col for col in filtered_df.columns if col != 'sub_category'],
            use_container_width=True,
            num_rows="fixed",
            key="transaction_editor"
        )
        
        # Update session state with edited data
        st.session_state.parsed_data = edited_df
        
        # Show prediction stats
        if 'sub_category' in edited_df.columns:
            filled_count = (edited_df['sub_category'] != '').sum()
            total_count = len(edited_df)
            if filled_count > 0:
                st.info(f"📝 {filled_count}/{total_count} transactions have sub-categories ({filled_count/total_count*100:.0f}%)")
        
        # Download buttons
        st.markdown("---")
        
        if not st.session_state.get('validation_passed', True):
            st.warning("⚠️ Warning: Files contain multiple accounts. Export may have inconsistent data.")
        
        dcol1, dcol2, _ = st.columns([1, 1, 3])
        
        # Use first account info for filename
        first_account = all_account_info[0] if all_account_info else {}
        filename_base = f"{first_account.get('bank', 'bank')}_{first_account.get('account_number', 'statement')}"
        
        with dcol1:
            # Use edited dataframe with sub_category changes
            csv = edited_df.to_csv(index=False)
            st.download_button(
                "📥 CSV",
                csv,
                file_name=f"{filename_base}_transactions.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with dcol2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Summary sheet
                first_info = all_account_info[0] if all_account_info else {}
                summary_data = {
                    'Metric': [
                        'Bank',
                        'Account Number',
                        'Account Name',
                        '',
                        'Total Files Processed',
                        'Total Transactions',
                        'Total Credits',
                        'Total Debits',
                        'Net Flow',
                        '',
                        'Credit Transactions',
                        'Debit Transactions',
                    ],
                    'Value': [
                        first_info.get('bank', ''),
                        first_info.get('account_number', ''),
                        first_info.get('account_name', ''),
                        '',
                        len(all_account_info),
                        len(df),
                        f"Rp {credits:,.0f}",
                        f"Rp {debits:,.0f}",
                        f"Rp {net:,.0f}",
                        '',
                        len(df[df['type'] == 'credit']),
                        len(df[df['type'] == 'debit']),
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Files processed
                pd.DataFrame(all_account_info).to_excel(writer, sheet_name='Files', index=False)
                
                # Category breakdown (using edited data)
                category_counts = edited_df.groupby('category').agg({
                    'amount': ['count', 'sum']
                }).reset_index()
                category_counts.columns = ['Category', 'Count', 'Total Amount']
                category_counts.to_excel(writer, sheet_name='By Category', index=False)
                
                # Transactions (with sub_category edits)
                edited_df.to_excel(writer, sheet_name='Transactions', index=False)
            
            st.download_button(
                "📥 Excel",
                buffer.getvalue(),
                file_name=f"{filename_base}_transactions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    # Clear session state
    st.session_state.parsed_data = None
    st.session_state.all_account_info = []
    
    st.info("👆 Upload PDF bank statements to get started (max 10 files)")
    
    st.subheader("Validation Rules")
    st.markdown("""
    - ✅ All files must be from **same bank** (auto-detected)
    - ✅ All files must be from **same account** (validated after parsing)
    - ⚠️ If validation fails, you'll see a warning before export
    """)
    
    st.subheader("Supported Banks")
    st.markdown("""
    | Bank | Status |
    |------|--------|
    | CIMB Niaga | ✅ Ready |
    | BNI | ✅ Ready |
    | BCA | 🔄 Coming soon |
    | Mandiri | 🔄 Coming soon |
    | BRI | 🔄 Coming soon |
    """)
