# Sprint 6 - Hotel Analytics Dashboard

This README describes the setup and execution steps for Sprint 6, including how to create a Python virtual environment and run the Streamlit dashboard.

## Prerequisites

- Python 3.11 (or compatible Python 3.x)
- Git (optional, for repository checkout)
- ODBC Driver 17 for SQL Server installed
- Access to the SQL Server instance used by the dashboard

## Project Layout

- `dashboard/dashboard.py` - Streamlit dashboard application
- `dashboard/requirements.txt` - Python dependencies for the dashboard
- `SprintDocumentation.md` - Sprint 6 documentation and notes

## Setup Steps

1. Open a terminal in the repository root directory.

2. Create a Python virtual environment in the project root:
   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install the dashboard dependencies:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r "Sprint6-Deliverables\dashboard\requirements.txt"
   ```

## Run the Streamlit Dashboard

1. Change to the dashboard folder:
   ```powershell
   cd "Sprint6-Deliverables\dashboard"
   ```

2. Start the Streamlit dashboard:
   ```powershell
   python -m streamlit run dashboard.py
   ```

3. Open the displayed local URL in your browser (typically `http://localhost:8501`).

### Optional: Run on a specific port

```powershell
python -m streamlit run dashboard.py --server.headless true --server.port 8502
```

## Notes

- The dashboard connects to a SQL Server data warehouse using `pyodbc`.
- Connection details are configured inside `Sprint6-Deliverables\dashboard\dashboard.py`.
- If you do not have access to the configured database, update the connection values in `dashboard.py` or use a local test database.

## Troubleshooting

- If `pyodbc` installation fails, verify that the ODBC Driver 17 for SQL Server is installed.
- If Streamlit does not start, ensure the virtual environment is activated and dependencies are installed.
- If the dashboard cannot connect to the database, check network access and SQL Server credentials.
