"""auth.py — Authentication using SQLite via database.py"""
import bcrypt
from datetime import datetime, date
from database import (get_all_users, get_user, user_exists, mobile_exists,
                      email_exists, create_user, update_user, delete_user_db,
                      save_finance, load_finance, save_user_report)

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

def signup(username, full_name, email, mobile, dob, password):
    username = username.lower().strip()
    mobile   = mobile.strip()
    email    = email.strip().lower()
    if len(username) < 3:         return False, "Username must be at least 3 characters."
    if " " in username:           return False, "Username cannot have spaces."
    if len(password) < 6:         return False, "Password must be at least 6 characters."
    if "@" not in email:          return False, "Invalid email address."
    if not mobile.isdigit() or len(mobile) != 10:
        return False, "Enter a valid 10-digit mobile number."
    if user_exists(username):     return False, "Username already taken."
    if mobile_exists(mobile):     return False, "Mobile number already registered."
    if email_exists(email):       return False, "Email already registered."
    ok = create_user({
        "username":   username,
        "full_name":  full_name.strip() or username,
        "email":      email,
        "mobile":     mobile,
        "dob":        dob,
        "age":        _age(dob),
        "password":   hash_pw(password),
        "created_at": datetime.now().isoformat(),
        "reports":    [],
        "finance":    {},
    })
    return (True, "Account created successfully!") if ok else (False, "Could not create account. Please try again.")

def login(username, password):
    username = username.lower().strip()
    u = get_user(username)
    if not u:                          return False, "Username not found.", {}
    if not check_pw(password, u.get("password","")): return False, "Incorrect password.", {}
    return True, "Login successful!", u

def update_profile(username, updates):
    username = username.lower().strip()
    u = get_user(username)
    if not u: return False, "User not found."
    patch = {}
    if updates.get("full_name","").strip(): patch["full_name"] = updates["full_name"].strip()
    if updates.get("email","").strip():
        e = updates["email"].strip().lower()
        if "@" not in e: return False, "Invalid email."
        if email_exists(e, exclude_username=username): return False, "Email already used by another account."
        patch["email"] = e
    if updates.get("mobile","").strip():
        m = updates["mobile"].strip()
        if not m.isdigit() or len(m) != 10: return False, "Invalid mobile number."
        if mobile_exists(m, exclude_username=username): return False, "Mobile already used by another account."
        patch["mobile"] = m
    if updates.get("dob",""):
        a = _age(updates["dob"])
        if a == 0: return False, "Invalid date of birth."
        patch["dob"] = updates["dob"]; patch["age"] = a
    if updates.get("new_password",""):
        if len(updates["new_password"]) < 6: return False, "Password must be at least 6 characters."
        patch["password"] = hash_pw(updates["new_password"])
    if patch:
        update_user(username, patch)
    return True, "Profile updated successfully!"

def all_users():              return get_all_users()
def admin_update_user(u, up): return update_profile(u, up)

def delete_user(username):
    ok = delete_user_db(username)
    return (True, f"User '{username}' deleted.") if ok else (False, "Could not delete user.")