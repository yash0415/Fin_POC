"""
db.py — Persistent storage for FinSight
Uses Supabase (free PostgreSQL) when configured, falls back to local JSON.

Setup Supabase (free, 5 minutes):
1. Go to https://supabase.com → New project
2. Go to SQL Editor → run the SQL in supabase_setup.sql
3. Go to Project Settings → API → copy URL and anon key
4. Add to Streamlit secrets:
      SUPABASE_URL = "https://xxxx.supabase.co"
      SUPABASE_KEY = "your-anon-key"
"""


import json
import streamlit as st
from pathlib import Path
from datetime import datetime

# ── Local fallback paths ───────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
SUBS_FILE  = DATA_DIR / "submissions.json"
REPORTS_DIR= DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ── Try to connect to Supabase ─────────────────────────────────────────────────
def _get_supabase():
    """Returns Supabase client or None if not configured."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None

def _use_supabase():
    return _get_supabase() is not None


# ══════════════════════════════════════════════════════════════════════════════
# USER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_users() -> dict:
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("users").select("*").execute()
            return {r["username"]: r for r in (res.data or [])}
        except Exception:
            pass
    # Local fallback
    if USERS_FILE.exists():
        try: return json.loads(USERS_FILE.read_text())
        except: pass
    return {}

def get_user(username: str) -> dict:
    username = username.lower().strip()
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("users").select("*").eq("username", username).execute()
            return res.data[0] if res.data else {}
        except Exception:
            pass
    return get_all_users().get(username, {})

def user_exists(username: str) -> bool:
    return bool(get_user(username.lower().strip()))

def mobile_exists(mobile: str) -> bool:
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("users").select("username").eq("mobile", mobile.strip()).execute()
            return bool(res.data)
        except Exception:
            pass
    return any(u.get("mobile","") == mobile.strip() for u in get_all_users().values())

def email_exists(email: str) -> bool:
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("users").select("username").eq("email", email.strip().lower()).execute()
            return bool(res.data)
        except Exception:
            pass
    return any(u.get("email","").lower() == email.strip().lower() for u in get_all_users().values())

def create_user(user_dict: dict) -> bool:
    """Insert new user. Returns True on success."""
    sb = _get_supabase()
    if sb:
        try:
            sb.table("users").insert(user_dict).execute()
            return True
        except Exception as e:
            st.warning(f"DB write failed, using local: {e}")
    # Local fallback
    try:
        users = get_all_users()
        users[user_dict["username"]] = user_dict
        USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False

def update_user(username: str, updates: dict) -> bool:
    """Update user fields. Returns True on success."""
    username = username.lower().strip()
    sb = _get_supabase()
    if sb:
        try:
            sb.table("users").update(updates).eq("username", username).execute()
            return True
        except Exception:
            pass
    # Local fallback
    try:
        users = get_all_users()
        if username in users:
            users[username].update(updates)
            USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))
            return True
    except Exception:
        pass
    return False

def delete_user_db(username: str) -> bool:
    username = username.lower().strip()
    sb = _get_supabase()
    if sb:
        try:
            sb.table("users").delete().eq("username", username).execute()
            return True
        except Exception:
            pass
    try:
        users = get_all_users()
        if username in users:
            del users[username]
            USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))
            return True
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════════════════════════
# FINANCE DATA  (stored inside user row as JSON column)
# ══════════════════════════════════════════════════════════════════════════════

def save_finance(username: str, finance_data: dict):
    username = username.lower().strip()
    # Supabase stores finance as JSONB column
    sb = _get_supabase()
    if sb:
        try:
            sb.table("users").update({"finance": finance_data}).eq("username", username).execute()
            return
        except Exception:
            pass
    # Local fallback
    users = get_all_users()
    if username in users:
        users[username]["finance"] = finance_data
        USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))

def load_finance(username: str) -> dict:
    u = get_user(username.lower().strip())
    fin = u.get("finance", {})
    # Supabase returns JSONB as dict directly
    if isinstance(fin, str):
        try: return json.loads(fin)
        except: return {}
    return fin or {}


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS / SUBMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

def save_submission(meta: dict):
    sb = _get_supabase()
    if sb:
        try:
            # Remove non-serializable items
            clean = {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool, type(None)))}
            sb.table("submissions").insert(clean).execute()
            return
        except Exception:
            pass
    # Local fallback
    try:
        subs = []
        if SUBS_FILE.exists():
            try: subs = json.loads(SUBS_FILE.read_text())
            except: subs = []
        subs.append(meta)
        SUBS_FILE.write_text(json.dumps(subs, indent=2, ensure_ascii=False))
    except Exception:
        pass

def load_submissions() -> list:
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("submissions").select("*").order("created_at", desc=True).execute()
            return res.data or []
        except Exception:
            pass
    if SUBS_FILE.exists():
        try: return json.loads(SUBS_FILE.read_text())
        except: pass
    return []

def save_user_report(username: str, report_meta: dict):
    """Append report metadata to user's reports list."""
    u = get_user(username)
    if not u: return
    reports = u.get("reports", []) or []
    if isinstance(reports, str):
        try: reports = json.loads(reports)
        except: reports = []
    reports.append(report_meta)
    update_user(username, {"reports": reports})

def is_supabase_connected() -> bool:
    return _use_supabase()
