# Implementation Plan: Flask + HTMX Frontend

**Goal**: Create a lightweight, fast frontend for the parser using **Flask** and **HTMX**.
**Why HTMX?**: It allows dynamic page updates (like "SPA" feel) without writing complex JavaScript or needing Node.js.
**Styling**: We will use **TailwindCSS** (via CDN) to keep the UI clean and professional (Shadcn-like aesthetics).

## 🏗️ Architecture

- **Backend**: Flask (`flask_app/app.py`)
  - Serves HTML templates.
  - API endpoints return **HTML fragments** (not JSON) for HTMX to swap.
- **Frontend**: 
  - **HTMX**: Handles file upload interactions and partial page reloads.
  - **Alpine.js**: (Optional) For simple UI state (e.g. dropdowns).
  - **TailwindCSS**: For specific styling.
- **Core Logic**: Reuses `src/` modules (Parsers, Classifier).

## 🎨 Design (Single Page)
1.  **Header**: "Bank Statement Parser".
2.  **Upload Zone**: Drag & Drop area.
    - `hx-post="/parse"`: Sends file immediately on drop or selection.
3.  **Result Area**: Initially empty.
    - Swapped via HTMX with the table of transactions after parsing.
4.  **Export Buttons**: Appear after parsing.

## 📅 Comparison: Streamlit vs HTMX
| Feature | Streamlit (`web_app.py`) | Flask + HTMX (`flask_app/`) |
| :--- | :--- | :--- |
| **Updates** | Reruns entire script | Updates only specific DIVs |
| **Control** | Limited CSS/Layout | Full HTML/CSS control |
| **Speed** | Slower (Python reruns) | Fast (Targeted updates) |

## 📅 Implementation Steps

### 1. Setup
- [ ] Create `flask_app/` and `flask_app/templates/`.
- [ ] Install `flask`.

### 2. Backend (`flask_app/app.py`)
- [ ] Initialize Flask.
- [ ] Route `/` (GET): Render main page.
- [ ] Route `/parse` (POST): 
    - Accept `file`.
    - Detect Bank (`src.classifier`).
    - Parse (`src.parsers`).
    - Return `_transactions_table.html` partial.

### 3. Templates
- [ ] `base.html`: standard layout with HTMX/Tailwind scripts.
- [ ] `index.html`: The main container.
- [ ] `_transactions_table.html`: The template for just the data rows.

### 4. Integration
- [ ] Connect `BNIParser` logic (handle password input if needed - maybe simple input field next to upload?).
- [ ] Connect `CIMBParser`.

## 📦 Deliverable
A new folder `flask_app/` that runs concurrently with `web_app.py`. You can choose which UI to use.
