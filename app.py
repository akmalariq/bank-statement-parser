"""
Fund Lineage Audit Dashboard with AI Chat
A Streamlit web application with Google login and Gemini AI chatbot.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import google.generativeai as genai
import json

# Page config
st.set_page_config(
    page_title="Fund Lineage Audit",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f4e79;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .flow-box {
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
    .span-box { background: #fff2cc; color: #7f6000; }
    .bni-box { background: #deebf7; color: #1f4e79; }
    .casa-box { background: #e2efda; color: #375623; }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background: #e3f2fd;
        margin-left: 20%;
    }
    .ai-message {
        background: #f5f5f5;
        margin-right: 20%;
    }
    .login-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        max-width: 500px;
        margin: 2rem auto;
    }
</style>
""", unsafe_allow_html=True)


def parse_amount(val) -> float:
    """Parse amount to float."""
    if pd.isna(val):
        return 0.0
    try:
        return abs(float(str(val).replace(',', '').replace('-', '').strip() or 0))
    except:
        return 0.0


def load_data():
    """Load all statement data."""
    excel_dir = Path('excel')
    data = {}
    
    files = {
        'CASA': 'CASA_Combined_Statements.xlsx',
        'BNI': 'BNI_Combined_Statements.xlsx',
        'SPAN': 'SPAN_Combined_Statements.xlsx'
    }
    
    for name, filename in files.items():
        filepath = excel_dir / filename
        if filepath.exists():
            data[name] = pd.read_excel(filepath, sheet_name='All_Transactions')
        else:
            data[name] = pd.DataFrame()
    
    return data


def analyze_fund_lineage(data: dict) -> dict:
    """Analyze fund flow between accounts."""
    results = {
        'span_withdrawals': {'count': 0, 'total': 0},
        'bni_deposits': {'count': 0, 'total': 0},
        'bni_to_casa': {'count': 0, 'total': 0}
    }
    
    span = data.get('SPAN', pd.DataFrame())
    if not span.empty and 'Tipe_Transaksi' in span.columns:
        withdrawals = span[span['Tipe_Transaksi'].str.contains('TARIK', na=False, case=False)]
        if not withdrawals.empty:
            results['span_withdrawals']['count'] = len(withdrawals)
            results['span_withdrawals']['total'] = withdrawals['Debit'].apply(parse_amount).sum()
    
    bni = data.get('BNI', pd.DataFrame())
    if not bni.empty and 'Tipe_Transaksi' in bni.columns:
        deposits = bni[bni['Tipe_Transaksi'].str.contains('Setor Tunai', na=False, case=False)]
        if not deposits.empty:
            results['bni_deposits']['count'] = len(deposits)
            results['bni_deposits']['total'] = deposits['Kredit'].apply(parse_amount).sum()
        
        if 'Penerima' in bni.columns:
            transfers = bni[
                (bni['Tipe_Transaksi'].str.contains('Transfer', na=False, case=False)) &
                (bni['Penerima'].str.contains('CIMB|INDAH ROSALIA', na=False, case=False))
            ]
            if not transfers.empty:
                results['bni_to_casa']['count'] = len(transfers)
                results['bni_to_casa']['total'] = transfers['Debit'].apply(parse_amount).sum()
    
    return results


def get_data_summary(data: dict, lineage: dict) -> str:
    """Create a text summary of the data for the AI."""
    summary = """
    FUND LINEAGE AUDIT DATA SUMMARY:
    
    ACCOUNTS:
    - CASA (CIMB): Account 700633117500, Owner: INDAH ROSALIA DESYANTI
    - BNI Personal: Account 223070779, Owner: INDAH ROSALIA DESYANTI  
    - SPAN Government: Account 9892376932701000, Pusbanglin Badan Bahasa
    
    TRANSACTION COUNTS:
    """
    
    for name, df in data.items():
        if not df.empty:
            summary += f"- {name}: {len(df)} transactions\n"
    
    summary += f"""
    FUND FLOW ANALYSIS:
    1. SPAN Withdrawals (TARIK TUNAI): {lineage['span_withdrawals']['count']} transactions, Rp {lineage['span_withdrawals']['total']:,.0f}
    2. BNI Cash Deposits (SETOR TUNAI): {lineage['bni_deposits']['count']} transactions, Rp {lineage['bni_deposits']['total']:,.0f}
    3. BNI to CASA Transfers: {lineage['bni_to_casa']['count']} transactions, Rp {lineage['bni_to_casa']['total']:,.0f}
    
    FUND FLOW PATTERN:
    The data shows a pattern of funds moving from government SPAN account → BNI personal account → CASA (CIMB) account.
    - Government funds are withdrawn via TARIK TUNAI (teller)
    - Cash is deposited to BNI personal account
    - Funds are then transferred to CASA via BI-FAST
    """
    
    # Add some transaction details
    bni = data.get('BNI', pd.DataFrame())
    if not bni.empty:
        bni['Debit_Val'] = bni['Debit'].apply(parse_amount)
        bni['Kredit_Val'] = bni['Kredit'].apply(parse_amount)
        
        summary += f"""
    BNI ACCOUNT STATISTICS:
    - Total Debit: Rp {bni['Debit_Val'].sum():,.0f}
    - Total Credit: Rp {bni['Kredit_Val'].sum():,.0f}
    - Months covered: {', '.join(bni['Month'].dropna().unique()) if 'Month' in bni.columns else 'N/A'}
        """
    
    return summary


def chat_with_gemini(api_key: str, messages: list, data_context: str) -> str:
    """Send message to Gemini and get response."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Build conversation with context
        system_prompt = f"""You are a helpful financial audit assistant analyzing bank transaction data. 
        You have access to the following data:
        
        {data_context}
        
        Answer questions about this data helpfully and accurately. If asked about specific transactions,
        provide insights based on the patterns you can see. Focus on fund lineage, suspicious patterns,
        and audit observations.
        
        Be concise but thorough. Use Rupiah (Rp) for currency amounts.
        """
        
        # Build chat history
        chat_history = [{"role": "user", "parts": [system_prompt]}, 
                        {"role": "model", "parts": ["I understand. I'm ready to help you analyze the fund lineage and transaction data. What would you like to know?"]}]
        
        for msg in messages[:-1]:  # All except last
            chat_history.append({"role": msg["role"], "parts": [msg["content"]]})
        
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(messages[-1]["content"])
        
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


def show_login_page():
    """Show the login/API key entry page."""
    st.markdown('<h1 class="main-header">💰 Fund Lineage Audit</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Transaction Analysis</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-box">
            <h2>🔐 Welcome!</h2>
            <p>To use the AI chat feature, please enter your Gemini API key.</p>
            <p style="font-size: 0.9rem; opacity: 0.9;">
                Get your free API key at:<br>
                <a href="https://aistudio.google.com/apikey" target="_blank" style="color: #fff;">
                    aistudio.google.com/apikey
                </a>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("")
        
        api_key = st.text_input(
            "Enter your Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Get your free API key from Google AI Studio"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🚀 Start with AI Chat", use_container_width=True, type="primary"):
                if api_key and api_key.startswith("AIza"):
                    st.session_state['gemini_api_key'] = api_key
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("Please enter a valid Gemini API key (starts with 'AIza')")
        
        with col_b:
            if st.button("👀 View Demo Only", use_container_width=True):
                st.session_state['logged_in'] = True
                st.session_state['demo_mode'] = True
                st.rerun()
        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #888; font-size: 0.9rem;">
            <p>🔒 Your API key is stored only in your session and never saved.</p>
            <p>The free tier includes 60 queries per minute.</p>
        </div>
        """, unsafe_allow_html=True)


def show_main_dashboard():
    """Show the main dashboard with AI chat."""
    # Load data
    data = load_data()
    lineage = analyze_fund_lineage(data)
    data_context = get_data_summary(data, lineage)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 👤 Session")
        if st.session_state.get('demo_mode'):
            st.info("Demo Mode (AI Chat disabled)")
        else:
            st.success("✓ AI Chat Enabled")
        
        if st.button("🚪 Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Data Summary")
        for name, df in data.items():
            if not df.empty:
                st.metric(f"{name}", f"{len(df)} txns")
        
        st.markdown("---")
        st.markdown("### 🔗 Navigation")
        page = st.radio("Go to", ["Dashboard", "AI Chat", "Data Explorer"])
    
    # Header
    st.markdown('<h1 class="main-header">💰 Fund Lineage Audit</h1>', unsafe_allow_html=True)
    
    if page == "Dashboard":
        show_dashboard(data, lineage)
    elif page == "AI Chat":
        show_chat(data_context)
    else:
        show_data_explorer(data)


def show_dashboard(data: dict, lineage: dict):
    """Show the main dashboard."""
    st.markdown("### 📈 Fund Flow Overview")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = sum(len(df) for df in data.values() if not df.empty)
        st.metric("Total Transactions", f"{total:,}")
    
    with col2:
        st.metric("SPAN Withdrawals", f"{lineage['span_withdrawals']['count']}", 
                  f"Rp {lineage['span_withdrawals']['total']/1e9:.2f}B")
    
    with col3:
        st.metric("BNI Cash Deposits", f"{lineage['bni_deposits']['count']}", 
                  f"Rp {lineage['bni_deposits']['total']/1e9:.2f}B")
    
    with col4:
        st.metric("BNI→CASA Transfers", f"{lineage['bni_to_casa']['count']}", 
                  f"Rp {lineage['bni_to_casa']['total']/1e9:.2f}B")
    
    st.markdown("---")
    
    # Flow diagram
    st.markdown("### 🔄 Fund Flow Diagram")
    
    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 2])
    
    with col1:
        st.markdown("""<div class="flow-box span-box">
            <h4>🏛️ SPAN (Govt)</h4>
            <small>TARIK TUNAI</small>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h2 style='text-align:center;'>➡️</h2>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("""<div class="flow-box bni-box">
            <h4>🏦 BNI Personal</h4>
            <small>SETOR TUNAI</small>
        </div>""", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<h2 style='text-align:center;'>➡️</h2>", unsafe_allow_html=True)
    
    with col5:
        st.markdown("""<div class="flow-box casa-box">
            <h4>💳 CASA (CIMB)</h4>
            <small>BI-FAST</small>
        </div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sankey chart
    st.markdown("### 📊 Fund Flow Visualization")
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, thickness=20,
            line=dict(color="black", width=0.5),
            label=["SPAN (Govt)", "Cash", "BNI Personal", "CASA (CIMB)"],
            color=["#fff2cc", "#d5d5d5", "#deebf7", "#e2efda"]
        ),
        link=dict(
            source=[0, 1, 2],
            target=[1, 2, 3],
            value=[
                lineage['span_withdrawals']['total'] / 1e6,
                lineage['bni_deposits']['total'] / 1e6,
                lineage['bni_to_casa']['total'] / 1e6
            ],
            color=["rgba(255,242,204,0.5)", "rgba(222,235,247,0.5)", "rgba(226,239,218,0.5)"]
        )
    )])
    fig.update_layout(title_text="Fund Flow (Millions Rp)", font_size=12, height=400)
    st.plotly_chart(fig, use_container_width=True)


def show_chat(data_context: str):
    """Show the AI chat interface."""
    st.markdown("### 🤖 AI Audit Assistant")
    
    if st.session_state.get('demo_mode'):
        st.warning("⚠️ AI Chat is disabled in demo mode. Please login with your Gemini API key to enable.")
        st.markdown("""
        **Sample questions you could ask:**
        - What is the total amount of fund movements?
        - How many suspicious transactions are there?
        - Explain the fund flow pattern
        - What are the largest cash deposits?
        """)
        return
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about the transaction data..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                api_key = st.session_state.get('gemini_api_key', '')
                response = chat_with_gemini(api_key, st.session_state.messages, data_context)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "model", "content": response})
    
    # Suggested questions
    st.markdown("---")
    st.markdown("**💡 Suggested Questions:**")
    
    suggestions = [
        "What is the total fund movement from SPAN to CASA?",
        "Are there any suspicious patterns in the transactions?",
        "Summarize the fund lineage findings",
        "What are the largest cash deposits in BNI?"
    ]
    
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"sugg_{i}"):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                st.rerun()


def show_data_explorer(data: dict):
    """Show the data explorer."""
    st.markdown("### 🔍 Data Explorer")
    
    account = st.selectbox("Select Account", ["CASA", "BNI", "SPAN"])
    
    if account in data and not data[account].empty:
        df = data[account]
        
        col1, col2 = st.columns(2)
        with col1:
            if 'Month' in df.columns:
                months = ['All'] + list(df['Month'].dropna().unique())
                month_filter = st.selectbox("Month", months)
            else:
                month_filter = 'All'
        
        with col2:
            if 'Klasifikasi' in df.columns:
                classes = ['All'] + list(df['Klasifikasi'].dropna().unique())
                class_filter = st.selectbox("Classification", classes)
            else:
                class_filter = 'All'
        
        filtered = df.copy()
        if month_filter != 'All' and 'Month' in df.columns:
            filtered = filtered[filtered['Month'] == month_filter]
        if class_filter != 'All' and 'Klasifikasi' in df.columns:
            filtered = filtered[filtered['Klasifikasi'] == class_filter]
        
        st.dataframe(filtered, use_container_width=True, height=500)
        
        csv = filtered.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, f"{account}_data.csv", "text/csv")
    else:
        st.info(f"No data available for {account}")


def main():
    """Main app entry point."""
    # Check if logged in
    if not st.session_state.get('logged_in'):
        show_login_page()
    else:
        show_main_dashboard()


if __name__ == "__main__":
    main()
