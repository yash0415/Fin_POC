"""auth.py — Simple file-based auth, no DB, no OTP."""
import json, bcrypt
from pathlib import Path
from datetime import datetime, date

DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)

def _load():
    if USERS_FILE.exists():
        try: return json.loads(USERS_FILE.read_text())
        except: return {}
    return {}

def _save(u): USERS_FILE.write_text(json.dumps(u, indent=2, ensure_ascii=False))

def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p, h):
    try: return bcrypt.checkpw(p.encode(), h.encode())
    except: return False

def _age(dob):
    try:
        bd = datetime.strptime(dob, "%Y-%m-%d").date()
        t  = date.today()
        return t.year - bd.year - ((t.month, t.day) < (bd.month, bd.day))
    except: return 0

def user_exists(u): return u.lower().strip() in _load()
def mobile_exists(m): return any(v.get("mobile","") == m.strip() for v in _load().values())
def email_exists(e): return any(v.get("email","").lower() == e.strip().lower() for v in _load().values())

def signup(username, full_name, email, mobile, dob, password):
    username = username.lower().strip(); mobile = mobile.strip(); email = email.strip().lower()
    if len(username) < 3: return False, "Username must be at least 3 characters."
    if " " in username:   return False, "Username cannot have spaces."
    if len(password) < 6: return False, "Password must be at least 6 characters."
    if "@" not in email:  return False, "Invalid email address."
    if not mobile.isdigit() or len(mobile) != 10: return False, "Enter a valid 10-digit mobile number."
    users = _load()
    if username in users:    return False, "Username already taken."
    if mobile_exists(mobile): return False, "Mobile number already registered."
    if email_exists(email):   return False, "Email already registered."
    users[username] = {
        "username": username, "full_name": full_name.strip() or username,
        "email": email, "mobile": mobile, "dob": dob, "age": _age(dob),
        "password": hash_pw(password), "created_at": datetime.now().isoformat(),
        "reports": [], "finance": {},
    }
    _save(users); return True, "Account created successfully!"

def login(username, password):
    username = username.lower().strip(); users = _load()
    if username not in users: return False, "Username not found.", {}
    u = users[username]
    if not check_pw(password, u.get("password","")): return False, "Incorrect password.", {}
    return True, "Login successful!", u

def save_finance(username, finance_data):
    users = _load(); u = username.lower().strip()
    if u in users:
        users[u]["finance"] = finance_data
        dob = users[u].get("dob","")
        if dob: users[u]["age"] = _age(dob)
        _save(users)

def load_finance(username):
    return _load().get(username.lower().strip(), {}).get("finance", {})

def update_profile(username, updates):
    users = _load(); username = username.lower().strip()
    if username not in users: return False, "User not found."
    u = users[username]
    if updates.get("full_name","").strip(): u["full_name"] = updates["full_name"].strip()
    if updates.get("email","").strip():
        e = updates["email"].strip().lower()
        if "@" not in e: return False, "Invalid email."
        for k,v in users.items():
            if k != username and v.get("email","").lower() == e: return False, "Email already used."
        u["email"] = e
    if updates.get("mobile","").strip():
        m = updates["mobile"].strip()
        if not m.isdigit() or len(m) != 10: return False, "Invalid mobile number."
        for k,v in users.items():
            if k != username and v.get("mobile","") == m: return False, "Mobile already used."
        u["mobile"] = m
    if updates.get("dob",""):
        a = _age(updates["dob"])
        if a == 0: return False, "Invalid date of birth."
        u["dob"] = updates["dob"]; u["age"] = a
    if updates.get("new_password",""):
        if len(updates["new_password"]) < 6: return False, "Password must be at least 6 characters."
        u["password"] = hash_pw(updates["new_password"])
    users[username] = u; _save(users); return True, "Profile updated successfully!"

def all_users(): return _load()
def get_user(username): return _load().get(username.lower().strip(), {})

def delete_user(username):
    users = _load(); username = username.lower().strip()
    if username not in users: return False, "User not found."
    del users[username]; _save(users); return True, f"User '{username}' deleted."

def admin_update_user(username, updates): return update_profile(username, updates)

def save_user_report(username, report_meta):
    users = _load(); username = username.lower().strip()
    if username in users:
        users[username].setdefault("reports",[]).append(report_meta)
        _save(users)