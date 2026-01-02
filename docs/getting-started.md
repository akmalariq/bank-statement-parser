## 🚀 Getting Started

### Option 1: Use Online (No Installation)
The easiest way to use the parser is via our **Browser-Only App**.
It runs entirely on your device (files are **never** uploaded to a server).
👉 **[Open Bank Parser](https://akmalariq.dev/bank-statement-parser/)**

---

### Option 2: Run Locally (Developer Mode)
Follow these steps if you want to modify the code or run it on your own machine.


## Prerequisites

- **Python 3.9 or higher**
- **pip** (Python package manager)
- A terminal/command prompt

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/akmalariq/bank-statement-parser.git
cd bank-statement-parser
```

### 2. Create a virtual environment
```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Application

### Option A: Web Dashboard (Recommended)
```bash
streamlit run web_app.py
```
Then open http://localhost:8501 in your browser.

### Option B: CLI Tool (Legacy)
Not currently supported in the v2 architecture. Please use the web dashboard.

---

## First Run Checklist

- [ ] Virtual environment is activated (you see `(venv)` in terminal)
- [ ] All packages installed without errors
- [ ] Web app opens in browser
- [ ] You can upload a sample PDF and see parsed data

---

## Common Issues

### `ModuleNotFoundError: No module named 'streamlit'`
**Fix:** Make sure your virtual environment is activated:
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### `streamlit: command not found`
**Fix:** Install Streamlit:
```bash
pip install streamlit
```

### App runs but page is blank
**Fix:** Check the terminal for error messages. Often it is a missing import.

---

## Next Steps

- Read [Architecture Overview](./architecture.md) to understand the code structure
- Check `web_app.py` source code to see how the UI is built
