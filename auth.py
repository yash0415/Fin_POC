"""
Install: pip install twilio  (already in requirements.txt)
auth.py v8 — FinSight Authentication & User Data
Features: signup with mobile+DOB, OTP, login, finance data persistence,
          profile update, delete user, admin operations
"""
import json, random, bcrypt
from pathlib import Path
from datetime import datetime, date

DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
OTP_FILE   = DATA_DIR / "otps.json"
DATA_DIR.mkdir(exist_ok=True)

def _load() -> dict:
    if USERS_FILE.exists():
        try: return json.loads(USERS_FILE.read_text())
        except: return {}
    return {}

def _save(users):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))

def _load_otps():
    if OTP_FILE.exists():
        try: return json.loads(OTP_FILE.read_text())
        except: return {}
    return {}

def _save_otps(otps):
    OTP_FILE.write_text(json.dumps(otps, indent=2))

# ── OTP ───────────────────────────────────────────────────────────────────────
def generate_otp(identifier):
    otp = str(random.randint(100000, 999999))
    otps = _load_otps()
    otps[identifier] = {"otp": otp, "created_at": datetime.now().isoformat()}
    _save_otps(otps)
    return otp

def verify_otp(identifier, entered):
    otps = _load_otps()
    if identifier not in otps:
        return False, "No OTP found. Request a new one."
    rec = otps[identifier]
    diff = (datetime.now() - datetime.fromisoformat(rec["created_at"])).total_seconds()
    if diff > 600:
        return False, "OTP expired. Request a new one."
    if rec["otp"] != entered.strip():
        return False, "Incorrect OTP."
    del otps[identifier]; _save_otps(otps)
    return True, "OTP verified!"

def send_otp_sms(mobile, otp):
    """
    Send OTP via Twilio SMS.
    Reads credentials from st.secrets (Streamlit Cloud) or env vars (local).

    st.secrets (set in Streamlit Cloud → App Settings → Secrets):
        TWILIO_SID   = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        TWILIO_TOKEN = "your_auth_token"
        TWILIO_FROM  = "+1XXXXXXXXXX"   ← your Twilio phone number

    Returns: "sent" if SMS sent, or the OTP string in demo/fallback mode.
    """
    try:
        import streamlit as _st
        sid   = _st.secrets["TWILIO_SID"]
        token = _st.secrets["TWILIO_TOKEN"]
        from_ = _st.secrets["TWILIO_FROM"]
        from twilio.rest import Client
        Client(sid, token).messages.create(
            body=f"Your FinSight OTP is: {otp}. Valid for 10 minutes. Do not share with anyone.",
            from_=from_,
            to=f"+91{mobile}"
        )
        return "sent"
    except KeyError:
        # Twilio secrets not configured — demo mode (OTP shown on screen)
        return otp
    except ImportError:
        # twilio package not installed
        return otp
    except Exception as e:
        # SMS failed but don't crash the app — return OTP for fallback display
        return otp

# ── Password ──────────────────────────────────────────────────────────────────
def hash_pw(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def check_pw(plain, hashed):
    try: return bcrypt.checkpw(plain.encode(), hashed.encode())
    except: return False

def _calc_age(dob_str):
    try:
        bd = datetime.strptime(dob_str, "%Y-%m-%d").date()
        t  = date.today()
        return t.year - bd.year - ((t.month, t.day) < (bd.month, bd.day))
    except: return 0

# ── Signup / Login ────────────────────────────────────────────────────────────
def user_exists(username): return username.lower().strip() in _load()

def mobile_exists(mobile):
    return any(u.get("mobile","") == mobile.strip() for u in _load().values())

def email_exists(email):
    return any(u.get("email","").lower() == email.strip().lower() for u in _load().values())

def signup(username, full_name, email, mobile, dob, plain_password):
    username = username.lower().strip(); mobile = mobile.strip(); email = email.strip().lower()
    if len(username) < 3:          return False, "Username must be at least 3 characters."
    if " " in username:            return False, "Username cannot have spaces."
    if len(plain_password) < 6:    return False, "Password must be at least 6 characters."
    if "@" not in email:           return False, "Invalid email address."
    if not mobile.isdigit() or len(mobile) != 10:
        return False, "Enter a valid 10-digit mobile number (without +91)."
    users = _load()
    if username in users:          return False, "Username already taken."
    if mobile_exists(mobile):      return False, "Mobile number already registered."
    if email_exists(email):        return False, "Email already registered."
    users[username] = {
        "username": username, "full_name": full_name.strip() or username,
        "email": email, "mobile": mobile, "dob": dob,
        "age": _calc_age(dob), "password": hash_pw(plain_password),
        "created_at": datetime.now().isoformat(), "reports": [], "finance": {},
    }
    _save(users); return True, "Account created successfully!"

def login(username, plain_password):
    username = username.lower().strip(); users = _load()
    if username not in users: return False, "Username not found.", {}
    u = users[username]
    if not check_pw(plain_password, u["password"]): return False, "Incorrect password.", {}
    return True, "Login successful!", u

def login_by_mobile(mobile):
    for uname, u in _load().items():
        if u.get("mobile","") == mobile.strip():
            return True, "User found.", u
    return False, "No account with this mobile number.", {}

# ── Finance data persistence ───────────────────────────────────────────────────
def save_finance(username, finance_data):
    users = _load(); username = username.lower().strip()
    if username in users:
        users[username]["finance"] = finance_data
        dob = users[username].get("dob","")
        if dob: users[username]["age"] = _calc_age(dob)
        _save(users)

def load_finance(username):
    return _load().get(username.lower().strip(), {}).get("finance", {})

# ── Profile update ────────────────────────────────────────────────────────────
def update_profile(username, updates):
    users = _load(); username = username.lower().strip()
    if username not in users: return False, "User not found."
    u = users[username]
    if updates.get("full_name","").strip(): u["full_name"] = updates["full_name"].strip()
    if updates.get("email","").strip():
        e = updates["email"].strip().lower()
        if "@" not in e: return False, "Invalid email."
        for k,v in users.items():
            if k != username and v.get("email","").lower() == e:
                return False, "Email already used by another account."
        u["email"] = e
    if updates.get("mobile","").strip():
        m = updates["mobile"].strip()
        if not m.isdigit() or len(m) != 10: return False, "Invalid mobile number."
        for k,v in users.items():
            if k != username and v.get("mobile","") == m:
                return False, "Mobile already used by another account."
        u["mobile"] = m
    if updates.get("dob",""):
        age = _calc_age(updates["dob"])
        if age == 0: return False, "Invalid date of birth."
        u["dob"] = updates["dob"]; u["age"] = age
    if updates.get("new_password",""):
        if len(updates["new_password"]) < 6: return False, "Password must be at least 6 characters."
        u["password"] = hash_pw(updates["new_password"])
    users[username] = u; _save(users)
    return True, "Profile updated successfully!"

# ── Admin ops ─────────────────────────────────────────────────────────────────
def all_users(): return _load()
def get_user(username): return _load().get(username.lower().strip(), {})

def delete_user(username):
    users = _load(); username = username.lower().strip()
    if username not in users: return False, "User not found."
    del users[username]; _save(users)
    return True, f"User '{username}' deleted."

def admin_update_user(username, updates): return update_profile(username, updates)

def save_user_report(username, report_meta):
    users = _load(); username = username.lower().strip()
    if username in users:
        users[username].setdefault("reports",[]).append(report_meta)
        _save(users)