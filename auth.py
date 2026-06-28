"""
auth.py — FinSight Authentication & OTP using Twilio Verify
Features: OTP send/verify, local user storage, password hashing, profile persistence
"""

import json, bcrypt, os
from pathlib import Path
from datetime import datetime, date
from twilio.rest import Client

# ── Twilio config ─────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = "ACad7357f7f325bcff5ce276fafe2fbc80"
TWILIO_AUTH_TOKEN = "f72f4143aef9bc4af7c63d01ce3a109d"
TWILIO_VERIFY_SERVICE_SID = "VA0c543aa08ec6f1a602ff2985361b4ab8"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ── Data files ────────────────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)

def _load() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except:
            return {}
    return {}

def _save(users):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))

# ── OTP using Twilio ──────────────────────────────────────────────────────────
def send_otp_sms(mobile: str):
    mobile = mobile.strip()
    if not mobile.startswith("+91"):
        mobile = "+91" + mobile

    verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(
        to=mobile,
        channel="sms"
    )
    return True, f"OTP sent to {mobile}. Status: {verification.status}"

def verify_otp(mobile: str, entered_otp: str):
    mobile = mobile.strip()
    if not mobile.startswith("+91"):
        mobile = "+91" + mobile

    check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
        to=mobile,
        code=entered_otp.strip()
    )

    if check.status == "approved":
        return True, "OTP verified successfully!"
    return False, "Incorrect or expired OTP."

# ── Password helpers ──────────────────────────────────────────────────────────
def hash_pw(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def check_pw(plain, hashed):
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except:
        return False

def _calc_age(dob_str):
    try:
        bd = datetime.strptime(dob_str, "%Y-%m-%d").date()
        t = date.today()
        return t.year - bd.year - ((t.month, t.day) < (bd.month, bd.day))
    except:
        return 0

# ── Signup / Login ────────────────────────────────────────────────────────────
def user_exists(username): return username.lower().strip() in _load()

def mobile_exists(mobile):
    return any(u.get("mobile", "") == mobile.strip() for u in _load().values())

def email_exists(email):
    return any(u.get("email", "").lower() == email.strip().lower() for u in _load().values())

def signup(username, full_name, email, mobile, dob, plain_password):
    username = username.lower().strip()
    mobile = mobile.strip()
    email = email.strip().lower()

    if len(username) < 3:       return False, "Username must be at least 3 characters."
    if " " in username:         return False, "Username cannot have spaces."
    if len(plain_password) < 6: return False, "Password must be at least 6 characters."
    if "@" not in email:        return False, "Invalid email address."
    if not mobile.isdigit() or len(mobile) != 10:
        return False, "Enter a valid 10-digit mobile number (without +91)."

    users = _load()
    if username in users:       return False, "Username already taken."
    if mobile_exists(mobile):   return False, "Mobile number already registered."
    if email_exists(email):     return False, "Email already registered."

    users[username] = {
        "username": username,
        "full_name": full_name.strip() or username,
        "email": email,
        "mobile": mobile,
        "dob": dob,
        "age": _calc_age(dob),
        "password": hash_pw(plain_password),
        "created_at": datetime.now().isoformat(),
        "reports": [],
        "finance": {},
    }
    _save(users)
    return True, "Account created successfully!"

def login(username, plain_password):
    username = username.lower().strip()
    users = _load()
    if username not in users:
        return False, "Username not found.", {}
    u = users[username]
    if not check_pw(plain_password, u["password"]):
        return False, "Incorrect password.", {}
    return True, "Login successful!", u

def login_by_mobile(mobile):
    for uname, u in _load().items():
        if u.get("mobile", "") == mobile.strip():
            return True, "User found.", u
    return False, "No account with this mobile number.", {}

# ── Finance persistence ───────────────────────────────────────────────────────
def save_finance(username, finance_data):
    users = _load()
    username = username.lower().strip()
    if username in users:
        users[username]["finance"] = finance_data
        dob = users[username].get("dob", "")
        if dob:
            users[username]["age"] = _calc_age(dob)
        _save(users)

def load_finance(username):
    return _load().get(username.lower().strip(), {}).get("finance", {})

# ── Profile update ────────────────────────────────────────────────────────────
def update_profile(username, updates):
    users = _load()
    username = username.lower().strip()
    if username not in users:
        return False, "User not found."

    u = users[username]
    if updates.get("full_name", "").strip():
        u["full_name"] = updates["full_name"].strip()

    if updates.get("email", "").strip():
        e = updates["email"].strip().lower()
        if "@" not in e:
            return False, "Invalid email."
        for k, v in users.items():
            if k != username and v.get("email", "").lower() == e:
                return False, "Email already used by another account."
        u["email"] = e

    if updates.get("mobile", "").strip():
        m = updates["mobile"].strip()
        if not m.isdigit() or len(m) != 10:
            return False, "Invalid mobile number."
        for k, v in users.items():
            if k != username and v.get("mobile", "") == m:
                return False, "Mobile already used by another account."
        u["mobile"] = m

    if updates.get("dob", ""):
        age = _calc_age(updates["dob"])
        if age == 0:
            return False, "Invalid date of birth."
        u["dob"] = updates["dob"]
        u["age"] = age

    if updates.get("new_password", ""):
        if len(updates["new_password"]) < 6:
            return False, "Password must be at least 6 characters."
        u["password"] = hash_pw(updates["new_password"])

    users[username] = u
    _save(users)
    return True, "Profile updated successfully!"

# ── Admin ops ────────────────────────────────────────────────────────────────
def all_users(): return _load()

def get_user(username):
    return _load().get(username.lower().strip(), {})

def delete_user(username):
    users = _load()
    username = username.lower().strip()
    if username not in users:
        return False, "User not found."
    del users[username]
    _save(users)
    return True, f"User '{username}' deleted."

def admin_update_user(username, updates):
    return update_profile(username, updates)

def save_user_report(username, report_meta):
    users = _load()
    username = username.lower().strip()
    if username in users:
        users[username].setdefault("reports", []).append(report_meta)
        _save(users)