# ✅ Project Tasks & Backlog

## 🟢 Completed (Recent)
- [x] **BNI Integration**
  - [x] Create `src/parsers/bni.py` wrapper
  - [x] Update `src/classifier.py` for BNI detection
  - [x] Add Password Input to Sidebar
  - [x] Update `web_app.py` logic
- [x] **UI & Theming**
  - [x] Remove buggy toggle
  - [x] Implement professional CSS Dark Theme
  - [x] Switch back to `st.data_editor` from `AgGrid`
  - [x] Fix "Coming Soon" table statuses

## 🟡 In Progress / Next Up
- [ ] **Add More Banks**
  - [ ] BCA (Sample PDFs needed)
  - [ ] Mandiri (Sample PDFs needed)
  - [ ] BRI (Sample PDFs needed)
- [ ] **Visualization Dashboard**
  - [ ] Monthly spending bar chart
  - [ ] Category pie chart
  - [ ] Income vs Expense trend line

## 🔴 Backlog (Future)
- [ ] **UI Framework Migration**: Evaluate moving to **Reflex** or **React+FastAPI** for more UI control.
- [ ] **Data Persistence**: Save parsed data to a local SQLite DB instead of just Session State.
- [ ] **Rule-Based Categorization**: Allow users to save rules (e.g., "Always tag 'Grab' as 'Transport'").
- [ ] **Multi-Currency**: Support USD/SGD statements.
