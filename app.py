"""
FinSight v6 — Financial Advisor Portal
Features: Login/Signup · 7-page calculator · Payment-gated PDF · Admin dashboard
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import io
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime, date
from auth import (signup, login, save_user_report, all_users,
                  get_user, save_finance, load_finance, update_profile,
                  delete_user, admin_update_user)
from admin import render as render_admin

DATA_DIR    = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
SUBS_FILE   = DATA_DIR / "submissions.json"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# ░░  CONFIG  ░░
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="FinSight — Financial Advisor",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── EDIT YOUR DETAILS HERE ────────────────────────────────────────────────────
ADVISOR = {
    "name":     "Yash Wankar",
    "title":    "Financial Advisor & Consultant",
    "phone":    "+91 90286 93456",
    "whatsapp": "+91 90286 93456",
    "email":    "yashwankar@finsight.in",
    "website":  "www.finsight.in",
    "address":  "Bengaluru, Karnataka – 560001",
    "tagline":  "Helping Indians build wealth the right way — honest, experience-backed, goal-based.",
    "linkedin": "linkedin.com/in/yashwankar",
    "instagram":"@yashwankar_finance",
}

# ── ADMIN CREDENTIALS ────────────────────────────────────────────────────────
# On Streamlit Cloud: set these in App Settings → Secrets (see README)
# Locally: hardcoded below as fallback
try:
    ADMIN_USER = st.secrets["ADMIN_USER"]
    ADMIN_PASS = st.secrets["ADMIN_PASS"]
except Exception:
    ADMIN_USER = "yashwankar"
    ADMIN_PASS = "Yash@2025#FS"

PAGES = [
    "🏠  Profile & Income",
    "💸  Expenses & EMIs",
    "📈  Investments & EPF",
    "🛡️  Insurance",
    "🏦  Savings & Assets",
    "📊  Dashboard & Report",
    "🤝  Consult an Advisor",
    "👤  My Profile",
]


# ── PAYMENT CONFIG ─────────────────────────────────────────────────────────────
PAYMENT = {
    "upi_id":   "yash04@icici",
    "amount":   100,
    "whatsapp": "9028693456",
    "qr_note":  "Pay Rs.100 · UPI ID: yash04@icici",
}

# ── REPORTS FOLDER (auto-created next to app.py on the host machine) ───────────
DATA_DIR    = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
SUBS_FILE   = DATA_DIR / "submissions.json"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

def save_report_to_disk(pdf_bytes, meta):
    """Save PDF and metadata to local files. Returns filename."""
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe  = (meta.get("name","Client") or "Client").replace(" ","_")
    fname = f"{ts}_{safe}.pdf"
    try: (REPORTS_DIR / fname).write_bytes(pdf_bytes)
    except Exception: pass
    meta["pdf_file"] = fname
    meta["saved_at"] = ts
    # Save metadata to submissions log
    try:
        subs = []
        if SUBS_FILE.exists():
            try: subs = json.loads(SUBS_FILE.read_text())
            except: pass
        subs.append(meta)
        SUBS_FILE.write_text(json.dumps(subs, indent=2, ensure_ascii=False))
    except Exception: pass
    uname = meta.get("username","")
    if uname:
        save_user_report(uname, {k: meta.get(k,"") for k in ["pdf_file","saved_at","score","score_label","net_worth"]})
    return fname

# ══════════════════════════════════════════════════════════════════════════════
# ░░  CSS  ░░
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Brand ── */
.brand { font-family:'DM Serif Display',serif; font-size:2.9rem;
  background:linear-gradient(135deg,#0f2d52 0%,#0e6b4a 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  line-height:1.1; margin-bottom:0; }
.brand-tag { font-size:0.93rem; color:#64748b; font-weight:400; margin-top:2px; }

/* ── Page banner ── */
.pg-banner {
  background:linear-gradient(135deg,#0f2d52 0%,#0e6b4a 100%);
  border-radius:16px; padding:24px 32px; margin-bottom:28px; color:#fff;
  display:flex; justify-content:space-between; align-items:center;
}
.pg-banner-left h2 { font-family:'DM Serif Display',serif; font-size:1.75rem; margin:0 0 4px; color:#fff; }
.pg-banner-left p  { margin:0; font-size:0.86rem; opacity:.75; }
.pg-banner-right   { text-align:right; }
.pg-step-no { font-size:3rem; font-weight:700; opacity:.18; font-family:'DM Serif Display',serif; line-height:1; }

/* ── Metric card ── */
.mc { background:#fff; border:1px solid #e8edf2; border-top:3px solid #0e6b4a;
  border-radius:14px; padding:16px 20px; margin:5px 0;
  box-shadow:0 1px 6px rgba(0,0,0,.06); }
.mc.r  { border-top-color:#ef4444; }
.mc.a  { border-top-color:#f59e0b; }
.mc.b  { border-top-color:#3b82f6; }
.mc.p  { border-top-color:#8b5cf6; }
.mc.t  { border-top-color:#0d9488; }
.mc.o  { border-top-color:#ea580c; }
.mc-lbl{ font-size:.68rem; font-weight:700; text-transform:uppercase; letter-spacing:.07em; color:#94a3b8; margin-bottom:5px; }
.mc-val{ font-family:'JetBrains Mono',monospace; font-size:1.48rem; font-weight:600; color:#0f172a; line-height:1.1; }
.mc-sub{ font-size:.7rem; color:#64748b; margin-top:4px; }

/* ── Alert boxes ── */
.ab { border-radius:10px; padding:13px 18px; margin:5px 0; font-size:.875rem; line-height:1.6; }
.ab.g { background:#f0fdf4; border:1px solid #86efac; color:#14532d; }
.ab.a { background:#fffbeb; border:1px solid #fcd34d; color:#78350f; }
.ab.r { background:#fef2f2; border:1px solid #fca5a5; color:#7f1d1d; }
.ab.b { background:#eff6ff; border:1px solid #93c5fd; color:#1e3a8a; }
.ab.p { background:#f5f3ff; border:1px solid #c4b5fd; color:#3b0764; }

/* ── Section title ── */
.stl { font-family:'DM Serif Display',serif; font-size:1.3rem; color:#0f2d52;
  margin:28px 0 14px; padding-bottom:8px; border-bottom:2px solid #e8edf2; }

/* ── Nav strip ── */
.nav-wrap { margin-top:40px; padding-top:18px; border-top:2px solid #f0f4f8; }

/* ── Loan row ── */
.loan-row { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:10px 16px; margin:6px 0; }

/* ── Bank slot cards ── */
.bslot { border-radius:14px; padding:18px 20px; margin:6px 0; min-height:140px; color:#fff; }
.bslot.n { background:linear-gradient(145deg,#0f172a,#1e293b); }
.bslot.g { background:linear-gradient(145deg,#064e3b,#065f46); }
.bslot.p { background:linear-gradient(145deg,#2e1065,#3b0764); }
.bslot.a { background:linear-gradient(145deg,#78350f,#92400e); }
.bslot-no   { font-size:.65rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; opacity:.5; margin-bottom:4px; }
.bslot-name { font-family:'DM Serif Display',serif; font-size:1.05rem; margin-bottom:6px; }
.bslot-desc { font-size:.76rem; opacity:.7; line-height:1.45; }

/* ── Score bar ── */
.sbar { margin:5px 0; }
.sbar-hd { font-size:.72rem; font-weight:600; color:#475569; display:flex; justify-content:space-between; margin-bottom:3px; }
.sbar-bg { background:#e2e8f0; border-radius:6px; height:7px; }
.sbar-fill { height:7px; border-radius:6px; transition:width .4s; }

/* ── Download button ── */
div[data-testid="stDownloadButton"] > button {
  background:linear-gradient(135deg,#0f2d52,#0e6b4a) !important;
  color:#fff !important; border:none !important; border-radius:12px !important;
  font-weight:600 !important; font-size:1rem !important;
  padding:14px 28px !important; width:100% !important;
  letter-spacing:.02em !important; box-shadow:0 4px 14px rgba(14,107,74,.35) !important;
}
div[data-testid="stDownloadButton"] > button:hover { opacity:.9 !important; }

/* ── Primary btn ── */
div[data-testid="stButton"] > button[kind="primary"] {
  background:linear-gradient(135deg,#0f2d52,#0e6b4a) !important;
  color:#fff !important; border:none !important; border-radius:10px !important;
  font-weight:600 !important; box-shadow:0 2px 8px rgba(14,107,74,.3) !important;
}

/* ── Sidebar ── */
div[data-testid="stSidebar"] { background:#0a0f1e !important; }
div[data-testid="stSidebar"] * { color:#8899aa !important; }
div[data-testid="stSidebar"] h1,
div[data-testid="stSidebar"] h2,
div[data-testid="stSidebar"] h3 { color:#dde5ee !important; }
div[data-testid="stSidebar"] .stRadio label { color:#b0c0d0 !important; font-size:.9rem !important; }

/* ── Contact hero ── */
.chero { background:linear-gradient(135deg,#0f2d52 0%,#0e6b4a 100%);
  border-radius:18px; padding:36px 44px; color:#fff; margin-bottom:28px; }
.chero h1 { font-family:'DM Serif Display',serif; font-size:2.4rem; margin:0 0 6px; color:#fff; }
.chero p  { margin:4px 0; opacity:.8; font-size:.92rem; }
.citem  { background:#fff; border-radius:14px; padding:20px 24px; margin:8px 0;
  border:1px solid #e8edf2; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.citem-icon  { font-size:1.6rem; margin-bottom:8px; }
.citem-lbl   { font-size:.68rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#94a3b8; }
.citem-val   { font-size:1.08rem; font-weight:600; color:#0f172a; margin-top:2px; }
.citem-note  { font-size:.73rem; color:#64748b; margin-top:3px; }
.svc { background:#fff; border:1px solid #e8edf2; border-radius:14px; padding:24px; margin:8px 0; border-top:4px solid #0e6b4a; }
.svc.b { border-top-color:#3b82f6; }
.svc.p { border-top-color:#8b5cf6; }
.svc-ttl { font-weight:700; color:#0f172a; font-size:1.02rem; margin-bottom:7px; }
.svc-dsc { color:#475569; font-size:.84rem; line-height:1.6; }
.svc-prc { font-family:'JetBrains Mono',monospace; color:#0e6b4a; font-weight:700; font-size:.95rem; margin-top:12px; }

/* ── Insight cards on dashboard ── */
.insight-strip { display:flex; gap:8px; flex-wrap:wrap; margin:8px 0; }
.itag { display:inline-block; padding:4px 12px; border-radius:20px; font-size:.73rem;
  font-weight:600; letter-spacing:.04em; }
.itag.g { background:#dcfce7; color:#15803d; }
.itag.a { background:#fef9c3; color:#854d0e; }
.itag.r { background:#fee2e2; color:#b91c1c; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ░░  SESSION DEFAULTS  ░░
# ══════════════════════════════════════════════════════════════════════════════
DEFS = {
    "pg": 0,
    "auth_logged_in": False,
    "auth_user": "",
    "auth_role": "user",
    "auth_full_name": "",
    "auth_email": "",
    "auth_mobile": "",
    "auth_dob": "",
    # otp state
    "otp_sent": False,
    "otp_identifier": "",
    "otp_pending_user": {},
    # finance persistence
    "finance_loaded": False,
    # profile
    "name":"", "age":28, "city":"Bengaluru",
    "occupation":"Salaried (Private)", "dependents":0, "marital":"Single",
    # income
    "salary":0, "other_income":0, "annual_bonus":0,
    # expenses
    "rent":0,"groceries":0,"utilities":0,"transport":0,
    "dining":0,"entertainment":0,"education":0,"other_exp":0,
    "emis":[],
    # investments
    "sip":0,"sip_rate":12.0,"stocks":0,"elss":0,"ppf":0,"nps":0,"other_inv":0,
    "existing_stocks":0,"existing_ppf":0,"existing_nps":0,
    # EPF
    "has_epf":False,"epf_basic":0,"epf_pct":12,"epf_rate":8.15,
    "epf_yrs":30,"epf_existing":0,"epf_emp_mo":0,"epf_proj":0,
    # insurance
    "has_ins":False,"insurances":[],"ins_prem":0,
    # assets
    "cash":0,"banks":1,"has_credit_card":False,"fd":0,"fd_rate":6.8,"fd_yrs":3,
    "gold_g":0.0,"gold_px":7400,"mf":0,"realty":0,"ef_mo":6,
    # retirement
    "ret_age":60,"ret_ret":12.0,"inflation":6.0,
    # report state
    "pdf_ready":False,"pdf_bytes":None,"pdf_filename":"",
}
for k, v in DEFS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# ░░  HELPERS  ░░
# ══════════════════════════════════════════════════════════════════════════════
def fmt(n):
    n = float(n)
    if abs(n) >= 1e7: return f"₹{n/1e7:.2f} Cr"
    if abs(n) >= 1e5: return f"₹{n/1e5:.2f} L"
    return f"₹{n:,.0f}"

def fmtr(n): return f"₹{float(n):,.0f}"
def pct(a, b): return f"{a/b*100:.1f}%" if b else "—"

def sipfv(mo, rpa, yr):
    r = rpa / 1200; n = yr * 12
    if r == 0: return mo * n
    return mo * (((1+r)**n - 1)/r) * (1+r)

def fdfv(p, r, yr): return p * ((1+r/100)**yr)

def hbadge(sc):
    if sc >= 75: return "🟢", "Excellent"
    if sc >= 55: return "🟡", "Good"
    if sc >= 35: return "🟠", "Needs Work"
    return "🔴", "Critical"

def ins_advice(age):
    if age < 26: return "Best time to buy! Premiums are at their lowest now. Lock in a 30-year Term Life plan + Health cover today — waiting even 5 years can cost 30% more."
    if age < 36: return "Act now before premiums rise. A Term plan (₹1 Cr+) + ₹10L Health Insurance + Critical Illness rider is the essential foundation."
    if age < 46: return "Premiums rise sharply post-40. Get Term + Health + Critical Illness immediately. With dependents, aim for ₹1.5–2 Cr life cover."
    return "Focus on Health Insurance (₹15–25L, Super Top-up) + Personal Accident + Annuity planning. Term may be expensive — explore TATA or Bajaj."

def go_page(delta):
    # Reset auto-save flag if navigating to dashboard so fresh data saves
    new_pg = max(0, min(len(PAGES)-1, st.session_state.pg + delta))
    if new_pg != st.session_state.pg:
        st.session_state.auto_saved = False
    st.session_state.pg = new_pg
    st.rerun()

# ── Nav buttons (bottom of every page) ───────────────────────────────────────
def nav(back_label="← Back", next_label="Save & Continue →", show_back=True, show_next=True):
    st.markdown('<div class="nav-wrap"></div>', unsafe_allow_html=True)
    l, m, r = st.columns([1, 4, 1])
    with l:
        if show_back and st.session_state.pg > 0:
            if st.button(back_label, use_container_width=True, key=f"back_{st.session_state.pg}"):
                go_page(-1)
    with m:
        # progress dots
        dots = ""
        for i in range(len(PAGES)):
            if i == st.session_state.pg:
                dots += '<span style="display:inline-block;width:20px;height:7px;background:#0e6b4a;border-radius:4px;margin:0 2px;vertical-align:middle"></span>'
            elif i < st.session_state.pg:
                dots += '<span style="display:inline-block;width:7px;height:7px;background:#0e6b4a;opacity:.5;border-radius:50%;margin:0 2px;vertical-align:middle"></span>'
            else:
                dots += '<span style="display:inline-block;width:7px;height:7px;background:#e2e8f0;border-radius:50%;margin:0 2px;vertical-align:middle"></span>'
        st.markdown(f'<div style="text-align:center;padding:10px 0">{dots}<br><span style="font-size:.72rem;color:#94a3b8">Step {st.session_state.pg+1} of {len(PAGES)}</span></div>', unsafe_allow_html=True)
    with r:
        if show_next and st.session_state.pg < len(PAGES)-1:
            if st.button(next_label, type="primary", use_container_width=True, key=f"next_{st.session_state.pg}"):
                go_page(+1)

# ── Derived totals (used across pages & PDF) ──────────────────────────────────
def totals():
    s = st.session_state
    total_emi = sum(e["amount"] for e in s.emis)
    total_exp = s.rent + s.groceries + s.utilities + s.transport + s.dining + s.entertainment + s.education + s.other_exp + total_emi
    total_inv = s.sip + s.stocks + s.elss + s.ppf + s.nps + s.other_inv + s.epf_emp_mo
    ti = s.salary + s.other_income
    gold_val = s.gold_g * s.gold_px
    ta = s.cash + s.fd + gold_val + s.mf + s.realty
    total_outst = sum(e["outstanding"] for e in s.emis)
    surplus = ti - total_exp - total_inv - s.ins_prem
    return dict(ti=ti, total_emi=total_emi, total_exp=total_exp,
                total_inv=total_inv, gold_val=gold_val,
                ta=ta, total_outst=total_outst,
                net_worth=ta - total_outst, surplus=surplus,
                ef_target=total_exp * s.ef_mo)

def compute_score(t):
    s = st.session_state
    ti = t["ti"]; score = 0; sb = []
    if ti <= 0: return 0, []
    inv_r = t["total_inv"]/ti; exp_r = t["total_exp"]/ti; emi_r = t["total_emi"]/ti
    if inv_r >= .20:   score+=25; sb.append(("Investment Rate",25,25,f"{inv_r*100:.0f}% ✅"))
    elif inv_r >= .10: score+=12; sb.append(("Investment Rate",12,25,f"{inv_r*100:.0f}% ⚠️"))
    else:                          sb.append(("Investment Rate", 0,25,f"{inv_r*100:.0f}% 🚨"))
    if exp_r <= .50:   score+=20; sb.append(("Expense Control",20,20,f"{exp_r*100:.0f}% on expenses ✅"))
    elif exp_r <= .70: score+=10; sb.append(("Expense Control",10,20,f"{exp_r*100:.0f}% on expenses ⚠️"))
    else:                          sb.append(("Expense Control", 0,20,f"{exp_r*100:.0f}% on expenses 🚨"))
    if s.has_ins:   score+=20; sb.append(("Insurance",20,20,"Covered ✅"))
    else:                       sb.append(("Insurance", 0,20,"No insurance 🚨"))
    cash = s.cash; ef = t["ef_target"]
    if cash >= ef:           score+=15; sb.append(("Emergency Fund",15,15,f"{cash/max(t['total_exp'],1):.1f} mo ✅"))
    elif cash >= ef*.5:      score+=8;  sb.append(("Emergency Fund", 8,15,"Half funded ⚠️"))
    else:                               sb.append(("Emergency Fund", 0,15,"Underfunded 🚨"))
    if emi_r <= .35:  score+=10; sb.append(("Debt Load",10,10,f"EMIs {emi_r*100:.0f}% ✅"))
    elif emi_r <= .50: score+=5; sb.append(("Debt Load", 5,10,f"EMIs {emi_r*100:.0f}% ⚠️"))
    else:                          sb.append(("Debt Load", 0,10,f"EMIs {emi_r*100:.0f}% 🚨"))
    if t["surplus"] > 0: score+=10; sb.append(("Monthly Surplus",10,10,f"+{fmtr(t['surplus'])} ✅"))
    else:                             sb.append(("Monthly Surplus", 0,10,f"Deficit {fmtr(abs(t['surplus']))} 🚨"))
    return min(100, score), sb

def gen_insights(t, score):
    s = st.session_state; ti = t["ti"]
    ins, warn, dng = [], [], []
    if ti <= 0: return ins, warn, dng
    inv_p = t["total_inv"]/ti*100; exp_p = t["total_exp"]/ti*100; emi_p = t["total_emi"]/ti*100
    if inv_p >= 25:    ins.append(f"✅ Outstanding! You invest {inv_p:.0f}% of income — top tier wealth builder.")
    elif inv_p >= 20:  ins.append(f"✅ You invest {inv_p:.0f}% — right on target. Keep compounding!")
    elif inv_p >= 10: warn.append(f"📊 Investing {inv_p:.0f}%. Aim for 20% — that's ₹{int(ti*.2-t['total_inv']):,}/month more. Automate it on salary day.")
    else:              dng.append(f"🚨 Only {inv_p:.0f}% invested. Wealth creation requires consistency. Even ₹500/month in SIP beats zero.")
    if exp_p > 70:    dng.append(f"🚨 Expenses {exp_p:.0f}% of income — critical. Review dining (₹{s.dining:,}) and entertainment (₹{s.entertainment:,}) first.")
    elif exp_p > 50: warn.append(f"💸 Expenses at {exp_p:.0f}%. Cutting ₹2,000/month = ₹24K/year = ~₹5L in 10 years at 12% returns.")
    else:              ins.append(f"✅ Expenses {exp_p:.0f}% — well controlled.")
    if emi_p > 40:    dng.append(f"🏦 EMI burden {emi_p:.0f}% — above the 35% safe limit. Prepay the highest-interest loan first.")
    elif emi_p > 0:    ins.append(f"✅ EMI ratio {emi_p:.0f}% — within healthy limits (<35%).")
    if s.cash >= t["ef_target"]: ins.append(f"✅ Emergency fund ({fmt(s.cash)}) covers {s.cash/max(t['total_exp'],1):.1f} months. Rock solid!")
    elif t["ef_target"] > 0:    warn.append(f"🛡️ Emergency fund gap: {fmt(max(0,t['ef_target']-s.cash))} short of {s.ef_mo}-month target ({fmt(t['ef_target'])}).")
    if t["surplus"] < 0:  dng.append(f"🚨 Monthly deficit of {fmtr(abs(t['surplus']))}. Depleting savings or taking on debt every month.")
    elif t["surplus"] > 0: ins.append(f"✅ Monthly surplus {fmtr(t['surplus'])} — route to SIP top-up or loan prepayment.")
    if not s.has_ins:         dng.append("🚨 No insurance! One medical emergency can cost ₹5–20L. Get term + health cover immediately.")
    if s.banks < 3:          warn.append(f"🏦 Only {s.banks} bank account(s). Open 3–4 purpose-driven accounts for better financial discipline.")
    if s.ppf == 0 and s.nps == 0 and s.elss == 0:
        warn.append("📋 No 80C/80CCD investments. You could save up to ₹46,800/year in taxes (30% slab on ₹1.5L 80C + ₹50K NPS).")
    bad = [p for p in s.insurances if "ULIP" in p.get("type","") or "Endowment" in p.get("type","")]
    if bad: warn.append(f"⚠️ {len(bad)} ULIP/Endowment policy/policies detected (4–6% returns). Consider switching to Term + SIP for significantly better wealth creation.")
    gold_pct = t["gold_val"]/t["ta"]*100 if t["ta"] else 0
    if gold_pct > 15: warn.append(f"🥇 Gold is {gold_pct:.0f}% of assets. Cap it at 5–10%. Consider Sovereign Gold Bonds (SGBs) — same exposure + 2.5% annual interest.")
    return ins, warn, dng


# ══════════════════════════════════════════════════════════════════════════════
# ░░  PDF GENERATOR  ░░
# ══════════════════════════════════════════════════════════════════════════════
def build_pdf(t, score, sb, ins, warn, dng):
    s    = st.session_state
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=18*mm, rightMargin=18*mm,
                              topMargin=16*mm, bottomMargin=16*mm)
    W    = 174*mm
    GRN  = colors.HexColor("#0e6b4a")
    NAV  = colors.HexColor("#0f2d52")
    AMB  = colors.HexColor("#f59e0b")
    RED  = colors.HexColor("#ef4444")
    LGR  = colors.HexColor("#f8fafc")
    GRY  = colors.HexColor("#64748b")
    BLK  = colors.HexColor("#0f172a")
    WHT  = colors.white
    LGRE = colors.HexColor("#dcfce7")
    LAMB = colors.HexColor("#fffbeb")
    LRED = colors.HexColor("#fef2f2")
    LBLU = colors.HexColor("#eff6ff")
    now  = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # ── Paragraph styles ──────────────────────────────────────────────────────
    def ps(name, font="Helvetica", size=9, color=BLK, align=TA_LEFT, leading=None, bold=False):
        return ParagraphStyle(name, fontName=f"Helvetica{'-Bold' if bold else ''}", fontSize=size,
                              textColor=color, alignment=align, leading=leading or size*1.4)
    H1   = ps("H1",  size=22, color=WHT, bold=True,   leading=26)
    H1S  = ps("H1S", size=12, color=colors.HexColor("#a7f3d0"), leading=16)
    H2   = ps("H2",  size=14, color=NAV, bold=True,   leading=18)
    H3   = ps("H3",  size=11, color=NAV, bold=True,   leading=14)
    H3G  = ps("H3G", size=11, color=GRN, bold=True,   leading=14)
    BD   = ps("BD",  size=9,  color=BLK, bold=True)
    BO   = ps("BO",  size=9,  color=BLK)
    SM   = ps("SM",  size=8,  color=GRY)
    CTR  = ps("CTR", size=9,  color=BLK, align=TA_CENTER)
    RGT  = ps("RGT", size=9,  color=BLK, align=TA_RIGHT)
    WHTB = ps("WHTB",size=9,  color=WHT, bold=True)
    WHT9 = ps("WHT9",size=9,  color=WHT)

    story = []

    # ─── helpers inside PDF ─────────────────────────────────────────────────
    def hr(thick=1.5, color=GRN, after=3):
        story.append(HRFlowable(width=W, thickness=thick, color=color, spaceAfter=after*mm))

    def section(title, n=""):
        story.append(Spacer(1, 5*mm))
        hr()
        prefix = f"{n}. " if n else ""
        story.append(Paragraph(f"{prefix}{title}", H2))
        story.append(Spacer(1, 2*mm))

    def kv(rows, widths=None):
        if not widths: widths = [W*.54, W*.46]
        data = [[Paragraph(str(k), BD), Paragraph(str(v), RGT)] for k, v in rows]
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHT, LGR]),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(t); story.append(Spacer(1,2*mm))

    def metric_row(metrics):
        n = len(metrics); cw = W/n
        row0 = [Paragraph(m[0], ps(f"mlbl{i}", size=8, color=GRY, align=TA_CENTER)) for i,m in enumerate(metrics)]
        row1 = [Paragraph(m[1], ps(f"mval{i}", size=12, color=colors.HexColor(m[2]), align=TA_CENTER, bold=True, leading=15)) for i,m in enumerate(metrics)]
        tb = Table([row0,row1], colWidths=[cw]*n)
        tb.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),LGR),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
            ("ALIGN",(0,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(tb); story.append(Spacer(1,3*mm))

    def ibox(text, bg):
        tb = Table([[Paragraph(text, BO)]], colWidths=[W])
        tb.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#d1d5db")),
            ("LEFTPADDING",(0,0),(-1,-1),10), ("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),6),  ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(tb); story.append(Spacer(1,1.5*mm))

    # ════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ════════════════════════════════════════════════════════════════════════
    cover = Table([[
        Paragraph("FinSight", H1),
        Paragraph("Personal Financial Report", H1S),
    ]], colWidths=[W*.55, W*.45])
    cover.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAV),
        ("TOPPADDING",(0,0),(-1,-1),26), ("BOTTOMPADDING",(0,0),(-1,-1),26),
        ("LEFTPADDING",(0,0),(-1,-1),18), ("RIGHTPADDING",(0,0),(-1,-1),18),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(cover); story.append(Spacer(1,6*mm))

    s_ico, s_lbl = hbadge(score)
    client_rows = [
        ("Prepared for", s.name or "—", "Report Date", now),
        ("Age", f"{s.age} years", "City", s.city),
        ("Occupation", s.occupation, "Dependents", str(s.dependents)),
        ("Marital Status", s.marital, "Financial Health Score", f"{s_ico} {score}/100 ({s_lbl})"),
    ]
    for row in client_rows:
        tb = Table([[Paragraph(row[0],BD), Paragraph(row[1],BO),
                     Paragraph(row[2],BD), Paragraph(row[3],BO)]],
                   colWidths=[W*.22, W*.28, W*.24, W*.26])
        tb.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHT,LGR]),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(tb)

    story.append(Spacer(1,5*mm))
    # Executive summary box
    surplus_sign = "+" if t["surplus"] >= 0 else "-"
    exec_data = [
        ["Monthly Income", "Total Expenses", "Investments", "Monthly Surplus", "Net Worth"],
        [fmt(t["ti"]), fmt(t["total_exp"]), fmt(t["total_inv"]), f"{surplus_sign}{fmt(abs(t['surplus']))}", fmt(t["net_worth"])],
    ]
    exec_tb = Table(exec_data, colWidths=[W/5]*5)
    exec_tb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAV),   ("TEXTCOLOR",(0,0),(-1,0),WHT),
        ("BACKGROUND",(0,1),(-1,1),LGR),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0),8),
        ("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"), ("FONTSIZE",(0,1),(-1,1),12),
        ("TEXTCOLOR",(0,1),(-1,1),NAV),
        ("ALIGN",(0,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#e2e8f0")),
        ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(exec_tb)

    # ════════════════════════════════════════════════════════════════════════
    # 1. INCOME
    # ════════════════════════════════════════════════════════════════════════
    section("INCOME SUMMARY", "1")
    metric_row([
        ("Monthly Take-Home", fmtr(s.salary), "#0e6b4a"),
        ("Other Income / Month", fmtr(s.other_income), "#3b82f6"),
        ("Total Monthly Income", fmtr(t["ti"]), "#0f2d52"),
        ("Annual Income (incl. bonus)", fmt(t["ti"]*12+s.annual_bonus), "#8b5cf6"),
    ])

    # ════════════════════════════════════════════════════════════════════════
    # 2. EXPENSES
    # ════════════════════════════════════════════════════════════════════════
    section("MONTHLY EXPENSES", "2")
    exp_color = "#ef4444" if t["total_exp"] > t["ti"]*.7 else "#f59e0b"
    metric_row([
        ("Fixed Expenses", fmt(s.rent+s.groceries+s.utilities+s.transport+t["total_emi"]), "#0f2d52"),
        ("Variable Expenses", fmt(s.dining+s.entertainment+s.education+s.other_exp), "#8b5cf6"),
        ("Total EMIs", fmt(t["total_emi"]), "#f59e0b"),
        ("Total Monthly Expenses", fmt(t["total_exp"]), exp_color),
    ])
    kv([
        ("Rent / Home Loan", fmtr(s.rent)), ("Groceries & Household", fmtr(s.groceries)),
        ("Utilities", fmtr(s.utilities)), ("Transport", fmtr(s.transport)),
        ("Dining & Food Delivery", fmtr(s.dining)), ("Entertainment / OTT", fmtr(s.entertainment)),
        ("Education / Courses", fmtr(s.education)), ("Other Expenses", fmtr(s.other_exp)),
        ("Total Active EMIs", fmtr(t["total_emi"])), ("% of Income", pct(t["total_exp"], t["ti"])),
    ])
    if s.emis:
        story.append(Paragraph("Active Loans", H3))
        hdr = [Paragraph(h, WHTB) for h in ["Loan","EMI/month","Months Left","Rate %","Outstanding"]]
        rows = [hdr] + [[Paragraph(e["name"],BO), Paragraph(fmtr(e["amount"]),BO),
                          Paragraph(str(e["months_left"]),CTR), Paragraph(f'{e["rate"]}%',CTR),
                          Paragraph(fmtr(e["outstanding"]),RGT)] for e in s.emis]
        lt = Table(rows, colWidths=[W*.32, W*.18, W*.14, W*.14, W*.22])
        lt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAV), ("TEXTCOLOR",(0,0),(-1,0),WHT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHT,LGR]),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
            ("ALIGN",(1,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(lt)

    # ════════════════════════════════════════════════════════════════════════
    # 3. INVESTMENTS & EPF
    # ════════════════════════════════════════════════════════════════════════
    section("INVESTMENTS & EPF", "3")
    metric_row([
        ("SIP / Mutual Funds", fmtr(s.sip), "#0e6b4a"),
        ("Direct Stocks", fmtr(s.stocks), "#3b82f6"),
        ("ELSS", fmtr(s.elss), "#8b5cf6"),
        ("PPF + NPS", fmtr(s.ppf+s.nps), "#0d9488"),
    ])
    kv([
        ("SIP — Mutual Funds (₹/month)", fmtr(s.sip)),
        ("Direct Stocks (₹/month)", fmtr(s.stocks)),
        ("ELSS — Tax Saving MF", fmtr(s.elss)),
        ("PPF (₹/month)", fmtr(s.ppf)),
        ("NPS (₹/month)", fmtr(s.nps)),
        ("Other Investments", fmtr(s.other_inv)),
        ("EPF — Employee Share/month", fmtr(s.epf_emp_mo)),
        ("Total Monthly Investment", fmtr(t["total_inv"])),
        ("Investment as % of Income", pct(t["total_inv"], t["ti"])),
        ("EPF Projected Corpus", fmt(s.epf_proj)),
    ])
    if s.sip > 0:
        sip15 = sipfv(s.sip, s.sip_rate, 15)
        sip20 = sipfv(s.sip, s.sip_rate, 20)
        sip30 = sipfv(s.sip, s.sip_rate, 30)
        story.append(Paragraph("SIP Growth Projections", H3))
        proj_hdr = [Paragraph(h, WHTB) for h in ["Period","Amount Invested","Projected Value","Gain","XIRR"]]
        proj_rows = [proj_hdr] + [
            [Paragraph(yr,BO), Paragraph(fmt(s.sip*int(yr.split()[0])*12),BO),
             Paragraph(fmt(fv),BD), Paragraph(fmt(fv-s.sip*int(yr.split()[0])*12),BO),
             Paragraph(f"{s.sip_rate}%",CTR)]
            for yr, fv in [("15 Years",sip15),("20 Years",sip20),("30 Years",sip30)]
        ]
        pt = Table(proj_rows, colWidths=[W*.16, W*.2, W*.22, W*.22, W*.2])
        pt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAV), ("TEXTCOLOR",(0,0),(-1,0),WHT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHT,LGR]),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
            ("ALIGN",(1,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(pt)

    # ════════════════════════════════════════════════════════════════════════
    # 4. INSURANCE
    # ════════════════════════════════════════════════════════════════════════
    section("INSURANCE COVERAGE", "4")
    if s.has_ins and s.insurances:
        life_cov   = sum(p.get("cover_l",0) for p in s.insurances if any(k in p.get("type","") for k in ["Life","Term","ULIP","Endow","Whole"]))
        health_cov = sum(p.get("cover_l",0) for p in s.insurances if any(k in p.get("type","") for k in ["Health","Mediclaim"]))
        metric_row([
            ("Total Monthly Premium", fmtr(s.ins_prem), "#0f2d52"),
            ("No. of Policies", str(len(s.insurances)), "#3b82f6"),
            ("Life Cover", f"₹{life_cov}L", "#0e6b4a"),
            ("Health Cover", f"₹{health_cov}L", "#8b5cf6"),
        ])
        ins_hdr = [Paragraph(h, WHTB) for h in ["Policy Type","Insurer","Premium/mo","Cover (₹L)"]]
        ins_rows = [ins_hdr] + [[Paragraph(p.get("type","—"),BO), Paragraph(p.get("insurer","—"),BO),
                                  Paragraph(fmtr(p.get("premium",0)),CTR), Paragraph(str(p.get("cover_l",0)),CTR)]
                                 for p in s.insurances]
        it = Table(ins_rows, colWidths=[W*.38, W*.22, W*.2, W*.2])
        it.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAV), ("TEXTCOLOR",(0,0),(-1,0),WHT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHT,LGR]),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
            ("ALIGN",(2,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(it)
        rec_cover = int(s.salary*12*10/100000)
        if life_cov < rec_cover and life_cov > 0:
            ibox(f"⚠️ Life cover (₹{life_cov}L) below recommended ₹{rec_cover}L (10× annual income). Consider a top-up term plan.", LAMB)
        if health_cov < 10 and health_cov > 0:
            ibox(f"⚠️ Health cover ₹{health_cov}L may be insufficient. Medical inflation ~14%/yr. Aim for ₹10L+.", LAMB)
        if health_cov == 0:
            ibox("🚨 No health insurance detected. One hospitalisation can cost ₹3–15L. Get cover immediately.", LRED)
    else:
        ibox(f"🚨 No insurance! You are financially exposed. Get Term + Health cover immediately.", LRED)
        ibox(ins_advice(s.age), LBLU)

    # ════════════════════════════════════════════════════════════════════════
    # 5. SAVINGS & ASSETS
    # ════════════════════════════════════════════════════════════════════════
    section("SAVINGS & ASSETS", "5")
    metric_row([
        ("Cash / Savings", fmt(s.cash), "#3b82f6"),
        ("Fixed Deposits", fmt(s.fd), "#0e6b4a"),
        ("Gold", fmt(t["gold_val"]), "#f59e0b"),
        ("Mutual Funds (corpus)", fmt(s.mf), "#8b5cf6"),
    ])
    kv([
        ("Cash / Savings Account Balance", fmtr(s.cash)),
        ("Number of Bank Accounts", str(s.banks)),
        ("Fixed Deposits", fmtr(s.fd)),
        ("FD Interest Rate", f"{s.fd_rate}% p.a."),
        ("FD Tenure", f"{s.fd_yrs} years"),
        ("FD Maturity Value", fmt(fdfv(s.fd, s.fd_rate, s.fd_yrs))),
        ("Gold Holdings", f"{s.gold_g:.1f} grams"),
        ("Gold Value (@₹{s.gold_px}/g)", fmtr(t["gold_val"])),
        ("Mutual Fund Portfolio", fmtr(s.mf)),
        ("Real Estate Value", fmtr(s.realty)),
        ("Total Assets", fmt(t["ta"])),
        ("Total Outstanding Liabilities", fmt(t["total_outst"])),
        ("Net Worth", fmt(t["net_worth"])),
        ("Emergency Fund Coverage", f"{s.cash/max(t['total_exp'],1):.1f} months (target: {s.ef_mo} months)"),
    ])
    if s.banks < 3:
        ibox(f"⚠️ Only {s.banks} bank account(s). Open 3–4 purpose-driven accounts: Salary · Emergency · Investment · Expenses. This creates automatic financial discipline.", LAMB)

    # ════════════════════════════════════════════════════════════════════════
    # 6. HEALTH SCORE
    # ════════════════════════════════════════════════════════════════════════
    section("FINANCIAL HEALTH SCORE", "6")
    sc_hdr = [Paragraph(h, WHTB) for h in ["Category","Score Earned","Max Score","Status"]]
    sc_rows = [sc_hdr]
    for cat, got, mx, note in sb:
        c = "#0e6b4a" if got==mx else "#f59e0b" if got>0 else "#ef4444"
        sc_rows.append([Paragraph(cat,BO),
                         Paragraph(str(got), ps("sv", size=11, color=colors.HexColor(c), bold=True, align=TA_CENTER)),
                         Paragraph(str(mx), CTR), Paragraph(note,BO)])
    sc_tb = Table(sc_rows, colWidths=[W*.3, W*.16, W*.14, W*.4])
    sc_tb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAV), ("TEXTCOLOR",(0,0),(-1,0),WHT),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHT,LGR]),
        ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
        ("ALIGN",(1,0),(2,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(sc_tb)
    total_score_bar = Table([[
        Paragraph("OVERALL FINANCIAL HEALTH SCORE", ps("tot", size=10, color=WHT, bold=True)),
        Paragraph(f"{s_ico}  {score} / 100  —  {s_lbl}",
                  ps("totv", size=12, color=WHT, bold=True, align=TA_RIGHT, leading=15)),
    ]], colWidths=[W*.6, W*.4])
    total_score_bar.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAV), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),10), ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),14), ("RIGHTPADDING",(0,0),(-1,-1),14),
    ]))
    story.append(Spacer(1,3*mm)); story.append(total_score_bar)

    # ════════════════════════════════════════════════════════════════════════
    # 7. INSIGHTS
    # ════════════════════════════════════════════════════════════════════════
    section("KEY INSIGHTS & ACTION ITEMS", "7")
    for msg in ins:  ibox(msg, LGRE)
    for msg in warn: ibox(msg, LAMB)
    for msg in dng:  ibox(msg, LRED)

    # ════════════════════════════════════════════════════════════════════════
    # 8. RETIREMENT PROJECTION
    # ════════════════════════════════════════════════════════════════════════
    section("RETIREMENT PROJECTION", "8")
    ytr   = max(0, s.ret_age - s.age)
    rr    = s.ret_ret
    sip_c = sipfv(s.sip + s.stocks + s.elss, rr, ytr)
    ppf_c = sipfv(s.ppf, 7.1, ytr)
    nps_c = sipfv(s.nps, 10.0, ytr)
    mf_c  = s.mf * ((1+rr/100)**ytr)
    epf_c = s.epf_proj
    tot_c = sip_c + ppf_c + nps_c + mf_c + epf_c
    fut_e = t["total_exp"] * .8 * ((1+s.inflation/100)**ytr)
    need  = fut_e * 12 * 25
    gap   = tot_c - need
    metric_row([
        ("Years to Retire", str(ytr), "#0f2d52"),
        ("Projected Corpus", fmt(tot_c), "#0e6b4a"),
        ("Corpus Needed", fmt(need), "#f59e0b"),
        ("Surplus / (Shortfall)", fmt(gap), "#0e6b4a" if gap>=0 else "#ef4444"),
    ])
    kv([
        ("Target Retirement Age", str(s.ret_age)),
        ("Years to Retirement", str(ytr)),
        ("Expected Portfolio Return", f"{rr}% p.a."),
        ("Assumed Inflation", f"{s.inflation}% p.a."),
        ("SIP + Stocks + ELSS Corpus", fmt(sip_c)),
        ("PPF Corpus (at 7.1%)", fmt(ppf_c)),
        ("NPS Corpus (at 10%)", fmt(nps_c)),
        ("EPF Projected Corpus", fmt(epf_c)),
        ("Existing MF Portfolio (grown)", fmt(mf_c)),
        ("TOTAL Projected Retirement Corpus", fmt(tot_c)),
        ("Monthly Expenses at Retirement (inflated)", fmt(fut_e)),
        ("Corpus Required (25× Annual Expenses)", fmt(need)),
        ("Surplus / (Shortfall)", fmt(gap)),
    ])
    if gap < 0:
        ibox(f"⚠️ To close the retirement shortfall, invest an additional {fmt(abs(gap)/(sipfv(1,rr,ytr) or 1))}/month in equity SIP starting today.", LAMB)

    # ════════════════════════════════════════════════════════════════════════
    # 9. ADVISOR CONTACT (FULL PAGE LAST)
    # ════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # ── Green header banner ──────────────────────────────────────────────────
    banner = Table([[
        Paragraph(f"Get a Personalised Financial Plan", ps("bh", size=18, color=WHT, bold=True, leading=22)),
        Paragraph(f"Connect with {ADVISOR['name']}", ps("bs", size=10, color=colors.HexColor("#a7f3d0"), align=TA_RIGHT, leading=13)),
    ]], colWidths=[W*.62, W*.38])
    banner.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAV),
        ("TOPPADDING",(0,0),(-1,-1),20), ("BOTTOMPADDING",(0,0),(-1,-1),20),
        ("LEFTPADDING",(0,0),(-1,-1),18), ("RIGHTPADDING",(0,0),(-1,-1),18),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(banner); story.append(Spacer(1,5*mm))

    story.append(Paragraph(
        f"A financial report shows you the numbers. A financial advisor helps you <b>act</b> on them. "
        f"{ADVISOR['name']} ({ADVISOR['title']}) offers fee-only, unbiased advice — no commissions, no conflicts.",
        ps("adv_intro", size=10, leading=14, color=BLK)
    ))
    story.append(Spacer(1,5*mm))

    # ── Advisor contact table ────────────────────────────────────────────────
    story.append(Paragraph("CONTACT DETAILS", H2))
    hr(thick=1)
    kv([
        ("Name & Designation",    f"{ADVISOR['name']}  |  {ADVISOR['title']}"),
        ("📱  Phone",              ADVISOR["phone"]),
        ("💬  WhatsApp",           ADVISOR["whatsapp"]),
        ("📧  Email",              ADVISOR["email"]),
        ("🌐  Website",            ADVISOR["website"]),
        ("📍  Office Location",    ADVISOR["address"]),
        ("💼  LinkedIn",           ADVISOR["linkedin"]),
        ("📸  Instagram",          ADVISOR["instagram"]),
    ])

    # ── Services block ───────────────────────────────────────────────────────
    story.append(Spacer(1,4*mm))
    story.append(Paragraph("SERVICES & PRICING", H2))
    hr(thick=1)
    svc_hdr = [Paragraph(h, WHTB) for h in ["Service","What's Included","Fee"]]
    svc_rows = [svc_hdr,
        [Paragraph("🔍 Financial Health Check",BD),
         Paragraph("Deep-dive review of income, expenses, investments, insurance & assets. Written report with prioritised action items.",BO),
         Paragraph("₹2,999\none-time",CTR)],
        [Paragraph("📋 Comprehensive Plan",BD),
         Paragraph("Full goal-based plan: retirement, education, home purchase, tax optimisation, insurance restructuring, portfolio strategy.",BO),
         Paragraph("₹7,999\none-time",CTR)],
        [Paragraph("🔄 Annual Advisory",BD),
         Paragraph("Quarterly reviews, unlimited consultations, portfolio rebalancing, dedicated advisor for all financial decisions year-round.",BO),
         Paragraph("₹14,999\n/ year",CTR)],
    ]
    sv_tb = Table(svc_rows, colWidths=[W*.24, W*.56, W*.2])
    sv_tb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAV), ("TEXTCOLOR",(0,0),(-1,0),WHT),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHT,LGR]),
        ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#e2e8f0")),
        ("VALIGN",(0,0),(-1,-1),"TOP"), ("ALIGN",(2,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(sv_tb)

    # ── CTA box ──────────────────────────────────────────────────────────────
    story.append(Spacer(1,6*mm))
    cta_text = (
        f"📞  Book a FREE 15-minute Discovery Call — No commitment, no pressure.\n"
        f"WhatsApp: <b>{ADVISOR['whatsapp']}</b>   |   Email: <b>{ADVISOR['email']}</b>   |   Web: <b>{ADVISOR['website']}</b>\n"
        f"We'll understand your situation and tell you honestly if and how we can help."
    )
    cta_tb = Table([[Paragraph(cta_text, ps("cta", size=10, color=colors.HexColor("#064e3b"), leading=15))]], colWidths=[W])
    cta_tb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#dcfce7")),
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#86efac")),
        ("TOPPADDING",(0,0),(-1,-1),14), ("BOTTOMPADDING",(0,0),(-1,-1),14),
        ("LEFTPADDING",(0,0),(-1,-1),16), ("RIGHTPADDING",(0,0),(-1,-1),16),
    ]))
    story.append(cta_tb)

    # ── Disclaimer ───────────────────────────────────────────────────────────
    story.append(Spacer(1,8*mm))
    hr(thick=.5, color=GRY)
    story.append(Paragraph(
        f"DISCLAIMER: This report is prepared for informational and educational purposes only and does not constitute investment advice. "
        f"All projections are based on assumed rates of return and are indicative. Actual returns may vary. "
        f"Mutual fund investments are subject to market risks. Please read all scheme-related documents carefully before investing. "
        f"This report is for informational purposes only and does not constitute investment advice. "
        f"Please consult a qualified financial professional before making investment decisions. "
        f"Report generated by FinSight on {now}. | {ADVISOR['name']} — Financial Advisor & Consultant.",
        SM))

    doc.build(story)
    return buf.getvalue()



# ══════════════════════════════════════════════════════════════════════════════
# ░░  AUTH CSS (injected into existing <style> block via extra markdown)  ░░
# ══════════════════════════════════════════════════════════════════════════════
AUTH_EXTRA_CSS = """
<style>
.auth-wrap { max-width:460px; margin:60px auto 0; }
.auth-card {
  background:#fff; border:1px solid #e2e8f0; border-radius:20px;
  padding:36px 40px; box-shadow:0 8px 32px rgba(15,45,82,.10);
}
.auth-logo {
  font-family:'DM Serif Display',serif; font-size:2.4rem;
  background:linear-gradient(135deg,#0f2d52,#0e6b4a);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  text-align:center; margin-bottom:4px;
}
.auth-sub { text-align:center; color:#64748b; font-size:.88rem; margin-bottom:28px; }
.auth-tab-active {
  background:linear-gradient(135deg,#0f2d52,#0e6b4a) !important;
  color:#fff !important; border-radius:8px !important;
  font-weight:600 !important;
}
.admin-pill {
  display:inline-block; background:#fef9c3; color:#854d0e;
  font-size:.72rem; font-weight:700; padding:2px 10px;
  border-radius:20px; letter-spacing:.04em; text-transform:uppercase;
  margin-left:8px; vertical-align:middle;
}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# ░░  AUTH GATE  ░░
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(AUTH_EXTRA_CSS, unsafe_allow_html=True)

def do_logout():
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

def _do_user_login(user):
    st.session_state.auth_logged_in = True
    st.session_state.auth_user      = user["username"]
    st.session_state.auth_role      = "user"
    st.session_state.auth_full_name = user.get("full_name", user["username"])
    st.session_state.auth_email     = user.get("email","")
    st.session_state.auth_mobile    = user.get("mobile","")
    st.session_state.auth_dob       = user.get("dob","")
    st.session_state.name           = user.get("full_name","")
    st.session_state.age            = user.get("age", 28)
    fd = load_finance(user["username"])
    for k, v in fd.items():
        st.session_state[k] = v
    st.session_state.finance_loaded = True

if not st.session_state.get("auth_logged_in", False):
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-card">
      <div class="auth-logo">💼 FinSight</div>
      <div class="auth-sub">Your Personal Financial Advisor Portal</div>
    </div>""", unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔑  Log In", "📝  Sign Up"])

    with tab_login:
        st.markdown("")
        with st.form("login_form"):
            lu = st.text_input("Username", placeholder="your username")
            lp = st.text_input("Password", type="password", placeholder="••••••••")
            st.markdown('<p style="font-size:.72rem;color:#94a3b8;text-align:center">Admin? Use your admin credentials.</p>', unsafe_allow_html=True)
            login_btn = st.form_submit_button("Log In →", type="primary", use_container_width=True)
        if login_btn:
            if lu.strip().lower() == ADMIN_USER.lower() and lp == ADMIN_PASS:
                st.session_state.auth_logged_in = True
                st.session_state.auth_user      = ADMIN_USER
                st.session_state.auth_role      = "admin"
                st.session_state.auth_full_name = "Yash Wankar"
                st.rerun()
            else:
                try:
                    ok, msg, user = login(lu.strip(), lp)
                    if ok: _do_user_login(user); st.rerun()
                    else: st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"❌ Login error: {e}")

    with tab_signup:
        st.markdown("")
        with st.form("signup_form"):
            f_name  = st.text_input("Full Name *",                          placeholder="e.g. Arjun Mehta")
            f_email = st.text_input("Email Address *",                      placeholder="you@example.com")
            f_mob   = st.text_input("Mobile Number * (10 digits, no +91)",  placeholder="9876543210")
            f_dob   = st.date_input("Date of Birth *", min_value=date(1950,1,1), max_value=date.today(), value=date(1995,1,1))
            f_user  = st.text_input("Choose Username *", placeholder="min 3 chars, no spaces")
            f_pass  = st.text_input("Password *",         type="password", placeholder="min 6 characters")
            f_pass2 = st.text_input("Confirm Password *", type="password")
            signup_btn = st.form_submit_button("Create Account →", type="primary", use_container_width=True)
        if signup_btn:
            mob = f_mob.strip().replace(" ","").replace("-","").replace("+91","")
            if f_pass != f_pass2:
                st.error("❌ Passwords do not match.")
            elif not f_name.strip():
                st.error("❌ Full name is required.")
            elif not mob.isdigit() or len(mob) != 10:
                st.error("❌ Enter a valid 10-digit mobile number.")
            else:
                ok, msg = signup(f_user.strip().lower(), f_name.strip(),
                                  f_email.strip(), mob, str(f_dob), f_pass)
                if ok: st.success(f"✅ {msg} Please log in.")
                else:  st.error(f"❌ {msg}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# ░░  ADMIN ROUTE  ░░
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("auth_role") == "admin":
    with st.sidebar:
        st.markdown("## 💼 FinSight")
        st.markdown('<span class="admin-pill">ADMIN</span>', unsafe_allow_html=True)
        st.markdown(f"Logged in as **{st.session_state.auth_full_name}**")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, key="admin_logout"):
            do_logout()
    render_admin()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# ░░  FINANCE DATA AUTO-SAVE ON EVERY PAGE CHANGE  ░░
# ══════════════════════════════════════════════════════════════════════════════
def _save_current_finance():
    """Persist all finance keys to user account."""
    finance_keys = [
        "salary","other_income","annual_bonus","rent","groceries","utilities","transport",
        "dining","entertainment","education","other_exp","emis",
        "sip","sip_rate","stocks","elss","ppf","nps","other_inv",
        "existing_stocks","existing_ppf","existing_nps",
        "has_epf","epf_basic","epf_pct","epf_rate","epf_yrs","epf_existing","epf_emp_mo","epf_proj",
        "has_ins","insurances","ins_prem",
        "cash","banks","has_credit_card","fd","fd_rate","fd_yrs",
        "gold_g","gold_px","mf","realty","ef_mo","ret_age","ret_ret","inflation",
    ]
    s  = st.session_state
    fd = {k: getattr(s, k, s.get(k, None)) for k in finance_keys if k in s}
    uname = s.get("auth_user","")
    if uname:
        save_finance(uname, fd)

# ══════════════════════════════════════════════════════════════════════════════
# ░░  SIDEBAR  ░░
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 💼 FinSight")
    st.markdown("*Your financial clarity engine*")
    st.markdown("---")
    uname_disp = st.session_state.get("auth_full_name","") or st.session_state.get("auth_user","")
    st.markdown(f"👤 **{uname_disp}**")
    st.markdown(f'<p style="font-size:.72rem;color:#64748b;margin-top:-4px">`{st.session_state.get("auth_user","")}`</p>', unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True, key="user_logout"):
        _save_current_finance()
        do_logout()
    st.markdown("---")
    chosen = st.radio("", PAGES, index=st.session_state.pg, label_visibility="collapsed")
    if PAGES.index(chosen) != st.session_state.pg:
        _save_current_finance()
        st.session_state.pg = PAGES.index(chosen)
        st.rerun()
    st.markdown("---")
    s = st.session_state
    filled = sum([bool(s.get("salary")), bool(s.get("rent") or s.get("groceries")),
                  bool(s.get("sip") or s.get("ppf") or s.get("has_epf")),
                  bool(s.get("has_ins")), bool(s.get("cash") or s.get("fd"))])
    st.progress(filled/5, text=f"Finance {filled}/5 filled")
    if s.get("salary"): st.markdown(f"💰 {fmt(s.salary+s.get('other_income',0))}/mo")
    st.markdown("---")
    st.markdown('<p style="font-size:.72rem;color:#475569;line-height:1.5">Data saved to your account.</p>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ░░  ROUTER  ░░
# ══════════════════════════════════════════════════════════════════════════════
page = PAGES[st.session_state.pg]
s    = st.session_state

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 0 — PROFILE & INCOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Profile & Income":
    st.markdown('<p class="brand">FinSight</p>', unsafe_allow_html=True)
    st.markdown('<p class="brand-tag">Understand your finances. Make better decisions. Build lasting wealth.</p>', unsafe_allow_html=True)
    st.markdown("")
    st.markdown("""<div class="pg-banner">
      <div class="pg-banner-left"><h2>Profile & Income</h2>
        <p>Tell us about yourself — this personalises every insight and recommendation.</p></div>
      <div class="pg-banner-right"><div class="pg-step-no">01</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**👤 Personal Details**")
        s.name       = st.text_input("Full Name", value=s.name, placeholder="e.g. Arjun Mehta")
        s.age        = st.number_input("Age", 18, 80, s.age)
        s.city       = st.selectbox("City", ["Bengaluru","Mumbai","Delhi","Hyderabad","Chennai","Pune","Kolkata","Ahmedabad","Jaipur","Surat","Other"])
        s.occupation = st.selectbox("Occupation", ["Salaried (Private)","Salaried (Govt/PSU)","Self-Employed / Freelancer","Business Owner","Retired","Other"])
    with c2:
        st.markdown("**👨‍👩‍👧 Family & Income**")
        s.marital    = st.selectbox("Marital Status", ["Single","Married","Married with Kids"])
        s.dependents = st.number_input("Financial Dependents (spouse, kids, parents)", 0, 10, s.get("dependents",0))
        # DOB auto-fills from profile — show age derived from DOB
        dob_str = s.get("auth_dob","")
        if dob_str:
            try:
                from datetime import date as _date
                _bd = datetime.strptime(dob_str, "%Y-%m-%d").date()
                _td = _date.today()
                _age = _td.year - _bd.year - ((_td.month, _td.day) < (_bd.month, _bd.day))
                st.session_state.age = _age
                st.markdown(f'<div class="ab g">🎂 Age auto-filled from your profile: <b>{_age} years</b> (DOB: {dob_str})</div>', unsafe_allow_html=True)
            except Exception: pass
        s.salary     = st.number_input("Take-Home Salary (₹/month)", 0, step=1000, value=s.get("salary",0), format="%d",
                                        help="Amount credited to your bank after all deductions")
        s.other_income= st.number_input("Other Income — rent, freelance, dividends (₹/month)", 0, step=500, value=s.get("other_income",0), format="%d")
        s.annual_bonus= st.number_input("Expected Annual Bonus (₹)", 0, step=5000, value=s.get("annual_bonus",0), format="%d")

    ti = s.salary + s.other_income
    if ti > 0:
        st.markdown('<p class="stl">Income Snapshot</p>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="mc"><div class="mc-lbl">Monthly Income</div><div class="mc-val">{fmtr(ti)}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mc b"><div class="mc-lbl">Annual Income</div><div class="mc-val">{fmt(ti*12+s.annual_bonus)}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mc p"><div class="mc-lbl">Daily Earnings</div><div class="mc-val">{fmtr(ti/30)}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="mc t"><div class="mc-lbl">Per Hour (8 hr/day)</div><div class="mc-val">{fmtr(ti/240)}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ab g">✅ Every rupee you save or invest represents <b>{fmtr(ti/240*1)}</b> of work. That context transforms financial decisions.</div>', unsafe_allow_html=True)

    nav(show_back=False, next_label="Continue to Expenses →")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — EXPENSES & EMIs
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💸  Expenses & EMIs":
    st.markdown("""<div class="pg-banner">
      <div class="pg-banner-left"><h2>Expenses & EMIs</h2>
        <p>Track where every rupee goes each month. Honest numbers give honest insights.</p></div>
      <div class="pg-banner-right"><div class="pg-step-no">02</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🔒 Fixed & Essential**")
        s.rent        = st.number_input("🏠 Rent / Home Loan EMI (₹)", 0, step=500, value=s.rent, format="%d")
        s.groceries   = st.number_input("🛒 Groceries & Household (₹)", 0, step=200, value=s.groceries, format="%d")
        s.utilities   = st.number_input("💡 Utilities — electricity, internet, water (₹)", 0, step=100, value=s.utilities, format="%d")
        s.transport   = st.number_input("🚗 Transport / Fuel / Metro / Cab (₹)", 0, step=100, value=s.transport, format="%d")
    with c2:
        st.markdown("**💫 Lifestyle & Variable**")
        s.dining      = st.number_input("🍽️ Dining Out / Food Delivery (₹)", 0, step=200, value=s.dining, format="%d")
        s.entertainment=st.number_input("🎬 Entertainment / OTT / Hobbies (₹)", 0, step=100, value=s.entertainment, format="%d")
        s.education   = st.number_input("📚 Education / Courses / Kids' Fees (₹)", 0, step=100, value=s.education, format="%d")
        s.other_exp   = st.number_input("📦 Other — clothing, gifts, subscriptions (₹)", 0, step=100, value=s.other_exp, format="%d")

    st.markdown('<p class="stl">🏦 Active Loan EMIs</p>', unsafe_allow_html=True)
    st.caption("Add each active loan separately — home top-up, car, personal loan, credit card, education, etc.")
    num = st.number_input("Number of active EMIs / loans", 0, 12, value=max(len(s.emis),0), step=1)
    emis = []
    for i in range(int(num)):
        prev = s.emis[i] if i < len(s.emis) else {}
        cc = st.columns([3, 2, 2, 2])
        with cc[0]: nm  = st.text_input("Loan Name", value=prev.get("name",f"Loan {i+1}"), key=f"en{i}")
        with cc[1]: amt = st.number_input("EMI ₹/mo", 0, step=500, value=prev.get("amount",0), key=f"ea{i}", format="%d")
        with cc[2]: ml  = st.number_input("Months Left", 1, 360, value=prev.get("months_left",12), key=f"el{i}")
        with cc[3]: rt  = st.number_input("Rate % p.a.", 0.0, 36.0, value=prev.get("rate",10.0), step=.5, key=f"er{i}")
        emis.append({"name":nm,"amount":amt,"months_left":ml,"rate":rt,"outstanding":amt*ml})
    s.emis = emis

    total_emi = sum(e["amount"] for e in emis)
    total_exp = s.rent+s.groceries+s.utilities+s.transport+s.dining+s.entertainment+s.education+s.other_exp+total_emi
    ti = s.salary + s.other_income
    fixed = s.rent+s.groceries+s.utilities+s.transport+total_emi
    variable = s.dining+s.entertainment+s.education+s.other_exp

    st.markdown('<p class="stl">Summary</p>', unsafe_allow_html=True)
    cc = st.columns(4)
    exp_c = "r" if total_exp>ti*.7 else "a" if total_exp>ti*.5 else ""
    with cc[0]: st.markdown(f'<div class="mc"><div class="mc-lbl">Fixed Costs</div><div class="mc-val">{fmtr(fixed)}</div></div>', unsafe_allow_html=True)
    with cc[1]: st.markdown(f'<div class="mc b"><div class="mc-lbl">Variable Costs</div><div class="mc-val">{fmtr(variable)}</div></div>', unsafe_allow_html=True)
    with cc[2]: st.markdown(f'<div class="mc {exp_c}"><div class="mc-lbl">Total Monthly</div><div class="mc-val">{fmtr(total_exp)}</div><div class="mc-sub">{pct(total_exp,ti)} of income</div></div>', unsafe_allow_html=True)
    with cc[3]: st.markdown(f'<div class="mc a"><div class="mc-lbl">Outstanding Debt</div><div class="mc-val">{fmt(sum(e["outstanding"] for e in emis))}</div></div>', unsafe_allow_html=True)

    if emis:
        # Build display df safely — ensure all keys exist
        display_rows = []
        for e in emis:
            display_rows.append({
                "Loan":                 e.get("name",""),
                "EMI/month":            f"₹{e.get('amount',0):,}",
                "Months Left":          e.get("months_left",0),
                "Rate (% p.a.)":        f"{e.get('rate',0)}%",
                "Total Payable":        f"₹{e.get('outstanding',0):,.0f}",
                "Interest Till End":    f"₹{e.get('interest_cost',0):,.0f}",
            })
        if display_rows:
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
        total_interest = sum(e.get("interest_cost",0) for e in emis)
        if total_interest > 0:
            st.markdown(f'<div class="ab a">💸 Total interest you will pay across all loans: <b>₹{total_interest:,.0f}</b>. Prepaying the highest-rate loan first saves the most.</div>', unsafe_allow_html=True)

    if total_exp > ti * .7: st.markdown('<div class="ab r">🚨 Expenses are 70%+ of income. This is critical — immediate budget review needed.</div>', unsafe_allow_html=True)
    elif total_exp > ti * .5: st.markdown('<div class="ab a">⚠️ Expenses above 50% of income. Trimming ₹2,000/month = ₹24K/year saved.</div>', unsafe_allow_html=True)

    nav(next_label="Continue to Investments →")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — INVESTMENTS & EPF
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈  Investments & EPF":
    st.markdown("""<div class="pg-banner">
      <div class="pg-banner-left"><h2>Investments & EPF</h2>
        <p>Track what you're building. Consistent investing today = financial freedom tomorrow.</p></div>
      <div class="pg-banner-right"><div class="pg-step-no">03</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📈 Market-Linked**")
        s.sip    = st.number_input("SIP — Mutual Funds (₹/month)", 0, step=500, value=s.sip, format="%d", help="ELSS SIPs qualify for 80C deduction")
        s.sip_rate = st.slider("Expected SIP Return (% p.a.)", 6.0, 20.0, s.sip_rate, .5)
        s.stocks = st.number_input("Direct Stocks — monthly buy (₹)", 0, step=500, value=s.stocks, format="%d")
        s.elss   = st.number_input("ELSS — Tax-saving MF (₹/month)  ✅ 80C", 0, step=500, value=s.elss, format="%d", help="Max ₹1.5L/year eligible; 3-yr lock-in")
    with c2:
        st.markdown("**🏛️ Debt / Guaranteed**")
        s.ppf    = st.number_input("PPF (₹/month)  ✅ 80C + Tax-free", 0, step=500, value=s.ppf, format="%d", help="7.1% p.a. tax-free; max ₹1.5L/year")
        s.nps    = st.number_input("NPS (₹/month)  ✅ 80CCD extra ₹50K", 0, step=500, value=s.get("nps",0), format="%d")
        s.other_inv=st.number_input("Other Investments (₹/month)", 0, step=500, value=s.get("other_inv",0), format="%d")
    st.markdown('<p class="stl">📦 Existing Investment Corpus (what you already have)</p>', unsafe_allow_html=True)
    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        s.existing_stocks = st.number_input("Existing Stocks Portfolio (₹)", 0, step=5000, value=s.get("existing_stocks",0), format="%d", help="Current market value of all direct stock holdings")
    with ex2:
        s.existing_ppf = st.number_input("Existing PPF Balance (₹)", 0, step=5000, value=s.get("existing_ppf",0), format="%d", help="Current PPF account balance")
    with ex3:
        s.existing_nps = st.number_input("Existing NPS Corpus (₹)", 0, step=5000, value=s.get("existing_nps",0), format="%d", help="Current NPS account balance")
    if any([s.get("existing_stocks"), s.get("existing_ppf"), s.get("existing_nps")]):
        total_existing = s.get("existing_stocks",0) + s.get("existing_ppf",0) + s.get("existing_nps",0)
        st.markdown(f'<div class="ab g">📊 Your existing investment corpus: <b>{fmt(total_existing)}</b> — this will be included in your retirement projection.</div>', unsafe_allow_html=True)

    # ── EPF ──────────────────────────────────────────────────────────────────
    st.markdown('<p class="stl">🏛️ EPF — Employee Provident Fund</p>', unsafe_allow_html=True)
    st.caption("EPF earns ~8.15% p.a. tax-free. Your employer matches 12% of your basic — that's free money!")
    s.has_epf = st.toggle("I am enrolled in EPF", value=s.has_epf)
    if s.has_epf:
        ec1, ec2 = st.columns(2)
        with ec1:
            s.epf_basic  = st.number_input("Basic Salary (₹/month)", 0, step=1000, value=s.epf_basic, format="%d", help="EPF is on basic, typically 40–60% of CTC")
            s.epf_pct    = st.slider("Your EPF Contribution (%)", 12, 100, s.epf_pct, help="12% minimum; higher = VPF — same tax-free rate!")
            s.epf_rate   = st.number_input("EPF Interest Rate (% p.a.)", 5.0, 10.0, s.epf_rate, step=.05, format="%.2f")
        with ec2:
            s.epf_existing=st.number_input("Current EPF Balance (₹)", 0, step=10000, value=s.epf_existing, format="%d", help="Check on EPFO portal / UAN passbook")
            s.epf_yrs    = st.number_input("Years to Retirement", 1, 40, s.epf_yrs)
        emp = s.epf_basic * s.epf_pct / 100
        er  = s.epf_basic * .12
        tot = emp + er
        r   = s.epf_rate/100; n = s.epf_yrs
        future = tot*12*(((1+r)**n-1)/r) if r else tot*12*n
        corpus = future + s.epf_existing*((1+r)**n)
        s.epf_emp_mo = emp; s.epf_proj = corpus
        cc = st.columns(4)
        with cc[0]: st.markdown(f'<div class="mc"><div class="mc-lbl">Your Share/month</div><div class="mc-val">{fmtr(emp)}</div></div>', unsafe_allow_html=True)
        with cc[1]: st.markdown(f'<div class="mc t"><div class="mc-lbl">Employer adds</div><div class="mc-val">{fmtr(er)}</div><div class="mc-sub">🎁 Free money!</div></div>', unsafe_allow_html=True)
        with cc[2]: st.markdown(f'<div class="mc b"><div class="mc-lbl">Total EPF/month</div><div class="mc-val">{fmtr(tot)}</div></div>', unsafe_allow_html=True)
        with cc[3]: st.markdown(f'<div class="mc p"><div class="mc-lbl">Projected Corpus ({n} yrs)</div><div class="mc-val">{fmt(corpus)}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ab g">🏛️ EPF projected corpus: <b>{fmt(corpus)}</b> at retirement — completely <b>tax-free on maturity</b>. The employer\'s 12% is essentially free salary. Max it with VPF!</div>', unsafe_allow_html=True)
    else:
        s.epf_emp_mo = 0; s.epf_proj = 0

    # ── SIP Chart ─────────────────────────────────────────────────────────────
    if s.sip > 0:
        st.markdown('<p class="stl">📈 SIP Growth Projection</p>', unsafe_allow_html=True)
        yrs = st.slider("Projection years:", 5, 30, 15)
        rows = [{"Year":y, "Invested":s.sip*y*12,
                  "Returns":sipfv(s.sip,s.sip_rate,y)-s.sip*y*12,
                  "Total":sipfv(s.sip,s.sip_rate,y)} for y in range(1,yrs+1)]
        df = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.Year, y=df.Invested, name="Amount Invested",
                                  fill="tozeroy", line=dict(color="#93c5fd",width=2), fillcolor="rgba(147,197,253,.2)"))
        fig.add_trace(go.Scatter(x=df.Year, y=df.Total, name="Portfolio Value",
                                  fill="tonexty", line=dict(color="#34d399",width=2), fillcolor="rgba(52,211,153,.25)"))
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           xaxis=dict(title="Years",gridcolor="#f1f5f9"),
                           yaxis=dict(title="₹",gridcolor="#f1f5f9"),
                           legend=dict(orientation="h",y=1.1), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        fv = sipfv(s.sip, s.sip_rate, yrs); inv = s.sip*yrs*12
        st.markdown(f'<div class="ab g">💰 ₹{s.sip:,}/mo SIP at {s.sip_rate}% → <b>{fmt(fv)}</b> in {yrs} years | Invested: {fmt(inv)} | Gains: <b>{fmt(fv-inv)}</b> ({(fv-inv)/inv*100:.0f}%)</div>', unsafe_allow_html=True)

    ti = s.salary + s.other_income
    total_inv = s.sip + s.stocks + s.elss + s.ppf + s.nps + s.other_inv + s.epf_emp_mo
    tax80c = min((s.elss+s.ppf+s.epf_emp_mo)*12, 150000)
    cc = st.columns(3)
    ic = "" if ti>0 and total_inv/ti>=.2 else "a" if ti>0 and total_inv/ti>=.1 else "r"
    with cc[0]: st.markdown(f'<div class="mc"><div class="mc-lbl">Monthly Investment</div><div class="mc-val">{fmtr(total_inv)}</div></div>', unsafe_allow_html=True)
    with cc[1]: st.markdown(f'<div class="mc {ic}"><div class="mc-lbl">% of Income</div><div class="mc-val">{pct(total_inv,ti)}</div><div class="mc-sub">Target: 20%+</div></div>', unsafe_allow_html=True)
    with cc[2]: st.markdown(f'<div class="mc p"><div class="mc-lbl">80C Tax Saved/yr (est.)</div><div class="mc-val">₹{int(tax80c*.3):,}</div><div class="mc-sub">At 30% slab</div></div>', unsafe_allow_html=True)

    nav(next_label="Continue to Insurance →")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — INSURANCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛡️  Insurance":
    st.markdown("""<div class="pg-banner">
      <div class="pg-banner-left"><h2>Insurance Coverage</h2>
        <p>Insurance is the foundation of every financial plan — it protects everything you build.</p></div>
      <div class="pg-banner-right"><div class="pg-step-no">04</div></div>
    </div>""", unsafe_allow_html=True)

    s.has_ins = st.radio("Do you have any insurance policy?", ["Yes","No"],
                          index=0 if s.has_ins else 1, horizontal=True) == "Yes"

    if s.has_ins:
        st.markdown("---")
        st.markdown("**Add all your insurance policies below:**")
        num_ins = st.number_input("How many policies do you have?", 1, 15, max(len(s.insurances),1), step=1)
        ins_types = ["Term Life Insurance","Health / Mediclaim","ULIP (Unit Linked)","Endowment / LIC Money-back",
                     "Whole Life Insurance","Critical Illness Cover","Personal Accident Cover",
                     "Vehicle Insurance","Home Insurance","Travel Insurance","Other"]
        insurances = []
        for i in range(int(num_ins)):
            prev = s.insurances[i] if i < len(s.insurances) else {}
            st.markdown(f'<p style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#0e6b4a;margin-bottom:2px">Policy #{i+1}</p>', unsafe_allow_html=True)
            ic = st.columns([3,2,2,2])
            with ic[0]: itype  = st.selectbox("Type", ins_types, index=ins_types.index(prev.get("type","Health / Mediclaim")) if prev.get("type") in ins_types else 1, key=f"it{i}")
            with ic[1]: iprem  = st.number_input("Premium ₹/mo", 0, step=100, value=prev.get("premium",0), key=f"ip{i}", format="%d")
            with ic[2]: icov   = st.number_input("Cover (₹ Lakhs)", 0, step=1, value=prev.get("cover_l",0), key=f"ic{i}")
            with ic[3]: iins   = st.text_input("Insurer", value=prev.get("insurer",""), key=f"ii{i}", placeholder="LIC, HDFC, Max…")
            insurances.append({"type":itype,"premium":iprem,"cover_l":icov,"insurer":iins})
        s.insurances = insurances
        s.ins_prem = sum(p["premium"] for p in insurances)

        # Analysis
        life_cov   = sum(p["cover_l"] for p in insurances if any(k in p["type"] for k in ["Life","Term","ULIP","Endow","Whole"]))
        health_cov = sum(p["cover_l"] for p in insurances if any(k in p["type"] for k in ["Health","Mediclaim"]))
        rec_life   = int(s.salary*12*10/100000)

        st.markdown('<p class="stl">Coverage Analysis</p>', unsafe_allow_html=True)
        sc = st.columns(3)
        with sc[0]: st.markdown(f'<div class="mc"><div class="mc-lbl">Monthly Premium</div><div class="mc-val">{fmtr(s.ins_prem)}</div></div>', unsafe_allow_html=True)
        with sc[1]: st.markdown(f'<div class="mc b"><div class="mc-lbl">Life Cover</div><div class="mc-val">₹{life_cov}L</div><div class="mc-sub">Rec: ₹{rec_life}L (10×)</div></div>', unsafe_allow_html=True)
        with sc[2]: st.markdown(f'<div class="mc p"><div class="mc-lbl">Health Cover</div><div class="mc-val">₹{health_cov}L</div><div class="mc-sub">Rec: ₹10L+</div></div>', unsafe_allow_html=True)

        if life_cov >= rec_life: st.markdown(f'<div class="ab g">✅ Life cover ₹{life_cov}L meets the 10× income rule (₹{rec_life}L).</div>', unsafe_allow_html=True)
        elif life_cov > 0:       st.markdown(f'<div class="ab a">⚠️ Life cover ₹{life_cov}L below recommended ₹{rec_life}L. Gap: ₹{rec_life-life_cov}L — consider a top-up Term plan.</div>', unsafe_allow_html=True)
        if health_cov >= 10:     st.markdown(f'<div class="ab g">✅ Health cover ₹{health_cov}L is adequate.</div>', unsafe_allow_html=True)
        elif health_cov > 0:     st.markdown(f'<div class="ab a">⚠️ Health cover ₹{health_cov}L may be insufficient. Medical inflation ~14%/year. Target ₹10L+.</div>', unsafe_allow_html=True)
        else:                    st.markdown('<div class="ab r">🚨 No health insurance! One hospitalisation can cost ₹3–15L.</div>', unsafe_allow_html=True)

        bad = [p for p in insurances if "ULIP" in p["type"] or "Endow" in p["type"]]
        if bad:
            st.markdown(f'<div class="ab a">⚠️ <b>Advisor Note:</b> You have {len(bad)} ULIP/Endowment policy(s) — these mix insurance + investment with high charges, delivering only 4–6% returns. Consider: (1) Surrender/reduce premium, (2) Buy pure Term plan for cover, (3) SIP for wealth creation. This single switch can add lakhs to your retirement corpus.</div>', unsafe_allow_html=True)
    else:
        s.insurances = []; s.ins_prem = 0
        st.markdown(f'<div class="ab r">🚨 <b>No insurance detected.</b> A single hospitalisation (₹3–15L), disability, or premature death can wipe out years of savings and leave dependents financially vulnerable. This is the most urgent gap to fix.</div>', unsafe_allow_html=True)
        st.markdown('<p class="stl">Personalised Recommendation</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ab b">🎯 {ins_advice(s.age)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ab b">📋 <b>Quick Action Plan:</b><br>1️⃣ Get a <b>Term Life plan online</b> (PolicyBazaar, Ditto Insurance, HDFC Click2Protect)<br>2️⃣ Get <b>Health Insurance</b> (Star Health, Niva Bupa, Care Health, HDFC ERGO)<br>3️⃣ Add <b>Critical Illness + Personal Accident</b> rider (~₹300/month extra)<br>4️⃣ Budget <b>₹1,500–3,500/month</b> for complete, adequate protection</div>', unsafe_allow_html=True)
        cc = st.columns(3)
        term_prem = max(600, 2200 - (35-s.age)*35) if s.age < 50 else 6000
        hlth_prem = max(450, 280+s.age*12)
        with cc[0]: st.markdown(f'<div class="mc"><div class="mc-lbl">Term Plan (₹1 Cr)</div><div class="mc-val">~₹{term_prem:,}/mo</div></div>', unsafe_allow_html=True)
        with cc[1]: st.markdown(f'<div class="mc b"><div class="mc-lbl">Health (₹10L cover)</div><div class="mc-val">~₹{hlth_prem:,}/mo</div></div>', unsafe_allow_html=True)
        with cc[2]: st.markdown(f'<div class="mc p"><div class="mc-lbl">Combined Estimate</div><div class="mc-val">~₹{term_prem+hlth_prem:,}/mo</div></div>', unsafe_allow_html=True)

    nav(next_label="Continue to Savings →")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — SAVINGS & ASSETS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏦  Savings & Assets":
    st.markdown("""<div class="pg-banner">
      <div class="pg-banner-left"><h2>Savings & Assets</h2>
        <p>Your existing wealth — the launchpad for everything you want to build next.</p></div>
      <div class="pg-banner-right"><div class="pg-step-no">05</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🏦 Bank & Liquid**")
        s.cash  = st.number_input("💵 Total Savings / Current Account Balance (₹)", 0, step=5000, value=s.cash, format="%d")
        s.banks = st.number_input("🏦 Number of Bank Accounts", 1, 20, s.banks)
        s.ef_mo = st.slider("Emergency Fund Target (months of expenses)", 3, 12, s.ef_mo)

    with c2:
        st.markdown("**📋 Fixed Deposits**")
        s.fd = st.number_input("FD Total Principal (₹)", 0, step=10000, value=s.fd, format="%d")
        if s.fd > 0:
            s.fd_rate = st.slider("FD Rate (% p.a.)", 4.0, 9.5, s.fd_rate, .05)
            s.fd_yrs  = st.slider("FD Tenure (years)", 1, 10, s.fd_yrs)
            fd_mat    = fdfv(s.fd, s.fd_rate, s.fd_yrs)
            st.markdown(f'<div class="mc t"><div class="mc-lbl">FD Maturity Value</div><div class="mc-val">{fmt(fd_mat)}</div><div class="mc-sub">Gain: {fmt(fd_mat-s.fd)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ab b">💡 FD interest is fully taxable as per slab. Above your emergency fund, consider Debt MFs for better post-tax returns.</div>', unsafe_allow_html=True)

    # ── Bank Strategy ─────────────────────────────────────────────────────────
    st.markdown('<p class="stl">🏦 Optimal Bank Account Structure</p>', unsafe_allow_html=True)
    s.has_credit_card = st.toggle("Do you have a Credit Card?", value=s.get("has_credit_card", False),
                                   help="If yes, your credit card bill account becomes your 4th account need")
    ideal_banks = 4 if s.get("has_credit_card") else 3
    if s.get("banks",1) < ideal_banks:
        st.markdown(f'<div class="ab a">⚠️ You have <b>{s.get("banks",1)} account(s)</b> but need <b>{ideal_banks}</b> for {"a credit card user" if s.get("has_credit_card") else "optimal financial structure"}. See the recommended structure below.</div>', unsafe_allow_html=True)
    elif s.get("banks",1) == ideal_banks:
        st.markdown(f'<div class="ab g">✅ {s.get("banks",1)} accounts — perfect structure{"for a credit card user" if s.get("has_credit_card") else ""}! Set up auto-transfers on salary credit date.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ab a">⚠️ {s.get("banks",1)} accounts may create idle balances. Aim for {ideal_banks} purpose-driven accounts.</div>', unsafe_allow_html=True)

    if s.get("has_credit_card"):
        bc = st.columns(4)
        slots = [
            ("n","Account 1","💸 Daily Expenses","Variable monthly spending — groceries, fuel, eating out. Amount varies each month, keep only what you need here."),
            ("g","Account 2","💼 Salary Account","Fixed outflows — Rent/EMIs/SIP auto-debited here on salary day. Never touch for variable spending."),
            ("p","Account 3","🛡️ Savings Account","Emergency fund + FD ladder. 6 months of expenses. High-interest savings bank (IDFC, AU, SBI)."),
            ("a","Account 4","💳 Credit Card Bill","Keep funds here to pay your credit card full statement. Never pay minimum due — always pay full."),
        ]
    else:
        bc = st.columns(3)
        slots = [
            ("n","Account 1","💸 Daily Expenses","Variable monthly spending. Transfer a fixed budget here at start of month. When it's empty — stop spending."),
            ("g","Account 2","💼 Salary Account","Fixed outflows — Rent, EMIs, SIP all auto-debit from here. Protected from lifestyle spending."),
            ("p","Account 3","🛡️ Savings Account","Emergency fund (6 months expenses) + FD. High-interest savings (IDFC, AU, SBI). Touch only for emergencies."),
        ]
    for col, (cls, no, name, desc) in zip(bc, slots):
        with col:
            st.markdown(f'<div class="bslot {cls}"><div class="bslot-no">{no}</div><div class="bslot-name">{name}</div><div class="bslot-desc">{desc}</div></div>', unsafe_allow_html=True)

    # ── Other Assets ──────────────────────────────────────────────────────────
    st.markdown('<p class="stl">🥇 Other Assets</p>', unsafe_allow_html=True)
    ac = st.columns(2)
    with ac[0]:
        s.gold_g  = st.number_input("Gold Holdings (grams)", 0.0, step=1.0, value=float(s.gold_g))
        s.gold_px = st.number_input("Gold Price per gram (₹)", 1000, step=100, value=s.gold_px, format="%d")
        gold_val = s.gold_g * s.gold_px
        if gold_val > 0:
            st.markdown(f'<div class="mc o"><div class="mc-lbl">Gold Value</div><div class="mc-val">{fmt(gold_val)}</div></div>', unsafe_allow_html=True)
            st.markdown('<div class="ab b">💡 Consider converting physical gold to Sovereign Gold Bonds (SGBs) — same price exposure + 2.5% annual interest + no making charges.</div>', unsafe_allow_html=True)
    with ac[1]:
        s.mf     = st.number_input("Existing Mutual Fund Portfolio (₹)", 0, step=10000, value=s.mf, format="%d")
        s.realty = st.number_input("Real Estate Market Value (₹)", 0, step=100000, value=s.realty, format="%d")
        # Retirement sliders
        st.markdown("**🏁 Retirement Parameters**")
        s.ret_age  = st.number_input("Target Retirement Age", 45, 70, s.ret_age)
        s.ret_ret  = st.slider("Expected Portfolio Return (% p.a.)", 8.0, 15.0, s.ret_ret, .5)
        s.inflation= st.slider("Expected Inflation (% p.a.)", 4.0, 8.0, s.inflation, .5)

    t = totals()
    gold_val2 = s.gold_g * s.gold_px
    ta = s.cash + s.fd + gold_val2 + s.mf + s.realty
    cc = st.columns(4)
    with cc[0]: st.markdown(f'<div class="mc"><div class="mc-lbl">Liquid Assets</div><div class="mc-val">{fmt(s.cash+s.fd)}</div></div>', unsafe_allow_html=True)
    with cc[1]: st.markdown(f'<div class="mc o"><div class="mc-lbl">Gold + MF + Realty</div><div class="mc-val">{fmt(gold_val2+s.mf+s.realty)}</div></div>', unsafe_allow_html=True)
    with cc[2]: st.markdown(f'<div class="mc b"><div class="mc-lbl">Total Assets</div><div class="mc-val">{fmt(ta)}</div></div>', unsafe_allow_html=True)
    with cc[3]: st.markdown(f'<div class="mc p"><div class="mc-lbl">Net Worth</div><div class="mc-val">{fmt(t["net_worth"])}</div></div>', unsafe_allow_html=True)

    nav(next_label="View Dashboard & Download →")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — DASHBOARD & REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊  Dashboard & Report":
    t = totals()
    score, sb = compute_score(t)
    ins, warn, dng = gen_insights(t, score)
    s_ico, s_lbl = hbadge(score)
    score_color = "#0e6b4a" if score>=75 else "#f59e0b" if score>=55 else "#f97316" if score>=35 else "#ef4444"
    ti = t["ti"]
    gold_val = s.gold_g * s.gold_px
    total_emi = t["total_emi"]
    s_ico2, s_lbl2 = hbadge(score)  # needed for auto-save meta

    # ── AUTO-SAVE: generate & store report the moment dashboard is loaded ─────
    # This runs once per session (tracks via session_state flag)
    if not st.session_state.get("auto_saved") and ti > 0:
        try:
            _auto_pdf = build_pdf(t, score, sb, ins, warn, dng)
            _auto_fname = (
                f"AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                f"_{(s.name or st.session_state.get('auth_user','client')).replace(' ','_')}.pdf"
            )
            _auto_meta = {
                "name":        s.name or "Unknown",
                "full_name":   s.name or st.session_state.get("auth_full_name",""),
                "username":    st.session_state.get("auth_user",""),
                "email":       st.session_state.get("auth_email",""),
                "age":         s.age,
                "city":        s.city,
                "salary":      s.salary,
                "score":       score,
                "score_label": s_lbl2,
                "net_worth":   t["net_worth"],
                "phone":       "",
                "paid":        False,   # not paid yet — auto-save draft
                "upi_id":      "",
                "auto_save":   True,
            }
            _auto_path = REPORTS_DIR / _auto_fname
            _auto_path.write_bytes(_auto_pdf)
            # log to submissions
            try:
                _subs = json.loads(SUBS_FILE.read_text()) if SUBS_FILE.exists() else []
            except Exception:
                _subs = []
            _auto_meta["pdf_file"]  = _auto_fname
            _auto_meta["saved_at"]  = datetime.now().strftime("%Y%m%d_%H%M%S")
            _subs.append(_auto_meta)
            SUBS_FILE.write_text(json.dumps(_subs, indent=2, ensure_ascii=False))
            # attach to user
            if _auto_meta["username"]:
                save_user_report(_auto_meta["username"], {
                    "pdf_file":    _auto_fname,
                    "saved_at":    _auto_meta["saved_at"],
                    "score":       score,
                    "score_label": s_lbl2,
                    "net_worth":   t["net_worth"],
                    "auto_save":   True,
                })
            st.session_state.auto_saved      = True
            st.session_state.auto_saved_file = _auto_fname
        except Exception as _e:
            st.session_state.auto_saved = True  # prevent retry loop
            pass  # silent — don't break UX if disk write fails

    # ── Header ────────────────────────────────────────────────────────────────
    name_label = f"{s.name}'s" if s.name else "Your"
    st.markdown(f"""<div class="pg-banner" style="align-items:center">
      <div class="pg-banner-left">
        <h2>{name_label} Financial Dashboard</h2>
        <p>Complete picture — where money goes, where it grows, what to fix next.</p></div>
      <div style="text-align:right;color:white">
        <div style="font-size:2.8rem;line-height:1">{s_ico}</div>
        <div style="font-size:1.4rem;font-weight:700">{score}/100</div>
        <div style="font-size:.82rem;opacity:.8">{s_lbl}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Health Score — ONLY visible section (free) ───────────────────────────
    st.markdown('<p class="stl">🎯 Your Financial Health Score</p>', unsafe_allow_html=True)

    # Big score card — always visible, free
    sc_color  = "#0e6b4a" if score>=75 else "#f59e0b" if score>=55 else "#f97316" if score>=35 else "#ef4444"
    sc_bg     = "#f0fdf4" if score>=75 else "#fffbeb" if score>=55 else "#fff7ed" if score>=35 else "#fef2f2"
    sc_border = "#86efac" if score>=75 else "#fcd34d" if score>=55 else "#fdba74" if score>=35 else "#fca5a5"
    s_ico2, s_lbl2 = hbadge(score)

    st.markdown(f"""
    <div style="background:{sc_bg};border:2px solid {sc_border};border-radius:20px;padding:32px 36px;text-align:center;margin:12px 0">
      <div style="font-size:4rem;line-height:1;margin-bottom:8px">{s_ico2}</div>
      <div style="font-family:'DM Serif Display',serif;font-size:3.2rem;font-weight:700;color:{sc_color};line-height:1">{score}</div>
      <div style="font-size:1rem;font-weight:600;color:{sc_color};letter-spacing:.04em;margin-top:4px">out of 100 &nbsp;·&nbsp; {s_lbl2}</div>
      <div style="font-size:.85rem;color:#64748b;margin-top:12px;line-height:1.6;max-width:480px;margin-left:auto;margin-right:auto">
        This score reflects your investment rate, expense control, insurance cover, emergency fund, debt load, and monthly surplus.
        {"🎉 You're in great financial shape! Keep compounding." if score>=75 else
         "💪 Good foundation. A few tweaks can push you to Excellent." if score>=55 else
         "⚠️ Several gaps need attention. Your full report shows exactly what to fix." if score>=35 else
         "🚨 Significant financial gaps detected. Your report contains a prioritised action plan."}
      </div>
    </div>""", unsafe_allow_html=True)

    # Score breakdown bars (visible free)
    st.markdown("**Score Breakdown:**")
    for cat, got, mx, note in sb:
        pb  = got/mx if mx else 0
        bc  = "#0e6b4a" if pb==1 else "#f59e0b" if pb>.5 else "#ef4444"
        st.markdown(f"""<div class="sbar">
          <div class="sbar-hd"><span>{cat}</span><span style="color:{bc};font-weight:600">{got}/{mx}</span></div>
          <div class="sbar-bg"><div class="sbar-fill" style="width:{int(pb*100)}%;background:{bc}"></div></div>
          <div style="font-size:.7rem;color:#64748b;margin-top:2px">{note}</div>
        </div>""", unsafe_allow_html=True)

    # ── Payment Gate ──────────────────────────────────────────────────────────
    st.markdown("")
    st.markdown('<p class="stl">📄 Download Full Financial Report</p>', unsafe_allow_html=True)

    # What's locked
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f2d52,#0e6b4a);border-radius:16px;padding:24px 28px;color:white;margin:12px 0">
      <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;margin-bottom:10px">🔒 Full Report — ₹100 only</div>
      <div style="font-size:.88rem;opacity:.88;line-height:1.8">
        ✅ Complete income & expense analysis &nbsp;·&nbsp; ✅ SIP projections (15/20/30 yr)<br>
        ✅ EPF retirement corpus forecast &nbsp;·&nbsp; ✅ Insurance gap analysis<br>
        ✅ Personalised action items &nbsp;·&nbsp; ✅ Retirement gap & shortfall plan<br>
        ✅ Net worth statement &nbsp;·&nbsp; ✅ Advisor contact, services & pricing<br><br>
        <span style="opacity:.65;font-size:.8rem">A one-time fee of just ₹100 gets you a professionally formatted PDF — your complete financial picture in one document.</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # Payment instructions
    pc1, pc2 = st.columns([1,1])
    with pc1:
        st.markdown(f"""
        <div style="background:#fff;border:2px solid #e2e8f0;border-radius:16px;padding:24px 28px;text-align:center">
          <div style="font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#94a3b8;margin-bottom:12px">Step 1 — Pay ₹100</div>
          <div style="font-size:2.2rem;margin-bottom:8px">📱</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.35rem;font-weight:700;color:#0f2d52;background:#f1f5f9;border-radius:10px;padding:10px 18px;margin:10px 0;letter-spacing:.03em">{PAYMENT["upi_id"]}</div>
          <div style="font-size:.82rem;color:#64748b;margin-top:8px">Open any UPI app (GPay, PhonePe, Paytm, BHIM)<br>Search or scan: <b>{PAYMENT["upi_id"]}</b><br>Amount: <b>₹{PAYMENT["amount"]}</b></div>
        </div>""", unsafe_allow_html=True)
    with pc2:
        st.markdown(f"""
        <div style="background:#fff;border:2px solid #e2e8f0;border-radius:16px;padding:24px 28px;text-align:center">
          <div style="font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#94a3b8;margin-bottom:12px">Step 2 — Send Screenshot</div>
          <div style="font-size:2.2rem;margin-bottom:8px">💬</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.35rem;font-weight:700;color:#0f2d52;background:#f1f5f9;border-radius:10px;padding:10px 18px;margin:10px 0;letter-spacing:.03em">+91 {PAYMENT["whatsapp"]}</div>
          <div style="font-size:.82rem;color:#64748b;margin-top:8px">WhatsApp your payment screenshot<br>to <b>+91 {PAYMENT["whatsapp"]}</b><br>We'll send your PDF report within <b>2 hours</b></div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;padding:14px 20px;margin:12px 0;font-size:.86rem;color:#78350f;text-align:center">
      💡 After payment, share the screenshot on WhatsApp <b>+91 {PAYMENT["whatsapp"]}</b> along with your name.<br>
      Your personalised PDF report will be sent to you directly within 2 hours (usually much faster!).
    </div>""", unsafe_allow_html=True)

    # ── Screenshot upload + confirm ─────────────────────────────────────────────
    # KEY FIX: PDF bytes are stored in session_state so Streamlit Cloud reruns
    # don't lose the data when the download button is clicked.
    st.markdown("")
    st.markdown("**Already paid? Upload your screenshot to confirm:**")

    up_col, info_col = st.columns([1,1])
    with up_col:
        screenshot = st.file_uploader(
            "📸 Upload payment screenshot",
            type=["jpg","jpeg","png"],
            help="Upload the payment success screenshot from your UPI app"
        )
    with info_col:
        user_phone = st.text_input(
            "Your WhatsApp number (for delivery)",
            placeholder="+91 XXXXX XXXXX",
            help="We will send the report to this number on WhatsApp"
        )

    if screenshot is not None:
        st.image(screenshot, caption="Payment screenshot received ✅", width=260)

        # ── Generate button: builds PDF and caches in session_state ───────────
        if st.button("✅ Confirm Payment & Generate My Report", type="primary", use_container_width=True):
            with st.spinner("Building your personalised report…"):
                try:
                    pdf_data  = build_pdf(t, score, sb, ins, warn, dng)
                    fname_pdf = (
                        f"FinSight_Report_{(s.name or 'Client').replace(' ','_')}"
                        f"_{datetime.now().strftime('%d%b%Y_%H%M')}.pdf"
                    )
                    # Cache in session_state — survives the next Streamlit rerun
                    st.session_state.pdf_ready    = True
                    st.session_state.pdf_bytes    = pdf_data
                    st.session_state.pdf_filename = fname_pdf

                    # Save to disk (works when running locally / on a VPS)
                    try:
                        saved_name = save_report_to_disk(pdf_data, {
                            "name":        s.name or "Unknown",
                            "full_name":   s.name or st.session_state.get("auth_full_name",""),
                            "username":    st.session_state.get("auth_user",""),
                            "email":       st.session_state.get("auth_email",""),
                            "age":         s.age,
                            "city":        s.city,
                            "salary":      s.salary,
                            "score":       score,
                            "score_label": s_lbl2,
                            "net_worth":   t["net_worth"],
                            "phone":       user_phone,
                            "paid":        True,
                            "upi_id":      PAYMENT["upi_id"],
                        })
                        # Save screenshot alongside
                        ext      = screenshot.name.split(".")[-1]
                        ss_fname = (
                            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            f"_{(s.name or 'Client').replace(' ','_')}_ss.{ext}"
                        )
                        (REPORTS_DIR / ss_fname).write_bytes(screenshot.getvalue())
                        # patch screenshot filename back into submissions log
                        try:
                            subs = json.loads(SUBS_FILE.read_text()) if SUBS_FILE.exists() else []
                            if subs: subs[-1]["screenshot_file"] = ss_fname
                            SUBS_FILE.write_text(json.dumps(subs, indent=2))
                        except Exception: pass
                        st.session_state.saved_name = saved_name
                    except Exception:
                        st.session_state.saved_name = "cloud-mode (no local disk)"

                    st.rerun()   # rerun so download button renders cleanly

                except Exception as e:
                    st.error(
                        f"Report generation error: {e}. "
                        f"Please WhatsApp +91 {PAYMENT['whatsapp']} directly."
                    )

    # ── No download button for users — admin downloads from portal ─────────────
    if st.session_state.get("pdf_ready"):
        st.success(
            f"✅ Payment confirmed! Your report has been saved. "
            f"You will receive it on WhatsApp +91 {PAYMENT['whatsapp']} within 2 hours."
        )
        st.markdown('<div class="ab g">📋 Our advisor will review your payment screenshot and send your personalised PDF report to your WhatsApp number shortly. <br><b>No action needed from your side.</b></div>', unsafe_allow_html=True)

    elif screenshot is None:
        # Locked placeholder — no screenshot uploaded yet
        st.markdown("""
        <div style="background:#f8fafc;border:2px dashed #e2e8f0;border-radius:14px;
                    padding:28px;text-align:center;margin:12px 0">
          <div style="font-size:2rem;margin-bottom:8px">🔒</div>
          <div style="font-weight:600;color:#64748b">Upload your payment screenshot above to unlock the report</div>
          <div style="font-size:.8rem;color:#94a3b8;margin-top:6px">
            Download button appears here after screenshot is confirmed
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
    st.caption("FinSight is a financial planning tool. All projections are indicative. Consult a qualified financial professional before making investment decisions.")
    nav(next_label="Talk to an Advisor →")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — CONSULT AN ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤝  Consult an Advisor":
    st.markdown(f"""
    <div class="chero">
      <h1>Get Expert Financial Guidance</h1>
      <p>A calculator shows you numbers. A great advisor helps you <b>act</b> on them.</p>
      <p style="margin-top:10px;opacity:.65;font-size:.82rem">
        📍 Serving clients across India &nbsp;·&nbsp;
        Experience-backed, unbiased advice
      </p>
    </div>""", unsafe_allow_html=True)

    # ── Why consult ───────────────────────────────────────────────────────────
    st.markdown('<p class="stl">Why Work with a Financial Advisor?</p>', unsafe_allow_html=True)
    wc = st.columns(3)
    why = [
        ("🎯","Personalised Strategy","No two financial situations are the same. We build a strategy around your income, goals, risk appetite, and family — not a generic template."),
        ("🛡️","Unbiased, Fee-only","We earn nothing from recommending products. Every recommendation is purely in your interest."),
        ("📈","Goal-Based Investing","Every rupee mapped to a specific goal — home, education, retirement, travel — with a clear timeline and instrument."),
        ("🔄","Annual Reviews","Life changes. Regular reviews keep your plan aligned to your evolving reality."),
        ("🧾","Tax Optimisation","Save legally via 80C, 80D, 80CCD, HRA, LTCG harvesting. Every rupee saved is a rupee earned."),
        ("💬","Accountability Partner","The single biggest differentiator between those who achieve financial goals and those who don't."),
    ]
    for i, (icon, title, desc) in enumerate(why):
        with wc[i%3]:
            st.markdown(f'<div class="svc"><div style="font-size:1.7rem;margin-bottom:8px">{icon}</div><div class="svc-ttl">{title}</div><div class="svc-dsc">{desc}</div></div>', unsafe_allow_html=True)

    # ── Services ──────────────────────────────────────────────────────────────
    # Services & pricing section removed
    # ── Contact ───────────────────────────────────────────────────────────────
    st.markdown('<p class="stl">📞 Get in Touch</p>', unsafe_allow_html=True)
    ct = st.columns(4)
    contacts = [
        ("📱","Phone / WhatsApp",ADVISOR["phone"],"Call or WhatsApp — free 15-min discovery call"),
        ("📧","Email",ADVISOR["email"],"Queries, plans & documents"),
        ("🌐","Website",ADVISOR["website"],"Blog, resources & booking"),
        ("📍","Location",ADVISOR["address"],"In-person by appointment"),
    ]
    for col,(icon,lbl,val,note) in zip(ct,contacts):
        with col:
            st.markdown(f'<div class="citem"><div class="citem-icon">{icon}</div><div class="citem-lbl">{lbl}</div><div class="citem-val">{val}</div><div class="citem-note">{note}</div></div>', unsafe_allow_html=True)

    # Social
    soc = st.columns(4)
    with soc[0]: st.markdown(f'<div class="citem"><div class="citem-icon">💼</div><div class="citem-lbl">LinkedIn</div><div class="citem-val">{ADVISOR["linkedin"]}</div><div class="citem-note">Professional updates</div></div>', unsafe_allow_html=True)
    with soc[1]: st.markdown(f'<div class="citem"><div class="citem-icon">📸</div><div class="citem-lbl">Instagram</div><div class="citem-val">{ADVISOR["instagram"]}</div><div class="citem-note">Daily money tips</div></div>', unsafe_allow_html=True)

    # ── Book a call form ──────────────────────────────────────────────────────
    st.markdown('<p class="stl">📅 Book a Free Discovery Call</p>', unsafe_allow_html=True)
    st.markdown('<div class="ab b">15 minutes. No commitment. No sales pitch. We\'ll understand your situation and tell you honestly if and how we can help.</div>', unsafe_allow_html=True)
    st.markdown("")
    fc1, fc2 = st.columns(2)
    with fc1:
        fname  = st.text_input("Your Name", value=s.name, placeholder="e.g. Arjun Mehta")
        femail = st.text_input("Email Address", placeholder="you@example.com")
        fphone = st.text_input("WhatsApp / Phone", placeholder="+91 XXXXX XXXXX")
    with fc2:
        fgoal  = st.selectbox("Primary Financial Goal", [
            "Retirement Planning","Children's Education Fund","Home Purchase Planning",
            "Tax Optimisation","Insurance Review","Investment Portfolio Review",
            "Debt Management / Loan Planning","Just starting my financial journey","Other"])
        furgency = st.select_slider("How soon do you need this?",
                    ["Just exploring","Within 3 months","Within 1 month","This week — urgent"])
        fmsg   = st.text_area("Brief note (optional)", placeholder="e.g. I earn ₹90K/month, have 2 kids, want to retire by 55…")
    st.markdown("")
    if st.button("📩 Request Free Consultation", type="primary", use_container_width=True):
        if fname and fphone:
            st.success(f"✅ Thank you, {fname}! We'll reach out to {fphone} within 24 hours to schedule your free discovery call. Talk soon!")
            st.balloons()
        else:
            st.error("Please enter your name and phone number.")

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px 24px;margin-top:8px">
      <p style="font-size:.77rem;color:#64748b;margin:0;line-height:1.7">
        <b>Disclaimer:</b> FinSight is a financial education and planning tool. All calculations and projections are indicative and based on assumed rates.
        They do not constitute investment advice. Mutual fund investments are subject to market risks. Past performance is not a guarantee of future returns.
        Please consult a qualified financial professional before making investment decisions.
        <br><b>{ADVISOR['name']}</b> | {ADVISOR['title']}
      </p>
    </div>""", unsafe_allow_html=True)

    nav(show_next=False)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — MY PROFILE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👤  My Profile":
    s = st.session_state
    st.markdown("""<div class="pg-banner">
      <div class="pg-banner-left"><h2>👤 My Profile</h2>
        <p>Manage your personal details, security settings and account information.</p></div>
      <div class="pg-banner-right"><div class="pg-step-no">👤</div></div>
    </div>""", unsafe_allow_html=True)

    uname   = s.get("auth_user","")
    u_data  = get_user(uname)

    if not u_data:
        st.error("Could not load profile. Please log out and log in again.")
    else:
        # ── Profile summary card ──────────────────────────────────────────────
        pc1, pc2 = st.columns([1, 2])
        with pc1:
            initials = "".join([n[0].upper() for n in u_data.get("full_name","U").split()[:2]])
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0f2d52,#0e6b4a);border-radius:50%;
                        width:90px;height:90px;display:flex;align-items:center;justify-content:center;
                        font-size:2rem;font-weight:700;color:white;margin:0 auto 12px;letter-spacing:2px">
              {initials}
            </div>
            <div style="text-align:center;font-weight:600;font-size:1.05rem;color:#0f172a">{u_data.get("full_name","")}</div>
            <div style="text-align:center;font-size:.8rem;color:#64748b;margin-top:2px">`{uname}`</div>
            <div style="text-align:center;font-size:.75rem;color:#94a3b8;margin-top:4px">
              Joined {u_data.get("created_at","")[:10]}</div>
            """, unsafe_allow_html=True)
        with pc2:
            psc = st.columns(2)
            with psc[0]:
                st.markdown(f'<div class="mc"><div class="mc-lbl">Email</div><div class="mc-val" style="font-size:1rem">{u_data.get("email","—")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="mc b"><div class="mc-lbl">Mobile</div><div class="mc-val" style="font-size:1rem">+91 {u_data.get("mobile","—")}</div></div>', unsafe_allow_html=True)
            with psc[1]:
                st.markdown(f'<div class="mc p"><div class="mc-lbl">Date of Birth</div><div class="mc-val" style="font-size:1rem">{u_data.get("dob","—")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="mc t"><div class="mc-lbl">Age</div><div class="mc-val" style="font-size:1rem">{u_data.get("age","—")} years</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # ── Edit profile ──────────────────────────────────────────────────────
        st.markdown('<p class="stl">✏️ Edit Profile Information</p>', unsafe_allow_html=True)
        ep1, ep2 = st.columns(2)
        with ep1:
            new_name  = st.text_input("Full Name", value=u_data.get("full_name",""), key="ep_name")
            new_email = st.text_input("Email Address", value=u_data.get("email",""), key="ep_email")
            new_mob   = st.text_input("Mobile Number (10 digits)", value=u_data.get("mobile",""), key="ep_mob")
        with ep2:
            try:
                cur_dob = datetime.strptime(u_data.get("dob","1995-01-01"), "%Y-%m-%d").date()
            except Exception:
                cur_dob = date(1995,1,1)
            new_dob   = st.date_input("Date of Birth", value=cur_dob, key="ep_dob",
                                       min_value=date(1950,1,1), max_value=date.today())
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Save Profile Changes", type="primary", use_container_width=True, key="btn_save_profile"):
                ok, msg = update_profile(uname, {
                    "full_name": new_name,
                    "email":     new_email,
                    "mobile":    new_mob,
                    "dob":       str(new_dob),
                })
                if ok:
                    st.success(f"✅ {msg}")
                    # Update session
                    st.session_state.auth_full_name = new_name or s.auth_full_name
                    st.session_state.auth_email     = new_email or s.auth_email
                    st.session_state.auth_mobile    = new_mob
                    st.session_state.auth_dob       = str(new_dob)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        # ── Change Password ───────────────────────────────────────────────────
        st.markdown('<p class="stl">🔒 Change Password</p>', unsafe_allow_html=True)
        pp1, pp2 = st.columns(2)
        with pp1:
            cur_pw  = st.text_input("Current Password", type="password", key="ep_curpw")
            new_pw  = st.text_input("New Password (min 6 chars)", type="password", key="ep_newpw")
            new_pw2 = st.text_input("Confirm New Password", type="password", key="ep_newpw2")
        with pp2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("🔐 Change Password", use_container_width=True, key="btn_change_pw"):
                from auth import check_pw
                if not check_pw(cur_pw, u_data.get("password","")):
                    st.error("❌ Current password is incorrect.")
                elif new_pw != new_pw2:
                    st.error("❌ New passwords do not match.")
                elif len(new_pw) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                else:
                    ok, msg = update_profile(uname, {"new_password": new_pw})
                    if ok: st.success(f"✅ {msg}")
                    else: st.error(f"❌ {msg}")

        # ── OTP-verify new mobile ─────────────────────────────────────────────
        # ── Change Mobile ────────────────────────────────────────────────────────
        st.markdown('<p class="stl">📱 Change Mobile Number</p>', unsafe_allow_html=True)
        with st.form("chg_mob"):
            nm = st.text_input("New Mobile (10 digits)", placeholder="9876543210")
            mb = st.form_submit_button("Update Mobile", use_container_width=True)
        if mb:
            m2 = nm.strip().replace(" ","").replace("+91","")
            if not m2.isdigit() or len(m2)!=10: st.error("❌ Enter a valid 10-digit number.")
            else:
                ok2,msg2 = update_profile(uname,{"mobile":m2})
                if ok2: st.success(f"✅ Mobile updated to +91 {m2}"); st.session_state.auth_mobile=m2
                else: st.error(f"❌ {msg2}")

        # ── Reports history ───────────────────────────────────────────────────
        reports = u_data.get("reports",[])
        if reports:
            st.markdown('<p class="stl">📄 Your Report History</p>', unsafe_allow_html=True)
            for r in reversed(reports):
                rtype = "🔵 Auto-saved" if r.get("auto_save") else "💰 Paid report"
                st.markdown(f"- {rtype} · {r.get('saved_at','')[:16].replace('_',' ')} · Score: **{r.get('score','—')}/100** · Net Worth: {fmt(r.get('net_worth',0))}")
            st.markdown('<div class="ab b">📋 To download any report, please contact Yash Wankar on WhatsApp: <b>+91 90286 93456</b>.</div>', unsafe_allow_html=True)

    nav(show_next=False)