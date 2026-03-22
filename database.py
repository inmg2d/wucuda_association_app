from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

DB_PATH = Path(__file__).with_name("wucuda.db")

DEFAULT_SETTINGS = {
    "association_name": "WUCUDA",
    "patron": "The King of Babessi",
    "member_annual_due": "2000",
    "branch_annual_regulation": "15000",
    "executive_term_years": "3",
    "major_event_expected_attendance": "1500",
    "estimated_total_members": "30000",
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    region TEXT,
    contact_person TEXT,
    phone TEXT,
    annual_regulation REAL NOT NULL DEFAULT 15000,
    status TEXT NOT NULL DEFAULT 'Active',
    created_at TEXT NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    membership_no TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    gender TEXT,
    phone TEXT,
    email TEXT,
    occupation TEXT,
    city TEXT,
    branch_id INTEGER,
    joined_on TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active',
    annual_due REAL NOT NULL DEFAULT 2000,
    notes TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS member_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    payment_year INTEGER NOT NULL,
    amount REAL NOT NULL,
    date_paid TEXT NOT NULL,
    payment_type TEXT NOT NULL DEFAULT 'Annual Due',
    method TEXT,
    reference TEXT,
    notes TEXT,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS branch_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL,
    payment_year INTEGER NOT NULL,
    amount REAL NOT NULL,
    date_paid TEXT NOT NULL,
    method TEXT,
    reference TEXT,
    notes TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    level TEXT NOT NULL,
    branch_id INTEGER,
    election_date TEXT NOT NULL,
    venue TEXT,
    expected_attendance INTEGER,
    term_years INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'Planned',
    notes TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    position TEXT NOT NULL,
    manifesto TEXT,
    votes INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Cleared',
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE (election_id, member_id, position)
);

CREATE TABLE IF NOT EXISTS executive_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    branch_id INTEGER,
    office_name TEXT NOT NULL,
    member_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    election_id INTEGER,
    status TEXT NOT NULL DEFAULT 'Serving',
    notes TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agm_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    meeting_date TEXT NOT NULL,
    venue TEXT,
    expected_attendance INTEGER,
    actual_attendance INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT,
    location TEXT,
    branch_id INTEGER,
    budget REAL NOT NULL DEFAULT 0,
    amount_spent REAL NOT NULL DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'Planned',
    sponsor TEXT,
    manager TEXT,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS project_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    update_date TEXT NOT NULL,
    progress_percent INTEGER NOT NULL,
    summary TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_members_branch ON members(branch_id);
CREATE INDEX IF NOT EXISTS idx_member_payments_year ON member_payments(payment_year);
CREATE INDEX IF NOT EXISTS idx_branch_payments_year ON branch_payments(payment_year);
CREATE INDEX IF NOT EXISTS idx_candidates_election ON candidates(election_id);
CREATE INDEX IF NOT EXISTS idx_projects_branch ON projects(branch_id);
CREATE INDEX IF NOT EXISTS idx_executives_end_date ON executive_terms(end_date);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn



def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, str(value)),
            )
        conn.commit()
    seed_demo_data()



def _next_membership_no(conn: sqlite3.Connection) -> str:
    next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM members").fetchone()[0]
    return f"WU-{next_id:05d}"



def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()



def fetch_df(query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)



def get_setting(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return row[0]



def get_settings_dict() -> dict[str, str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}



def save_settings(values: dict[str, Any]) -> None:
    with get_connection() as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
        conn.commit()



def get_branch_options() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, city, annual_regulation, status FROM branches ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]



def get_member_options(active_only: bool = False) -> list[dict[str, Any]]:
    query = (
        "SELECT m.id, m.membership_no, m.full_name, COALESCE(b.name, 'Unassigned') AS branch_name "
        "FROM members m LEFT JOIN branches b ON b.id = m.branch_id"
    )
    params: tuple[Any, ...] = ()
    if active_only:
        query += " WHERE m.status = ?"
        params = ("Active",)
    query += " ORDER BY m.full_name"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]



def get_election_options() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, level, election_date, status FROM elections ORDER BY election_date DESC"
        ).fetchall()
    return [dict(row) for row in rows]



def get_project_options() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, status FROM projects ORDER BY title"
        ).fetchall()
    return [dict(row) for row in rows]



def create_branch(
    name: str,
    city: str,
    region: str,
    contact_person: str,
    phone: str,
    annual_regulation: float,
    status: str,
) -> None:
    execute(
        """
        INSERT INTO branches(name, city, region, contact_person, phone, annual_regulation, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, city, region, contact_person, phone, annual_regulation, status),
    )



def create_member(
    full_name: str,
    gender: str,
    phone: str,
    email: str,
    occupation: str,
    city: str,
    branch_id: int | None,
    joined_on: str,
    status: str,
    annual_due: float,
    notes: str,
) -> str:
    with get_connection() as conn:
        membership_no = _next_membership_no(conn)
        conn.execute(
            """
            INSERT INTO members(
                membership_no, full_name, gender, phone, email, occupation, city,
                branch_id, joined_on, status, annual_due, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                membership_no,
                full_name,
                gender,
                phone,
                email,
                occupation,
                city,
                branch_id,
                joined_on,
                status,
                annual_due,
                notes,
            ),
        )
        conn.commit()
    return membership_no



def record_member_payment(
    member_id: int,
    payment_year: int,
    amount: float,
    date_paid: str,
    payment_type: str,
    method: str,
    reference: str,
    notes: str,
) -> None:
    execute(
        """
        INSERT INTO member_payments(member_id, payment_year, amount, date_paid, payment_type, method, reference, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (member_id, payment_year, amount, date_paid, payment_type, method, reference, notes),
    )



def record_branch_payment(
    branch_id: int,
    payment_year: int,
    amount: float,
    date_paid: str,
    method: str,
    reference: str,
    notes: str,
) -> None:
    execute(
        """
        INSERT INTO branch_payments(branch_id, payment_year, amount, date_paid, method, reference, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (branch_id, payment_year, amount, date_paid, method, reference, notes),
    )



def create_election(
    title: str,
    level: str,
    branch_id: int | None,
    election_date: str,
    venue: str,
    expected_attendance: int,
    term_years: int,
    status: str,
    notes: str,
) -> None:
    execute(
        """
        INSERT INTO elections(title, level, branch_id, election_date, venue, expected_attendance, term_years, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, level, branch_id, election_date, venue, expected_attendance, term_years, status, notes),
    )



def register_candidate(
    election_id: int,
    member_id: int,
    position: str,
    manifesto: str,
    votes: int,
    status: str,
) -> None:
    execute(
        """
        INSERT INTO candidates(election_id, member_id, position, manifesto, votes, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (election_id, member_id, position, manifesto, votes, status),
    )



def create_executive_term(
    level: str,
    branch_id: int | None,
    office_name: str,
    member_id: int,
    start_date: str,
    end_date: str,
    election_id: int | None,
    status: str,
    notes: str,
) -> None:
    execute(
        """
        INSERT INTO executive_terms(level, branch_id, office_name, member_id, start_date, end_date, election_id, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (level, branch_id, office_name, member_id, start_date, end_date, election_id, status, notes),
    )



def create_agm(
    title: str,
    meeting_date: str,
    venue: str,
    expected_attendance: int,
    actual_attendance: int,
    notes: str,
) -> None:
    execute(
        """
        INSERT INTO agm_meetings(title, meeting_date, venue, expected_attendance, actual_attendance, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, meeting_date, venue, expected_attendance, actual_attendance, notes),
    )



def create_project(
    title: str,
    category: str,
    location: str,
    branch_id: int | None,
    budget: float,
    amount_spent: float,
    start_date: str,
    end_date: str,
    status: str,
    sponsor: str,
    manager: str,
    progress_percent: int,
    description: str,
) -> None:
    execute(
        """
        INSERT INTO projects(
            title, category, location, branch_id, budget, amount_spent,
            start_date, end_date, status, sponsor, manager, progress_percent, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            category,
            location,
            branch_id,
            budget,
            amount_spent,
            start_date,
            end_date,
            status,
            sponsor,
            manager,
            progress_percent,
            description,
        ),
    )



def add_project_update(
    project_id: int,
    update_date: str,
    progress_percent: int,
    summary: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO project_updates(project_id, update_date, progress_percent, summary)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, update_date, progress_percent, summary),
        )
        conn.execute(
            "UPDATE projects SET progress_percent = ? WHERE id = ?",
            (progress_percent, project_id),
        )
        conn.commit()



def get_branches_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT id, name AS branch_name, city, region, contact_person, phone,
               annual_regulation, status, created_at
        FROM branches
        ORDER BY name
        """
    )



def get_members_df(branch_id: int | None = None) -> pd.DataFrame:
    query = """
        SELECT m.id, m.membership_no, m.full_name, m.gender, m.phone, m.email,
               m.occupation, m.city, COALESCE(b.name, 'Unassigned') AS branch_name,
               m.joined_on, m.status, m.annual_due, m.notes
        FROM members m
        LEFT JOIN branches b ON b.id = m.branch_id
    """
    params: tuple[Any, ...] = ()
    if branch_id is not None:
        query += " WHERE m.branch_id = ?"
        params = (branch_id,)
    query += " ORDER BY m.full_name"
    return fetch_df(query, params)



def get_member_payments_df(payment_year: int | None = None) -> pd.DataFrame:
    query = """
        SELECT mp.id, mp.payment_year, mp.date_paid, mp.amount, mp.payment_type, mp.method,
               mp.reference, m.membership_no, m.full_name,
               COALESCE(b.name, 'Unassigned') AS branch_name, mp.notes
        FROM member_payments mp
        JOIN members m ON m.id = mp.member_id
        LEFT JOIN branches b ON b.id = m.branch_id
    """
    params: tuple[Any, ...] = ()
    if payment_year is not None:
        query += " WHERE mp.payment_year = ?"
        params = (payment_year,)
    query += " ORDER BY mp.date_paid DESC, m.full_name"
    return fetch_df(query, params)



def get_branch_payments_df(payment_year: int | None = None) -> pd.DataFrame:
    query = """
        SELECT bp.id, bp.payment_year, bp.date_paid, bp.amount, bp.method, bp.reference,
               b.name AS branch_name, b.city, bp.notes
        FROM branch_payments bp
        JOIN branches b ON b.id = bp.branch_id
    """
    params: tuple[Any, ...] = ()
    if payment_year is not None:
        query += " WHERE bp.payment_year = ?"
        params = (payment_year,)
    query += " ORDER BY bp.date_paid DESC, b.name"
    return fetch_df(query, params)



def get_elections_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT e.id, e.title, e.level, COALESCE(b.name, 'National') AS branch_scope,
               e.election_date, e.venue, e.expected_attendance, e.term_years,
               e.status, e.notes,
               (SELECT COUNT(*) FROM candidates c WHERE c.election_id = e.id) AS total_candidates
        FROM elections e
        LEFT JOIN branches b ON b.id = e.branch_id
        ORDER BY e.election_date DESC
        """
    )



def get_candidates_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT c.id, e.title AS election_title, c.position, m.membership_no, m.full_name,
               COALESCE(b.name, 'Unassigned') AS branch_name, c.votes, c.status, c.manifesto
        FROM candidates c
        JOIN elections e ON e.id = c.election_id
        JOIN members m ON m.id = c.member_id
        LEFT JOIN branches b ON b.id = m.branch_id
        ORDER BY e.election_date DESC, c.position, c.votes DESC, m.full_name
        """
    )



def get_executives_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT ex.id, ex.level, COALESCE(b.name, 'National') AS branch_scope,
               ex.office_name, m.membership_no, m.full_name,
               ex.start_date, ex.end_date, ex.status, ex.notes
        FROM executive_terms ex
        JOIN members m ON m.id = ex.member_id
        LEFT JOIN branches b ON b.id = ex.branch_id
        ORDER BY ex.end_date, ex.office_name
        """
    )



def get_agm_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT id, title, meeting_date, venue, expected_attendance, actual_attendance,
               CASE
                   WHEN expected_attendance IS NULL OR expected_attendance = 0 OR actual_attendance IS NULL THEN NULL
                   ELSE ROUND(actual_attendance * 100.0 / expected_attendance, 2)
               END AS attendance_rate_percent,
               notes
        FROM agm_meetings
        ORDER BY meeting_date DESC
        """
    )



def get_projects_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT p.id, p.title, p.category, p.location,
               COALESCE(b.name, 'National') AS supervising_branch,
               p.budget, p.amount_spent,
               CASE
                   WHEN p.budget = 0 THEN 0
                   ELSE ROUND(p.amount_spent * 100.0 / p.budget, 2)
               END AS budget_use_percent,
               p.start_date, p.end_date, p.status, p.sponsor, p.manager,
               p.progress_percent, p.description
        FROM projects p
        LEFT JOIN branches b ON b.id = p.branch_id
        ORDER BY p.status, p.title
        """
    )



def get_project_updates_df() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT u.id, p.title AS project_title, u.update_date, u.progress_percent, u.summary
        FROM project_updates u
        JOIN projects p ON p.id = u.project_id
        ORDER BY u.update_date DESC, p.title
        """
    )



def get_dashboard_metrics(report_year: int) -> dict[str, Any]:
    with get_connection() as conn:
        metrics = {
            "total_branches": conn.execute("SELECT COUNT(*) FROM branches").fetchone()[0],
            "total_members": conn.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            "active_members": conn.execute(
                "SELECT COUNT(*) FROM members WHERE status = 'Active'"
            ).fetchone()[0],
            "members_paid_this_year": conn.execute(
                "SELECT COUNT(DISTINCT member_id) FROM member_payments WHERE payment_year = ?",
                (report_year,),
            ).fetchone()[0],
            "branches_paid_this_year": conn.execute(
                "SELECT COUNT(DISTINCT branch_id) FROM branch_payments WHERE payment_year = ?",
                (report_year,),
            ).fetchone()[0],
            "member_dues_collected": conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM member_payments WHERE payment_year = ?",
                (report_year,),
            ).fetchone()[0],
            "branch_regulations_collected": conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM branch_payments WHERE payment_year = ?",
                (report_year,),
            ).fetchone()[0],
            "total_projects": conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "active_projects": conn.execute(
                "SELECT COUNT(*) FROM projects WHERE status IN ('Active', 'Ongoing')"
            ).fetchone()[0],
            "planned_or_open_elections": conn.execute(
                "SELECT COUNT(*) FROM elections WHERE status IN ('Planned', 'Open')"
            ).fetchone()[0],
            "expiring_executive_terms_180": conn.execute(
                """
                SELECT COUNT(*)
                FROM executive_terms
                WHERE status = 'Serving'
                  AND date(end_date) <= date('now', '+180 day')
                """
            ).fetchone()[0],
        }
    return metrics



def get_branch_summary_report(report_year: int) -> pd.DataFrame:
    return fetch_df(
        """
        SELECT b.name AS branch_name,
               b.city,
               b.region,
               b.annual_regulation,
               (SELECT COUNT(*) FROM members m WHERE m.branch_id = b.id) AS total_members,
               (SELECT COUNT(*) FROM members m WHERE m.branch_id = b.id AND m.status = 'Active') AS active_members,
               (SELECT COUNT(DISTINCT mp.member_id)
                  FROM member_payments mp
                  JOIN members m ON m.id = mp.member_id
                 WHERE m.branch_id = b.id AND mp.payment_year = ?) AS members_paid,
               COALESCE((SELECT SUM(mp.amount)
                           FROM member_payments mp
                           JOIN members m ON m.id = mp.member_id
                          WHERE m.branch_id = b.id AND mp.payment_year = ?), 0) AS member_dues_collected,
               COALESCE((SELECT SUM(bp.amount)
                           FROM branch_payments bp
                          WHERE bp.branch_id = b.id AND bp.payment_year = ?), 0) AS branch_regulation_paid,
               (SELECT COUNT(*) FROM projects p WHERE p.branch_id = b.id) AS project_count
        FROM branches b
        ORDER BY b.name
        """,
        (report_year, report_year, report_year),
    )



def get_member_compliance_report(report_year: int, branch_id: int | None = None) -> pd.DataFrame:
    query = """
        SELECT *
        FROM (
            SELECT m.membership_no,
                   m.full_name,
                   COALESCE(b.name, 'Unassigned') AS branch_name,
                   m.phone,
                   m.email,
                   m.status,
                   m.annual_due,
                   COALESCE((SELECT SUM(mp.amount)
                               FROM member_payments mp
                              WHERE mp.member_id = m.id AND mp.payment_year = ?), 0) AS paid_amount
            FROM members m
            LEFT JOIN branches b ON b.id = m.branch_id
        ) q
    """
    params: list[Any] = [report_year]
    if branch_id is not None:
        query += " WHERE branch_name = (SELECT name FROM branches WHERE id = ?)"
        params.append(branch_id)
    query += " ORDER BY full_name"
    df = fetch_df(query, tuple(params))
    if not df.empty:
        df["balance"] = df["annual_due"] - df["paid_amount"]
        df["payment_status"] = df["balance"].apply(lambda value: "Paid" if value <= 0 else "Outstanding")
    return df



def get_branch_compliance_report(report_year: int) -> pd.DataFrame:
    df = fetch_df(
        """
        SELECT b.name AS branch_name,
               b.city,
               b.annual_regulation,
               COALESCE((SELECT SUM(bp.amount)
                           FROM branch_payments bp
                          WHERE bp.branch_id = b.id AND bp.payment_year = ?), 0) AS paid_amount
        FROM branches b
        ORDER BY b.name
        """,
        (report_year,),
    )
    if not df.empty:
        df["balance"] = df["annual_regulation"] - df["paid_amount"]
        df["payment_status"] = df["balance"].apply(lambda value: "Paid" if value <= 0 else "Outstanding")
    return df



def get_finance_transactions_report(report_year: int) -> pd.DataFrame:
    return fetch_df(
        """
        SELECT 'Member Due' AS source_type,
               mp.date_paid AS transaction_date,
               mp.payment_year,
               m.membership_no AS reference_no,
               m.full_name AS payer_name,
               COALESCE(b.name, 'Unassigned') AS unit_name,
               mp.payment_type,
               mp.method,
               mp.reference,
               mp.amount
        FROM member_payments mp
        JOIN members m ON m.id = mp.member_id
        LEFT JOIN branches b ON b.id = m.branch_id
        WHERE mp.payment_year = ?

        UNION ALL

        SELECT 'Branch Regulation' AS source_type,
               bp.date_paid AS transaction_date,
               bp.payment_year,
               '' AS reference_no,
               b.name AS payer_name,
               b.city AS unit_name,
               'Annual Regulation' AS payment_type,
               bp.method,
               bp.reference,
               bp.amount
        FROM branch_payments bp
        JOIN branches b ON b.id = bp.branch_id
        WHERE bp.payment_year = ?

        ORDER BY transaction_date DESC, payer_name
        """,
        (report_year, report_year),
    )



def get_projects_report(status_filter: str = "All") -> pd.DataFrame:
    query = """
        SELECT p.title,
               p.category,
               p.location,
               COALESCE(b.name, 'National') AS supervising_branch,
               p.status,
               p.budget,
               p.amount_spent,
               p.progress_percent,
               p.start_date,
               p.end_date,
               p.sponsor,
               p.manager
        FROM projects p
        LEFT JOIN branches b ON b.id = p.branch_id
    """
    params: tuple[Any, ...] = ()
    if status_filter != "All":
        query += " WHERE p.status = ?"
        params = (status_filter,)
    query += " ORDER BY p.status, p.title"
    return fetch_df(query, params)



def get_election_report() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT e.title,
               e.level,
               COALESCE(b.name, 'National') AS branch_scope,
               e.election_date,
               e.venue,
               e.expected_attendance,
               e.term_years,
               e.status,
               (SELECT COUNT(*) FROM candidates c WHERE c.election_id = e.id) AS candidate_count
        FROM elections e
        LEFT JOIN branches b ON b.id = e.branch_id
        ORDER BY e.election_date DESC
        """
    )



def get_candidate_results_report() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT e.title AS election_title,
               c.position,
               m.membership_no,
               m.full_name,
               COALESCE(b.name, 'Unassigned') AS member_branch,
               c.votes,
               c.status
        FROM candidates c
        JOIN elections e ON e.id = c.election_id
        JOIN members m ON m.id = c.member_id
        LEFT JOIN branches b ON b.id = m.branch_id
        ORDER BY e.election_date DESC, c.position, c.votes DESC, m.full_name
        """
    )



def get_executive_expiry_report(days_ahead: int = 180) -> pd.DataFrame:
    cutoff_date = (date.today() + timedelta(days=days_ahead)).isoformat()
    return fetch_df(
        """
        SELECT ex.level,
               COALESCE(b.name, 'National') AS branch_scope,
               ex.office_name,
               m.membership_no,
               m.full_name,
               ex.start_date,
               ex.end_date,
               ROUND(julianday(ex.end_date) - julianday(date('now'))) AS days_remaining,
               ex.status
        FROM executive_terms ex
        JOIN members m ON m.id = ex.member_id
        LEFT JOIN branches b ON b.id = ex.branch_id
        WHERE date(ex.end_date) <= date(?)
        ORDER BY ex.end_date, ex.office_name
        """,
        (cutoff_date,),
    )



def get_agm_report() -> pd.DataFrame:
    return get_agm_df()



def get_national_summary_text(report_year: int) -> str:
    metrics = get_dashboard_metrics(report_year)
    settings = get_settings_dict()
    total_collected = metrics["member_dues_collected"] + metrics["branch_regulations_collected"]
    return (
        f"Association: {settings.get('association_name', 'WUCUDA')}\n"
        f"Patron: {settings.get('patron', 'The King of Babessi')}\n"
        f"Reporting Year: {report_year}\n\n"
        f"Total branches: {metrics['total_branches']}\n"
        f"Total members: {metrics['total_members']}\n"
        f"Active members: {metrics['active_members']}\n"
        f"Members who paid in {report_year}: {metrics['members_paid_this_year']}\n"
        f"Branches that paid regulation in {report_year}: {metrics['branches_paid_this_year']}\n"
        f"Member dues collected: {metrics['member_dues_collected']:.2f} FCFA\n"
        f"Branch regulations collected: {metrics['branch_regulations_collected']:.2f} FCFA\n"
        f"Total finance collected: {total_collected:.2f} FCFA\n"
        f"Total projects: {metrics['total_projects']}\n"
        f"Active projects: {metrics['active_projects']}\n"
        f"Planned/open elections: {metrics['planned_or_open_elections']}\n"
        f"Executive terms expiring in 180 days: {metrics['expiring_executive_terms_180']}\n"
    )



def seed_demo_data() -> None:
    with get_connection() as conn:
        branch_count = conn.execute("SELECT COUNT(*) FROM branches").fetchone()[0]
        if branch_count > 0:
            return

        annual_regulation = float(get_setting("branch_annual_regulation", "15000") or 15000)
        annual_due = float(get_setting("member_annual_due", "2000") or 2000)
        term_years = int(get_setting("executive_term_years", "3") or 3)
        major_event_expected_attendance = int(
            get_setting("major_event_expected_attendance", "1500") or 1500
        )

        branches = [
            ("WUCUDA Yaounde", "Yaounde", "Centre", "Branch Chairperson", "+237670000001", annual_regulation, "Active"),
            ("WUCUDA Douala", "Douala", "Littoral", "Branch Chairperson", "+237670000002", annual_regulation, "Active"),
            ("WUCUDA Bamenda", "Bamenda", "North West", "Branch Chairperson", "+237670000003", annual_regulation, "Active"),
            ("WUCUDA Bafoussam", "Bafoussam", "West", "Branch Chairperson", "+237670000004", annual_regulation, "Active"),
        ]
        conn.executemany(
            """
            INSERT INTO branches(name, city, region, contact_person, phone, annual_regulation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            branches,
        )

        branch_rows = conn.execute("SELECT id, name FROM branches ORDER BY id").fetchall()
        branch_map = {row["name"]: row["id"] for row in branch_rows}

        demo_members = [
            ("Nfor Emmanuel", "Male", "+237670111001", "nfor.emmanuel@example.com", "Businessman", "Yaounde", branch_map["WUCUDA Yaounde"], "2022-02-10", "Active", annual_due, ""),
            ("Tebit Susan", "Female", "+237670111002", "tebit.susan@example.com", "Teacher", "Douala", branch_map["WUCUDA Douala"], "2021-05-18", "Active", annual_due, ""),
            ("Fonyuy Peter", "Male", "+237670111003", "fonyuy.peter@example.com", "Engineer", "Bamenda", branch_map["WUCUDA Bamenda"], "2023-01-15", "Active", annual_due, ""),
            ("Ngum Mercy", "Female", "+237670111004", "ngum.mercy@example.com", "Nurse", "Bafoussam", branch_map["WUCUDA Bafoussam"], "2020-11-22", "Active", annual_due, ""),
            ("Mbah Daniel", "Male", "+237670111005", "mbah.daniel@example.com", "Farmer", "Babessi", None, "2019-08-30", "Active", annual_due, "Based in Babessi"),
            ("Taku Linda", "Female", "+237670111006", "taku.linda@example.com", "Civil Servant", "Yaounde", branch_map["WUCUDA Yaounde"], "2024-03-02", "Active", annual_due, "Youth representative"),
            ("Keng Charles", "Male", "+237670111007", "keng.charles@example.com", "Accountant", "Douala", branch_map["WUCUDA Douala"], "2023-06-09", "Active", annual_due, "Finance volunteer"),
            ("Nchinda Rose", "Female", "+237670111008", "nchinda.rose@example.com", "Trader", "Bamenda", branch_map["WUCUDA Bamenda"], "2022-09-12", "Inactive", annual_due, ""),
        ]

        for member in demo_members:
            membership_no = _next_membership_no(conn)
            conn.execute(
                """
                INSERT INTO members(
                    membership_no, full_name, gender, phone, email, occupation, city,
                    branch_id, joined_on, status, annual_due, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (membership_no, *member),
            )

        member_rows = conn.execute("SELECT id, full_name FROM members ORDER BY id").fetchall()
        member_map = {row["full_name"]: row["id"] for row in member_rows}

        current_year = date.today().year
        previous_year = current_year - 1

        member_payments = [
            (member_map["Nfor Emmanuel"], current_year, annual_due, f"{current_year}-01-15", "Annual Due", "Mobile Money", "MP001", ""),
            (member_map["Tebit Susan"], current_year, annual_due, f"{current_year}-02-10", "Annual Due", "Bank Transfer", "BT002", ""),
            (member_map["Fonyuy Peter"], current_year, annual_due, f"{current_year}-01-28", "Annual Due", "Cash", "CS003", ""),
            (member_map["Ngum Mercy"], previous_year, annual_due, f"{previous_year}-03-05", "Annual Due", "Cash", "CS004", "Previous year payment"),
            (member_map["Taku Linda"], current_year, annual_due, f"{current_year}-03-01", "Annual Due", "Mobile Money", "MP005", ""),
        ]
        conn.executemany(
            """
            INSERT INTO member_payments(member_id, payment_year, amount, date_paid, payment_type, method, reference, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            member_payments,
        )

        branch_payments = [
            (branch_map["WUCUDA Yaounde"], current_year, annual_regulation, f"{current_year}-01-12", "Bank Transfer", "BR001", ""),
            (branch_map["WUCUDA Douala"], current_year, annual_regulation, f"{current_year}-01-18", "Mobile Money", "BR002", ""),
            (branch_map["WUCUDA Bamenda"], previous_year, annual_regulation, f"{previous_year}-02-22", "Cash", "BR003", "Previous year payment"),
        ]
        conn.executemany(
            """
            INSERT INTO branch_payments(branch_id, payment_year, amount, date_paid, method, reference, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            branch_payments,
        )

        conn.execute(
            """
            INSERT INTO elections(title, level, branch_id, election_date, venue, expected_attendance, term_years, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "WUCUDA National Elections",
                "National",
                None,
                f"{current_year}-08-20",
                "Babessi Community Hall",
                major_event_expected_attendance,
                term_years,
                "Planned",
                "Election planning for the next national executive term.",
            ),
        )
        election_id = conn.execute("SELECT id FROM elections LIMIT 1").fetchone()[0]

        candidates = [
            (election_id, member_map["Nfor Emmanuel"], "National President", "Unity and development agenda.", 0, "Cleared"),
            (election_id, member_map["Tebit Susan"], "National Secretary", "Improve communication across branches.", 0, "Cleared"),
            (election_id, member_map["Keng Charles"], "National Financial Secretary", "Stronger financial accountability.", 0, "Cleared"),
        ]
        conn.executemany(
            """
            INSERT INTO candidates(election_id, member_id, position, manifesto, votes, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            candidates,
        )

        today = date.today()
        start_date = date(today.year - 2, 9, 1)
        end_date = date(today.year + 1, 8, 31)
        executives = [
            ("National", None, "National President", member_map["Nfor Emmanuel"], start_date.isoformat(), end_date.isoformat(), election_id, "Serving", "Current serving president."),
            ("National", None, "National Secretary", member_map["Tebit Susan"], start_date.isoformat(), end_date.isoformat(), election_id, "Serving", "Current serving secretary."),
        ]
        conn.executemany(
            """
            INSERT INTO executive_terms(level, branch_id, office_name, member_id, start_date, end_date, election_id, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            executives,
        )

        conn.execute(
            """
            INSERT INTO agm_meetings(title, meeting_date, venue, expected_attendance, actual_attendance, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "WUCUDA Annual General Assembly",
                f"{current_year}-12-15",
                "Babessi Community Hall",
                major_event_expected_attendance,
                None,
                "Large gathering for general assembly and strategic decisions.",
            ),
        )

        projects = [
            (
                "Babessi Water Extension",
                "Water Supply",
                "Babessi Central",
                None,
                12000000,
                4500000,
                f"{current_year}-01-10",
                f"{current_year}-12-30",
                "Active",
                "Community Fund",
                "Project Committee",
                40,
                "Extension of safe water to underserved quarters in Babessi.",
            ),
            (
                "Scholarship Support Program",
                "Education",
                "Babessi",
                branch_map["WUCUDA Yaounde"],
                3000000,
                1000000,
                f"{current_year}-02-01",
                f"{current_year}-10-30",
                "Active",
                "Diaspora Donations",
                "Education Desk",
                35,
                "Support for needy students from Babessi community.",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO projects(
                title, category, location, branch_id, budget, amount_spent,
                start_date, end_date, status, sponsor, manager, progress_percent, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            projects,
        )

        project_rows = conn.execute("SELECT id, title FROM projects ORDER BY id").fetchall()
        project_map = {row["title"]: row["id"] for row in project_rows}
        updates = [
            (project_map["Babessi Water Extension"], f"{current_year}-03-12", 40, "Survey, pipes procurement and first trenching phase completed."),
            (project_map["Scholarship Support Program"], f"{current_year}-03-20", 35, "Application review and first sponsorship disbursement completed."),
        ]
        conn.executemany(
            """
            INSERT INTO project_updates(project_id, update_date, progress_percent, summary)
            VALUES (?, ?, ?, ?)
            """,
            updates,
        )

        conn.commit()
