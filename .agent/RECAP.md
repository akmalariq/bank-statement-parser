# 🏦 Bank Statement Parser - Project Recap

**Last Updated:** Jan 2026
**Status:** ✅ Production Ready for CIMB & BNI

## 🎯 Goal
A local, privacy-focused tool to parse PDF bank statements into structured Excel/CSV data for personal finance analysis.

## 🌟 Key Features
- **Multi-Bank Support**:
  - **CIMB Niaga**: Full support (Transfers, QRIS, Bill Payments).
  - **BNI**: **[NEW]** Full support with password handling.
- **Auto-Classification**: Automatically detects bank type from PDF content.
- **Smart Parsing**: Extracts transaction details (counterparty, bank, e-wallet) from messy descriptions.
- **Manual Categories**: UI for tagging transactions with sub-categories.
- **Privacy**: Processing happens locally. No data sent to cloud.

## 🛠️ Tech Stack
- **Language**: Python 3.12+
- **Frontend**: Streamlit (with Custom CSS Dark Mode)
- **PDF Extraction**: `pdfplumber`
- **Data**: `pandas`

## 📊 Current Status
- **Web App**: `web_app.py` is the main entry point.
- **Theme**: Professional Dark Mode (VS Code / GitHub Dimmed style).
- **Parsers**:
  - `src/parsers/cimb.py`: Active.
  - `src/parsers/bni.py`: Active (Wrapper around `parsers/bni_parser.py`).
- **UI Components**: Native `st.data_editor` used for reliable table editing (replaced AgGrid).

## 🚀 How to Run
```bash
source venv/bin/activate
streamlit run web_app.py
```

## 📝 Recent Changes
- **BNI Integration**: Added `BNIParser`, password input in sidebar, and classifier support.
- **UI Overhaul**: Switched to a robust CSS-injected dark theme. Removed buggy light/dark toggles.
- **Code Structure**: Standardized parsers under `src/parsers/`.
