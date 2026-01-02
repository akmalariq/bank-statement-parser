# 🤝 Contributing

Thank you for considering contributing to the Bank Statement Parser project!

---

## Quick Start for Contributors

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your feature: `git checkout -b feature/my-feature`
4. **Make changes** and test locally
5. **Commit** with a clear message: `git commit -m "Add: new BCA parser"`
6. **Push** to your fork: `git push origin feature/my-feature`
7. **Open a Pull Request** on GitHub

---

## Development Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/bank-statement-parser.git
cd bank-statement-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run web_app.py
```

---

## Code Style

- **Python:** Follow PEP 8
- **Naming:** Use `snake_case` for functions/variables, `PascalCase` for classes
- **Docstrings:** Add docstrings to functions
- **Comments:** Explain *why*, not *what*

---

## Adding a New Bank Parser

1. Create `parsers/newbank_parser.py`:
```python
import pdfplumber
import pandas as pd

def parse_newbank_pdf(pdf_bytes, password=None):
    """
    Parse NewBank PDF statement.
    
    Args:
        pdf_bytes: PDF file as bytes
        password: Optional PDF password
    
    Returns:
        tuple: (account_info dict, transactions DataFrame)
    """
    account_info = {}
    transactions = []
    
    with pdfplumber.open(pdf_bytes, password=password) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            # Parse logic here...
    
    df = pd.DataFrame(transactions)
    return account_info, df
```

2. Import in `web_app.py`:
```python
from parsers.newbank_parser import parse_newbank_pdf
```

3. Add detection logic:
```python
if 'NEWBANK' in detected_text:
    account_info, df = parse_newbank_pdf(file)
```

---

## Adding Sub-Category Keywords

Edit the `predict_subcategory()` function in `web_app.py`:

```python
# For spending (debit)
if 'netflix' in desc_lower or 'spotify' in desc_lower:
    return 'subscription'

# For income (credit)
if 'dividend' in desc_lower:
    return 'investment_return'
```

---

## Styling Changes

1. Edit `static/theme.css`
2. Use browser DevTools to find the element's selector
3. Add CSS with the `$variable` syntax for theme support:

```css
.stButton button {
    background: $button_bg;
    color: $text_color;
}
```

---

## Testing

### Manual Testing
1. Upload sample PDFs from `samples/`
2. Verify parsing is correct
3. Check all charts render
4. Test dark/light mode
5. Test CSV/Excel export

### Adding Test Files
Place test PDFs in `samples/` with descriptive names:
- `samples/cimb_checking_jan2024.pdf`
- `samples/bni_savings_q1_2024.pdf`

---

## Commit Message Format

```
Type: Short description

Longer description if needed.
```

**Types:**
- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Enhance existing feature
- `Refactor:` Code cleanup (no behavior change)
- `Docs:` Documentation only
- `Style:` CSS/formatting changes

**Examples:**
```
Add: BCA bank parser
Fix: Sankey diagram not showing empty sub-categories
Docs: Add Streamlit crash course
```

---

## Questions?

Open an issue on GitHub or check existing issues for similar questions.
