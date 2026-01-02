# 🌐 Web App Guide (`web_app.py`)

This document is a deep dive into `web_app.py`, the main Streamlit application file.

---

## File Overview

| Metric | Value |
|--------|-------|
| Total Lines | ~870 |
| Framework | Streamlit |
| Main Purpose | PDF upload, parsing, visualization, export |

---

## Section Breakdown

### 1. Imports & Page Config (Lines 1-55)

```python
import streamlit as st
import pandas as pd
from pathlib import Path
# ... more imports

st.set_page_config(
    page_title="Bank Statement Parser",
    page_icon="🏦",
    layout="wide"
)
```

**Key Points:**
- `st.set_page_config()` must be the **first** Streamlit call
- `layout="wide"` makes the app full-width

---

### 2. Dark Mode Styling (Lines 44-157)

```python
# Simple CSS for professional dark look
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    h1, h2, h3 { color: #f0f6fc !important; }
    /* ... more CSS overrides */
</style>
""", unsafe_allow_html=True)
```

**Design Decision:**
We enforce a **Professional Dark Theme** (GitHub Dimmed style) using injected CSS.
- **Background**: `#0d1117`
- **Cards**: `#161b22`
- **Text**: `#c9d1d9`

This replaces the old toggle system which was causing reload issues.

---

### 3. Sub-Category Prediction (Lines 91-180)

```python
def predict_subcategory(description: str, tx_type: str) -> str:
    desc_lower = description.lower()
    
    if tx_type == 'credit':
        if 'salary' in desc_lower or 'gaji' in desc_lower:
            return 'salary'
        # ... more patterns
    else:  # debit
        if 'grab' in desc_lower or 'gojek' in desc_lower:
            return 'ride_hailing'
        # ... more patterns
    
    return ''  # No match
```

**Purpose:** Automatically categorize transactions based on keywords in the description.

---

### 4. PDF Upload & Parsing (Lines 180-380)

```python
uploaded_files = st.file_uploader(
    "Upload Bank Statements",
    type=["pdf"],
    accept_multiple_files=True
)

if st.button("Parse Statements"):
    for file in uploaded_files:
        # Detect bank type and call appropriate parser
        if 'CIMB' in detected_bank:
            account_info, df = parse_casa_pdf(file)
        elif 'BNI' in detected_bank:
            account_info, df = parse_bni_pdf(file, password)
        # ... combine all DataFrames
    
    st.session_state.parsed_data = combined_df
```

**Flow:**
1. User uploads PDFs
2. Click "Parse" button
3. Loop through files, detect bank, call parser
4. Combine all results into one DataFrame
5. Store in session state

---

### 5. Sankey Diagram (Lines 380-580)

The Sankey shows money flow across 5 layers:

```
Income Sub-cats → Income Cats → Account → Expense Cats → Expense Sub-cats
```

```python
fig = go.Figure(go.Sankey(
    node=dict(
        label=nodes,
        color=node_colors,
    ),
    link=dict(
        source=link_sources,
        target=link_targets,
        value=link_values,
    )
))
st.plotly_chart(fig)
```

---

### 6. Other Charts (Lines 580-670)

- **Pie Charts:** Income/Expense by category
- **Bar Chart:** Monthly income vs expenses
- **Timeline:** Transactions over time
- **Balance Chart:** Cumulative cash flow

All charts use Plotly (`px.pie`, `px.bar`, `px.line`).

---

### 7. Transaction Table (Lines 670-760) ⭐

This is the main data display with filters.

#### Filters
```python
selected_type = st.selectbox("Transaction Type", ['All', 'credit', 'debit'])
selected_category = st.selectbox("Category", ['All'] + category_list)
selected_subcat = st.selectbox("Sub-Category", ['All', '(Empty)'] + subcat_list)

# Apply filters
filtered_df = df.copy()
if selected_type != 'All':
    filtered_df = filtered_df[filtered_df['type'] == selected_type]
```

#### Editable Table
```python
edited_df = st.data_editor(
    filtered_df,
    column_config={
        "sub_category": st.column_config.SelectboxColumn(
            "Sub Category",
            options=subcategory_options
        )
    },
    disabled=[col for col in df.columns if col != 'sub_category']
)
```

---

### 8. Export Buttons (Lines 760-870)

```python
# CSV
csv = edited_df.to_csv(index=False)
st.download_button("📥 CSV", csv, "transactions.csv", "text/csv")

# Excel
buffer = io.BytesIO()
with pd.ExcelWriter(buffer) as writer:
    edited_df.to_excel(writer, sheet_name="Transactions")
st.download_button("📥 Excel", buffer, "transactions.xlsx")
```

---

## Common Modifications

### Add a new filter
1. Add `st.selectbox()` in the filters section
2. Add filter logic to the `filtered_df` processing
3. Test with existing data

### Add a new chart
1. Import Plotly: `import plotly.express as px`
2. Create figure: `fig = px.bar(df, x='category', y='amount')`
3. Display: `st.plotly_chart(fig)`

### Change styles
1. Edit `static/theme.css`
2. Use browser DevTools to find the right selector
3. Restart the app to see changes

---

## Tips

1. **Use `st.rerun()`** to force a page refresh after state changes
2. **Wrap slow operations** in `@st.cache_data`
3. **Check terminal** for Python errors that don't show in the browser
4. **Use `st.write(variable)`** for quick debugging
