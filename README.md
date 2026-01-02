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

### 🔍 Fund Flow Visualization
- Visualize money flow with interactive Sankey diagrams
- Break down income and expenses by category

### 📊 Web Dashboard
- **Dark Mode**: Professional, eye-friendly interface
- **Interactive Tables**: Edit categories and sub-categories
- **Data Export**: Download clean Excel/CSV reports

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
streamlit run web_app.py
```

## 📁 Project Structure

```
bank-statement-parser/
├── web_app.py             # 🚦 MAIN ENTRY POINT
├── src/                   # 🧠 Core Logic
│   ├── classifier.py      # Bank Detection
│   ├── parsers/           # 📄 Bank Parser Implementations
│   │   ├── base.py
│   │   ├── cimb.py
│   │   ├── bni.py
│   │   └── bni_impl.py
│   └── models/
│       └── transaction.py
└── samples/               # 📂 PDF Samples for testing
```

## 📊 Output

### Excel Export
Each parser generates an Excel file with:
- `All_Transactions` - Complete transaction data
- `Summary` - Account info & statistics
- `SUSPICIOUS` - Flagged transactions
- Monthly breakdown sheets

### Fund Flow Analysis
- Visualize money flow with Sankey diagrams
- Track transactions across accounts

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
