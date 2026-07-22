"""
database.py — SQLite storage for FinSight
Single file DB: data/finsight.db
All tables created automatically on first run.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_DIR  = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "finsight.db"
DB_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION
# ══════════════════════════════════════════════════════════════════════════════
def get_conn():
    """Return a SQLite connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA — auto-created on import
# ══════════════════════════════════════════════════════════════════════════════
def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username    TEXT PRIMARY KEY,
            full_name   TEXT,
            email       TEXT UNIQUE,
            mobile      TEXT UNIQUE,
            dob         TEXT,
            age         INTEGER DEFAULT 0,
            password    TEXT NOT NULL,
            created_at  TEXT,
            reports     TEXT DEFAULT '[]',   -- JSON array
            finance     TEXT DEFAULT '{}'    -- JSON object
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT,
            full_name       TEXT,
            email           TEXT,
            phone           TEXT,
            city            TEXT,
            age             INTEGER,
            salary          REAL,
            score           INTEGER,
            score_label     TEXT,
            net_worth       REAL,
            paid            INTEGER DEFAULT 0,
            auto_save       INTEGER DEFAULT 0,
            upi_id          TEXT,
            pdf_file        TEXT,
            screenshot_file TEXT,
            saved_at        TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        """)

# Run on import
init_db()


# ══════════════════════════════════════════════════════════════════════════════
# USER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════
def _row_to_dict(row):
    if row is None:
        return {}
    d = dict(row)
    # Parse JSON columns
    for col in ("reports", "finance"):
        if col in d and isinstance(d[col], str):
            try:    d[col] = json.loads(d[col])
            except: d[col] = [] if col == "reports" else {}
    return d

def get_all_users() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
    return {r["username"]: _row_to_dict(r) for r in rows}

def get_user(username: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.lower().strip(),)
        ).fetchone()
    return _row_to_dict(row)

def user_exists(username: str) -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username.lower().strip(),)
        ).fetchone()
    return r is not None

def mobile_exists(mobile: str, exclude_username: str = "") -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "SELECT 1 FROM users WHERE mobile = ? AND username != ?",
            (mobile.strip(), exclude_username.lower())
        ).fetchone()
    return r is not None

def email_exists(email: str, exclude_username: str = "") -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "SELECT 1 FROM users WHERE email = ? AND username != ?",
            (email.strip().lower(), exclude_username.lower())
        ).fetchone()
    return r is not None

def create_user(user_dict: dict) -> bool:
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO users
                    (username, full_name, email, mobile, dob, age,
                     password, created_at, reports, finance)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                user_dict["username"],
                user_dict.get("full_name",""),
                user_dict.get("email",""),
                user_dict.get("mobile",""),
                user_dict.get("dob",""),
                user_dict.get("age", 0),
                user_dict["password"],
                user_dict.get("created_at", datetime.now().isoformat()),
                json.dumps(user_dict.get("reports", [])),
                json.dumps(user_dict.get("finance", {})),
            ))
        return True
    except sqlite3.IntegrityError as e:
        return False
    except Exception:
        return False

def update_user(username: str, updates: dict) -> bool:
    """Update specific fields for a user."""
    if not updates:
        return True
    username = username.lower().strip()
    # Serialize JSON fields
    for col in ("reports", "finance"):
        if col in updates and not isinstance(updates[col], str):
            updates[col] = json.dumps(updates[col], ensure_ascii=False)
    cols   = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [username]
    try:
        with get_conn() as conn:
            conn.execute(f"UPDATE users SET {cols} WHERE username = ?", values)
        return True
    except Exception:
        return False

def delete_user_db(username: str) -> bool:
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM users WHERE username = ?",
                         (username.lower().strip(),))
        return True
    except Exception:
        return False

def save_finance(username: str, finance_data: dict):
    update_user(username, {"finance": finance_data})

def load_finance(username: str) -> dict:
    u = get_user(username)
    fin = u.get("finance", {})
    return fin if isinstance(fin, dict) else {}

def save_user_report(username: str, report_meta: dict):
    u = get_user(username)
    if not u:
        return
    reports = u.get("reports", [])
    if not isinstance(reports, list):
        reports = []
    reports.append(report_meta)
    update_user(username, {"reports": reports})


# ══════════════════════════════════════════════════════════════════════════════
# SUBMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
def save_submission(meta: dict):
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO submissions
                    (username, full_name, email, phone, city, age,
                     salary, score, score_label, net_worth, paid,
                     auto_save, upi_id, pdf_file, screenshot_file, saved_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                meta.get("username",""),
                meta.get("full_name") or meta.get("name",""),
                meta.get("email",""),
                meta.get("phone",""),
                meta.get("city",""),
                meta.get("age", 0),
                meta.get("salary", 0),
                meta.get("score", 0),
                meta.get("score_label",""),
                meta.get("net_worth", 0),
                1 if meta.get("paid") else 0,
                1 if meta.get("auto_save") else 0,
                meta.get("upi_id",""),
                meta.get("pdf_file",""),
                meta.get("screenshot_file",""),
                meta.get("saved_at", datetime.now().strftime("%Y%m%d_%H%M%S")),
            ))
    except Exception:
        pass

def load_submissions() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM submissions ORDER BY id DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["paid"]      = bool(d.get("paid", 0))
        d["auto_save"] = bool(d.get("auto_save", 0))
        result.append(d)
    return result

def update_submission_screenshot(pdf_file: str, screenshot_file: str):
    try:
        with get_conn() as conn:
            conn.execute(
                "UPDATE submissions SET screenshot_file = ?, paid = 1 WHERE pdf_file = ?",
                (screenshot_file, pdf_file)
            )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN STATS
# ══════════════════════════════════════════════════════════════════════════════
def get_stats() -> dict:
    with get_conn() as conn:
        total_users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_subs   = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        paid_count   = conn.execute("SELECT COUNT(*) FROM submissions WHERE paid=1").fetchone()[0]
        auto_count   = conn.execute("SELECT COUNT(*) FROM submissions WHERE auto_save=1").fetchone()[0]
    return {
        "total_users": total_users,
        "total_subs":  total_subs,
        "paid_count":  paid_count,
        "auto_count":  auto_count,
        "revenue":     paid_count * 100,
    }

def db_path() -> str:
    return str(DB_PATH.resolve())