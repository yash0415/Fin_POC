"""
db.py v16 — Persistent storage for FinSight
Uses Supabase REST API directly via httpx — NO supabase package needed.
Falls back to local JSON when Supabase is not configured.

Why REST API instead of supabase-py package?
  The supabase-py package has version conflicts on Streamlit Cloud.
  Direct REST API uses only httpx which is already installed everywhere.
"""

import json
import httpx
import streamlit as st
from pathlib import Path
from datetime import datetime

# ── Local fallback paths ───────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
SUBS_FILE   = DATA_DIR / "submissions.json"
USERS_FILE  = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ── Cached connection state ────────────────────────────────────────────────────
_sb      = None          # SupabaseREST client instance
_sb_err  = None          # Last error string
_sb_init = False         # Whether we've tried to init


# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE REST CLIENT  (pure httpx, no extra packages)
# ══════════════════════════════════════════════════════════════════════════════
class SupabaseREST:
    """
    Minimal Supabase REST API client using httpx.
    Supports: select, insert, update, upsert, delete.
    Works with both eyJ... JWT keys and sb_publishable... keys.
    """
    def __init__(self, url: str, key: str):
        self.url  = url.rstrip("/")
        self.key  = key
        self.base = f"{self.url}/rest/v1"
        self.hdrs = {
            "apikey":        key,
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        }

    def _get(self, table, params=""):
        r = httpx.get(f"{self.base}/{table}?{params}",
                       headers=self.hdrs, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, table, data, prefer="return=representation"):
        h = {**self.hdrs, "Prefer": prefer}
        r = httpx.post(f"{self.base}/{table}", headers=h,
                        content=json.dumps(data, default=str), timeout=15)
        r.raise_for_status()
        return r.json() if r.text else []

    def _patch(self, table, data, filters):
        qs = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        h  = {**self.hdrs, "Prefer": "return=representation"}
        r  = httpx.patch(f"{self.base}/{table}?{qs}", headers=h,
                          content=json.dumps(data, default=str), timeout=15)
        r.raise_for_status()
        return r.json() if r.text else []

    def _delete(self, table, filters):
        qs = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        r  = httpx.delete(f"{self.base}/{table}?{qs}",
                           headers=self.hdrs, timeout=15)
        r.raise_for_status()
        return r.json() if r.text else []

    def select(self, table, cols="*", filters=None, limit=None):
        qs = f"select={cols}"
        if filters:
            for k, v in filters.items():
                qs += f"&{k}=eq.{v}"
        if limit:
            qs += f"&limit={limit}"
        return self._get(table, qs)

    def insert(self, table, data):
        return self._post(table, data)

    def upsert(self, table, data):
        return self._post(table, data,
                          prefer="resolution=merge-duplicates,return=representation")

    def update(self, table, data, filters):
        return self._patch(table, data, filters)

    def delete(self, table, filters):
        return self._delete(table, filters)

    def ping(self):
        """Quick connectivity test — reads 1 row from users table."""
        r = httpx.get(f"{self.base}/users?select=username&limit=1",
                       headers=self.hdrs, timeout=10)
        return r.status_code, r.text


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def _get_sb() -> SupabaseREST | None:
    global _sb, _sb_err, _sb_init
    if _sb_init:
        return _sb
    _sb_init = True
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key:
            _sb_err = "SUPABASE_URL or SUPABASE_KEY not set in Streamlit Secrets."
            return None
        client = SupabaseREST(url.strip(), key.strip())
        # Quick ping to verify it actually works
        status, body = client.ping()
        if status == 200:
            _sb     = client
            _sb_err = None
        elif status == 401:
            _sb_err = (
                "Authentication failed (401). Your SUPABASE_KEY is incorrect.\n"
                "Go to Supabase → Settings → API → copy the 'anon public' key.\n"
                f"Body: {body[:120]}"
            )
        elif status == 404:
            _sb_err = (
                "Table 'users' not found (404). Run supabase_setup.sql in Supabase SQL Editor."
            )
        else:
            _sb_err = f"Unexpected response {status}: {body[:150]}"
    except httpx.ConnectError as e:
        _sb_err = f"Cannot reach Supabase URL. Check SUPABASE_URL is correct. ({e})"
    except Exception as e:
        _sb_err = f"{type(e).__name__}: {e}"
    return _sb

def is_supabase_connected() -> bool:
    return _get_sb() is not None

def get_connection_error() -> str:
    _get_sb()   # ensure init
    return _sb_err or ""

def reset_connection():
    """Force reconnect — call after updating secrets."""
    global _sb, _sb_err, _sb_init
    _sb = None; _sb_err = None; _sb_init = False


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL JSON HELPERS (fallback)
# ══════════════════════════════════════════════════════════════════════════════
def _load_local_users():
    if USERS_FILE.exists():
        try: return json.loads(USERS_FILE.read_text())
        except: pass
    return {}

def _save_local_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))


# ══════════════════════════════════════════════════════════════════════════════
# USER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════
def get_all_users() -> dict:
    sb = _get_sb()
    if sb:
        try:
            rows = sb.select("users")
            return {r["username"]: r for r in rows}
        except Exception:
            pass
    return _load_local_users()

def get_user(username: str) -> dict:
    username = username.lower().strip()
    sb = _get_sb()
    if sb:
        try:
            rows = sb.select("users", filters={"username": username})
            return rows[0] if rows else {}
        except Exception:
            pass
    return _load_local_users().get(username, {})

def user_exists(username: str) -> bool:
    return bool(get_user(username.lower().strip()))

def mobile_exists(mobile: str) -> bool:
    sb = _get_sb()
    if sb:
        try:
            rows = sb.select("users", cols="username", filters={"mobile": mobile.strip()})
            return bool(rows)
        except Exception:
            pass
    return any(u.get("mobile","") == mobile.strip() for u in _load_local_users().values())

def email_exists(email: str) -> bool:
    sb = _get_sb()
    if sb:
        try:
            rows = sb.select("users", cols="username", filters={"email": email.strip().lower()})
            return bool(rows)
        except Exception:
            pass
    return any(u.get("email","").lower() == email.strip().lower() for u in _load_local_users().values())

def create_user(user_dict: dict) -> bool:
    sb = _get_sb()
    if sb:
        try:
            sb.insert("users", user_dict)
            return True
        except Exception as e:
            st.warning(f"Supabase write failed, saving locally: {e}")
    try:
        users = _load_local_users()
        users[user_dict["username"]] = user_dict
        _save_local_users(users)
        return True
    except Exception:
        return False

def update_user(username: str, updates: dict) -> bool:
    username = username.lower().strip()
    sb = _get_sb()
    if sb:
        try:
            sb.update("users", updates, {"username": username})
            return True
        except Exception:
            pass
    try:
        users = _load_local_users()
        if username in users:
            users[username].update(updates)
            _save_local_users(users)
            return True
    except Exception:
        pass
    return False

def delete_user_db(username: str) -> bool:
    username = username.lower().strip()
    sb = _get_sb()
    if sb:
        try:
            sb.delete("users", {"username": username})
            return True
        except Exception:
            pass
    try:
        users = _load_local_users()
        if username in users:
            del users[username]
            _save_local_users(users)
            return True
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════════════════════════
# FINANCE DATA
# ══════════════════════════════════════════════════════════════════════════════
def save_finance(username: str, finance_data: dict):
    update_user(username.lower().strip(), {"finance": finance_data})

def load_finance(username: str) -> dict:
    u   = get_user(username.lower().strip())
    fin = u.get("finance", {})
    if isinstance(fin, str):
        try: return json.loads(fin)
        except: return {}
    return fin or {}


# ══════════════════════════════════════════════════════════════════════════════
# SUBMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
def save_submission(meta: dict):
    sb = _get_sb()
    if sb:
        try:
            clean = {k: v for k, v in meta.items()
                     if isinstance(v, (str, int, float, bool, type(None)))}
            sb.insert("submissions", clean)
            return
        except Exception:
            pass
    try:
        subs = []
        if SUBS_FILE.exists():
            try: subs = json.loads(SUBS_FILE.read_text())
            except: pass
        subs.append(meta)
        SUBS_FILE.write_text(json.dumps(subs, indent=2, ensure_ascii=False))
    except Exception:
        pass

def load_submissions() -> list:
    sb = _get_sb()
    if sb:
        try:
            return sb.select("submissions")
        except Exception:
            pass
    if SUBS_FILE.exists():
        try: return json.loads(SUBS_FILE.read_text())
        except: pass
    return []

def save_user_report(username: str, report_meta: dict):
    u = get_user(username)
    if not u: return
    reports = u.get("reports", []) or []
    if isinstance(reports, str):
        try: reports = json.loads(reports)
        except: reports = []
    reports.append(report_meta)
    update_user(username, {"reports": reports})