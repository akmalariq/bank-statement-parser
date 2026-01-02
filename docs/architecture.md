# 🏗️ Architecture Guide

## Directory Structure
```text
.
├── web_app.py             # 🚦 MAIN ENTRY POINT (Streamlit)
├── .agent/                # 🤖 AI Context & Docs
├── src/                   # 🧠 Core Logic
│   ├── classifier.py      # Bank Detection (PDF content analysis)
│   ├── parsers/           # 📄 Bank Parser Implementations
│   │   ├── base.py        # Abstract Base Class (Interface)
│   │   ├── cimb.py        # CIMB Implementation
│   │   ├── bni.py         # BNI Implementation (Wrapper)
│   │   └── bni_impl.py    # BNI Core Logic (Implementation)
│   └── models/
│       └── transaction.py # Standardized Data Class
└── samples/               # 📂 PDF Samples for testing
```

## Core Flows

### 1. Bank Detection (`src/classifier.py`)
- Reads first page text.
- Matches keywords (e.g., "CIMB NIAGA", "BNI").
- **Fallback**: Checks filename if PDF is password protected.
- Returns `bank_code` (e.g., `'cimb'`, `'bni'`).

### 2. Transaction Parsing (`src/parsers/`)
- **`BaseBankParser`**: Defines `parse(file) -> List[Transaction]`.
- **`CIMBParser`**: Implements extraction for CIMB.
- **`BNIParser`**: Wrapper that calls `src.parsers.bni_impl.extract_transactions_from_bni` and converts the DataFrame result into standard `Transaction` objects.

### 3. Web UI (`web_app.py`)
- **Flow**: Upload -> Classify -> Select Parser -> Parse -> Edit -> Export.
- **State**: Uses `st.session_state` to persist data between re-runs.
- **Editing**: Uses `st.data_editor` for the main transaction table.
- **Theming**: Injects CSS via `st.markdown('<style>...</style>')`.

## Key Updates (Jan 2026)
- **BNI Support**: added via Wrapper pattern to reuse existing logic.
- **Dark Mode**: Hardcoded CSS theme (inter font, #0d1117 background) to ensure professional look without relying on Streamlit's flaky auto-theme detection.
