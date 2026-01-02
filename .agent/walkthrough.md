# Project Walkthrough: Bank Statement Parser

## 1. Core Parser Logic (`src/parsers/`)
We have successfully consolidated all parser logic into a clean, modular structure:
- **`src/parsers/base.py`**: The abstract base class defining the interface.
- **`src/parsers/cimb.py`**: The pure-Python implementation for CIMB/OCTO statements.
- **`src/parsers/bni.py`**: The wrapper for the BNI parser, integrating it into the new system.
- **`src/parsers/bni_impl.py`**: The core BNI logic (password handling, text extraction).

## 2. Streamlit Web App (`web_app.py`)
The main interface is a polished Streamlit dashboard:
- **Dark Theme**: Hardcoded professional dark mode (GitHub-dimmed style).
- **Multi-bank Support**: Automatically detects and chooses the right parser.
- **Bank Classifier**: Robustly identifies files by content or filename.
- **Visualization**: Use Plotly for Sankey diagrams and money flow charts.
- **Validation**: Prevents mixing files from different banks/accounts.

## 3. Browser-Only Deployment (`public/index.html`)
**New Feature**: We have enabled "Client-Side Only" deployment using `stlite`.
- **Zero Server Logic**: The app runs entirely in the user's browser using WebAssembly.
- **Privacy**: No files are ever uploaded to a server; parsing happens in RAM.
- **Deployment**: The single file `public/index.html` can be hosted on GitHub Pages or Netlify freely.

### How to Deploy
See `deployment_guide.md` for full instructions. In short:
1. Upload the `public/` folder to GitHub Pages.
2. Share the URL.
3. Users access the full app without any backend setup.

## 4. How to Run Locally
1. **Install**: `pip install -r requirements.txt`
2. **Run**: `streamlit run web_app.py`
3. **Access**: Go to `http://localhost:8501`

## Verification
- **Sample Files**: Tested parsing with `samples/bni/BNI_*.pdf` and `samples/cimb/Statement *.pdf`.
- **Browser Build**: Verified that `public/index.html` loads the Pyodide environment and runs the Python logic successfully.
