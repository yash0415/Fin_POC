"""
auth.py — User authentication for FinSight
Handles signup, login, password hashing, and user data persistence.
"""
import json
import bcrypt
from pathlib import Path
from datetime import datetime

DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
def _load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except Exception:
            return {}
    return {}

def _save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

# ── Public API ────────────────────────────────────────────────────────────────
def user_exists(username: str) -> bool:
    return username.lower().strip() in _load_users()

def signup(username: str, email: str, plain_password: str, full_name: str) -> tuple[bool, str]:
    """Returns (success, message)"""
    username = username.lower().strip()
    if not username or not plain_password or not email:
        return False, "Username, email and password are required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(plain_password) < 6:
        return False, "Password must be at least 6 characters."
    if "@" not in email:
        return False, "Please enter a valid email address."
    users = _load_users()
    if username in users:
        return False, "Username already exists. Please choose another."
    # check email uniqueness
    for u in users.values():
        if u.get("email","").lower() == email.lower():
            return False, "An account with this email already exists."
    users[username] = {
        "username":   username,
        "full_name":  full_name or username,
        "email":      email.lower(),
        "password":   hash_password(plain_password),
        "created_at": datetime.now().isoformat(),
        "reports":    [],   # list of report metadata
    }
    _save_users(users)
    return True, "Account created successfully!"

def login(username: str, plain_password: str) -> tuple[bool, str, dict]:
    """Returns (success, message, user_dict)"""
    username = username.lower().strip()
    users    = _load_users()
    if username not in users:
        return False, "Username not found.", {}
    u = users[username]
    if not check_password(plain_password, u["password"]):
        return False, "Incorrect password.", {}
    return True, "Login successful!", u

def get_user(username: str) -> dict:
    return _load_users().get(username.lower().strip(), {})

def save_user_report(username: str, report_meta: dict):
    """Attach a report record to the user's account."""
    users = _load_users()
    username = username.lower().strip()
    if username in users:
        users[username].setdefault("reports", []).append(report_meta)
        _save_users(users)

def all_users() -> dict:
    """Return all users (admin only)."""
    return _load_users()
