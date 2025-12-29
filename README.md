# 🏦 Bank Statement Parser

A comprehensive PDF bank statement parser and fund lineage audit tool for Indonesian banks. Extracts transaction data from multiple bank formats and traces fund movements across accounts.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

## ✨ Features

### 📄 Multi-Bank PDF Parsing
| Bank | Format | Features |
|------|--------|----------|
| **CIMB/OCTO** | CASA statements | Full transaction extraction |
| **BNI** | Personal statements | Password-protected PDF support |
| **SPAN** | Government treasury | Treasury fund tracking |

### 🔍 Fund Lineage Tracing
```
SPAN (Govt) → BNI (Personal) → CASA (CIMB)
    ↓              ↓              ↓
 TARIK TUNAI   SETOR TUNAI    BI-FAST
```

### 🤖 AI-Powered Analysis
- Gemini AI chatbot for data Q&A
- Suspicious transaction detection
- Pattern analysis & alerts

### 📊 Web Dashboard
- Interactive Sankey diagrams
- Monthly trend charts
- Data explorer with filters

## 🛠️ Tech Stack

![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![pdfplumber](https://img.shields.io/badge/pdfplumber-PDF%20Parsing-blue?style=flat-square)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![OpenPyXL](https://img.shields.io/badge/OpenPyXL-Excel-217346?style=flat-square)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/akmalariq/bank-statement-parser.git
cd bank-statement-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the web dashboard
streamlit run app.py
```

## 📁 Project Structure

```
bank-statement-parser/
├── parsers/
│   ├── casa_parser.py     # CIMB/OCTO parser
│   ├── bni_parser.py      # BNI parser
│   └── span_parser.py     # Government SPAN parser
├── app.py                 # Streamlit dashboard
├── audit.py               # CLI audit script
├── run_all.py             # Run all parsers
└── requirements.txt
```

## 📊 Output

### Excel Export
Each parser generates an Excel file with:
- `All_Transactions` - Complete transaction data
- `Summary` - Account info & statistics
- `SUSPICIOUS` - Flagged transactions
- Monthly breakdown sheets

### Fund Flow Analysis
```
SPAN (Govt)          →    BNI (Personal)    →    CASA (CIMB)
TARIK TUNAI              SETOR TUNAI             BI-FAST
33 txns                  80 txns                 54 txns
Rp 2.6B                  Rp 3.8B                 Rp 3.3B
```

## 🔮 Roadmap

- [ ] CLI tool with Click
- [ ] Docker support
- [ ] LangChain RAG for document Q&A
- [ ] Additional bank format support

## 📝 License

MIT License - feel free to use for personal or commercial projects.

## 👨‍💻 Author

**Akmal Ariq** - Data Engineer | Aspiring AI Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/akmalariq/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/akmalariq)
