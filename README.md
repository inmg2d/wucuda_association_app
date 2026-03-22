# WUCUDA Association Manager

A user-friendly local web application for managing a development association like WUCUDA.

It includes:
- Branch registration for major cities in Cameroon
- Member registration and annual dues tracking
- Branch annual regulation tracking
- Election planning and candidate registration
- Executive term tracking with expiry alerts
- Annual General Assembly records
- Development projects register and progress updates
- Reports for national level, branch level, finance, elections, AGM, projects, and compliance
- CSV and Excel downloads for reports

## Main rules already configured
- Patron: The King of Babessi
- Annual member due: 2,000 FCFA
- Annual branch regulation: 15,000 FCFA
- Executive term: 3 years
- Major event planning attendance: 1,500 people
- Estimated membership size: 30,000 members

## Files
- `app.py` - Streamlit user interface
- `database.py` - SQLite database and report logic
- `wucuda.db` - SQLite database created automatically when the app starts
- `requirements.txt` - Python dependencies

## How to run

### 1) Create a virtual environment

On Windows:
```powershell
python -m venv venv
venv\Scripts\activate
```

On macOS or Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Start the application
```bash
streamlit run app.py
```

Your browser should open automatically. If it does not, copy the local address shown in the terminal into your browser.

## First use
- The system loads small demo data on the first run so the dashboards and reports are not empty.
- You can immediately replace the demo records with real WUCUDA data.
- The **Settings** page lets you change annual dues, branch regulations, event attendance, and other core values.

## Reports available
- National Summary
- Branch Summary
- Member Compliance
- Branch Compliance
- Finance Transactions
- Projects Report
- Elections Report
- Candidate Results
- Executive Expiry Report
- AGM Report

## Recommended next improvements
- Add login and role-based access for national and branch officers
- Add receipt printing for dues and branch regulations
- Add photo upload for members and candidates
- Add SMS or email reminders for unpaid dues and expiring terms
- Add cloud hosting for access by branches in different cities
