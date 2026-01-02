# Project Recap: Bank Statement Parser

## 🎯 Objective
Build a Python-based tool to parse PDF bank statements (CIMB, BNI, etc.) into structured Excel/CSV data for personal finance analysis.

## 🏗️ Architecture
The project uses a **Streamlit** frontend (`web_app.py`) and a modular backend in `src/`.

### Key Components
- **`web_app.py`**: The main entry point.
  - **Dark Mode**: Implemented a professional "GitHub Dark" theme using custom CSS injection. Includes sidebar settings.
  - **No AgGrid**: Reverted to native `st.data_editor` for simplicity and better stability.
  - **Password Handling**: Added a sidebar text input for PDF passwords (required for BNI).

- **`src/parsers/`**:
  - **`base.py`**: Abstract base class defining the `parse()` interface.
  - **`cimb.py`**: Production-ready parser for CIMB Niaga statements.
  - **`bni.py`**: **[NEW]** Wrapper class that integrates the logic from `parsers/bni_parser.py` into the standard interface.

- **`src/classifier.py`**:
  - Automatically identifies bank type from PDF content.
  - **[UPDATED]** Robustly handles BNI files by checking filenames (`BNI_*.pdf`) if password protection prevents reading text. Default BNI password: `02121979`.

- **`src/models/transaction.py`**:
  - Standard `Transaction` data class used by all parsers.

## ✅ Recent Accomplishments
1.  **Refined UI**: Switched from a buggy light/dark toggle to a permanent, professional **Dark Theme**.
2.  **BNI Integration**: Fully implemented BNI parsing support.
    - Created `src/parsers/bni.py`.
    - Updated `web_app.py` to allow BNI uploads and ask for passwords.
    - Verified with sample files in `samples/bni/`.
3.  **Simplified Stack**: Removed `streamlit-aggrid` dependency to reduce complexity.

## 📁 File Structure
```text
.
├── web_app.py             # Main Streamlit App
├── src/
│   ├── classifier.py      # Bank detection logic
│   ├── models/
│   │   └── transaction.py # Data models
│   └── parsers/
│       ├── base.py        # Base parser class
│       ├── cimb.py        # CIMB implementation
│       └── bni.py         # BNI implementation (Wrapper)
├── parsers/
│   └── bni_parser.py      # Original BNI logic (used by src/parsers/bni.py)
└── samples/               # PDF samples for testing
```

## 🚀 Next Steps / Backlog
- **Add More Banks**: BCA, Mandiri, and BRI are listed as "Coming Soon".
- **Visualizations**: Add spending charts (currently placeholder or basic).
- **UI Framework**: Consider migrating to **Reflex** or **React+FastAPI** if Streamlit limits become too restrictive.
- **Testing**: Add unit tests for the new `BNIParser` class.
