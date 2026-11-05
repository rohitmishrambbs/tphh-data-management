# TPHH Data Management System

A high-performance local web application designed to import, clean, filter, analyze, and export large Excel databases (300,000+ records) securely on your Windows computer.

---

## 📁 Project Architecture & Folder Guide

- **`data/`**: Central storage for all data files.
  - **`data/raw/`**: Where your original Excel spreadsheets are placed. Your original files are never altered.
  - **`data/processed/`**: High-speed cached copies (stored in `.parquet` format) that allow 300,000+ rows to load in under a second.
  - **`data/exports/`**: Cleaned, filtered spreadsheets and reports exported by the system.
- **`src/`**: The engine and user interface logic.
  - **`src/utils/`**: Helper tools for file handling, caching, and data validation.
  - **`src/components/`**: Modular building blocks for data cleaning, filtering, analytics, and reporting.
- **`requirements.txt`**: List of required software libraries (Streamlit, Polars, etc.).
- **`app.py`**: The main entry point to launch the web dashboard (created in the next step).

---

## 🛠️ Technology Stack

1. **Python 3.14**: The programming foundation installed on your system.
2. **Streamlit**: Creates the interactive web application interface right in your browser.
3. **Polars**: An ultra-fast, multi-threaded data engine (written in Rust) capable of filtering and transforming 300,000+ rows in milliseconds.
4. **FastExcel / Calamine**: High-speed Excel parsing engine for rapid importing of large spreadsheets.
5. **Plotly**: Creates interactive charts and data visualizations.

