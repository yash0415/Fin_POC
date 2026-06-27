"""
admin.py — Admin dashboard rendered inside app.py
Called when st.session_state.auth_role == "admin"
"""
import json
import streamlit as st
from pathlib import Path
from datetime import datetime
from auth import all_users

DATA_DIR    = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
SUBS_FILE   = DATA_DIR / "submissions.json"

def _load_submissions():
    if SUBS_FILE.exists():
        try:
            return json.loads(SUBS_FILE.read_text())
        except Exception:
            return []
    return []

def fmt(n):
    n = float(n)
    if abs(n) >= 1e7: return f"₹{n/1e7:.2f} Cr"
    if abs(n) >= 1e5: return f"₹{n/1e5:.2f} L"
    return f"₹{n:,.0f}"

def render():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f2d52,#0e6b4a);border-radius:16px;
                padding:28px 36px;color:white;margin-bottom:24px">
      <h2 style="font-family:'DM Serif Display',serif;font-size:2rem;margin:0 0 4px;color:white">
        🛡️ Admin Dashboard
      </h2>
      <p style="margin:0;opacity:.75;font-size:.9rem">Yash Wankar · FinSight Internal Portal</p>
    </div>""", unsafe_allow_html=True)

    users = all_users()
    subs  = _load_submissions()

    # ── KPI Row ───────────────────────────────────────────────────────────────
    paid_subs = [s for s in subs if s.get("paid")]
    total_rev = len(paid_subs) * 100

    c1, c2, c3, c4 = st.columns(4)
    def mc(label, val, cls=""):
        return f'<div class="mc {cls}"><div class="mc-lbl">{label}</div><div class="mc-val">{val}</div></div>'

    with c1: st.markdown(mc("Total Users", len(users)), unsafe_allow_html=True)
    with c2: st.markdown(mc("Paid Reports", len(paid_subs), "t"), unsafe_allow_html=True)
    with c3: st.markdown(mc("Revenue Collected", f"₹{total_rev:,}", "p"), unsafe_allow_html=True)
    with c4:
        pending = [s for s in subs if not s.get("paid")]
        st.markdown(mc("Pending Verification", len(pending), "a"), unsafe_allow_html=True)

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📋 All Submissions", "👥 All Users", "📁 Download Reports"])

    # ── TAB 1: Submissions ───────────────────────────────────────────────────
    with tab1:
        st.markdown("### Payment Submissions")
        if not subs:
            st.info("No submissions yet.")
        else:
            for i, sub in enumerate(reversed(subs)):
                paid = sub.get("paid", False)
                border = "#0e6b4a" if paid else "#f59e0b"
                badge  = '<span style="background:#dcfce7;color:#15803d;padding:2px 10px;border-radius:20px;font-size:.72rem;font-weight:700">PAID ✅</span>' if paid else '<span style="background:#fef9c3;color:#854d0e;padding:2px 10px;border-radius:20px;font-size:.72rem;font-weight:700">PENDING</span>'
                with st.expander(f"{'✅' if paid else '⏳'} {sub.get('full_name', sub.get('name','?'))} — {sub.get('saved_at','')[:16].replace('_',' ')} {badge}", expanded=(i==0)):
                    cc = st.columns(3)
                    with cc[0]:
                        st.markdown(f"**Name:** {sub.get('full_name', sub.get('name','—'))}")
                        st.markdown(f"**Username:** `{sub.get('username','—')}`")
                        st.markdown(f"**Email:** {sub.get('email','—')}")
                        st.markdown(f"**Phone:** {sub.get('phone','—')}")
                    with cc[1]:
                        st.markdown(f"**Score:** {sub.get('score','—')}/100 ({sub.get('score_label','—')})")
                        st.markdown(f"**Income:** {fmt(sub.get('salary',0))}/mo")
                        st.markdown(f"**Net Worth:** {fmt(sub.get('net_worth',0))}")
                        st.markdown(f"**City:** {sub.get('city','—')}")
                    with cc[2]:
                        st.markdown(f"**UPI ID used:** {sub.get('upi_id','—')}")
                        st.markdown(f"**Submitted:** {sub.get('saved_at','—')}")
                        pf = sub.get("pdf_file")
                        sf = sub.get("screenshot_file")
                        if pf:
                            pdf_path = REPORTS_DIR / pf
                            if pdf_path.exists():
                                st.download_button(
                                    "⬇️ Download Report PDF",
                                    data=pdf_path.read_bytes(),
                                    file_name=pf,
                                    mime="application/pdf",
                                    key=f"dl_pdf_{i}"
                                )
                        if sf:
                            ss_path = REPORTS_DIR / sf
                            if ss_path.exists():
                                st.image(str(ss_path), caption="Payment Screenshot", width=300)

    # ── TAB 2: Users ─────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Registered Users")
        if not users:
            st.info("No users registered yet.")
        else:
            rows = []
            for uname, u in users.items():
                rows.append({
                    "Username":   uname,
                    "Full Name":  u.get("full_name","—"),
                    "Email":      u.get("email","—"),
                    "Joined":     u.get("created_at","—")[:10],
                    "Reports":    len(u.get("reports",[])),
                })
            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # User detail
            sel = st.selectbox("View user details:", ["— select —"] + list(users.keys()))
            if sel != "— select —":
                u = users[sel]
                st.markdown(f"**{u['full_name']}** · `{u['email']}` · Joined {u.get('created_at','')[:10]}")
                reps = u.get("reports",[])
                if reps:
                    st.markdown(f"**{len(reps)} report(s):**")
                    for r in reps:
                        st.markdown(f"- {r.get('saved_at','')[:16]} | Score: {r.get('score','—')}/100 | {r.get('pdf_file','')}")
                else:
                    st.info("No reports generated yet.")

    # ── TAB 3: Download any report ────────────────────────────────────────────
    with tab3:
        st.markdown("### All Saved Reports")
        REPORTS_DIR.mkdir(exist_ok=True)
        pdfs = sorted(REPORTS_DIR.glob("*.pdf"), reverse=True)
        if not pdfs:
            st.info("No PDF reports saved yet. (Reports appear here after users confirm payment.)")
        else:
            for pdf_path in pdfs:
                col1, col2 = st.columns([4,1])
                with col1: st.markdown(f"📄 `{pdf_path.name}`")
                with col2:
                    st.download_button(
                        "⬇️",
                        data=pdf_path.read_bytes(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"adl_{pdf_path.name}"
                    )
