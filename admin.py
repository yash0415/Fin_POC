"""
admin.py — Self-contained Admin Dashboard for FinSight
All CSS is injected here — does not depend on app.py styles.
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from auth import all_users

DATA_DIR    = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
SUBS_FILE   = DATA_DIR / "submissions.json"

# ── Ensure folders exist ───────────────────────────────────────────────────────
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fmt_amt(n):
    try:
        n = float(n)
        if abs(n) >= 1e7: return f"₹{n/1e7:.2f} Cr"
        if abs(n) >= 1e5: return f"₹{n/1e5:.2f} L"
        return f"₹{n:,.0f}"
    except Exception:
        return "₹—"

def _load_submissions():
    if SUBS_FILE.exists():
        try:
            return json.loads(SUBS_FILE.read_text())
        except Exception:
            return []
    return []

def _score_badge(score):
    try:
        sc = int(score)
        if sc >= 75: return f"🟢 {sc}/100 Excellent"
        if sc >= 55: return f"🟡 {sc}/100 Good"
        if sc >= 35: return f"🟠 {sc}/100 Needs Work"
        return f"🔴 {sc}/100 Critical"
    except Exception:
        return f"{score}/100"


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN CSS  (self-contained — injected here, not relying on app.py styles)
# ─────────────────────────────────────────────────────────────────────────────
ADMIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap');

/* ── Base ── */
[class*="css"] { font-family: 'Inter', sans-serif; }

/* ── KPI cards ── */
.akpi {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-top: 4px solid #0e6b4a;
    border-radius: 14px;
    padding: 18px 22px;
    margin: 4px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.akpi.r  { border-top-color: #ef4444; }
.akpi.a  { border-top-color: #f59e0b; }
.akpi.b  { border-top-color: #3b82f6; }
.akpi.p  { border-top-color: #8b5cf6; }
.akpi-lbl { font-size: .68rem; font-weight: 700; text-transform: uppercase;
             letter-spacing: .07em; color: #94a3b8; margin-bottom: 5px; }
.akpi-val { font-family: 'JetBrains Mono', monospace; font-size: 1.6rem;
             font-weight: 600; color: #0f172a; line-height: 1.1; }
.akpi-sub { font-size: .72rem; color: #64748b; margin-top: 3px; }

/* ── Sub card (per submission) ── */
.sub-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 5px solid #0e6b4a;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 10px 0;
    box-shadow: 0 2px 6px rgba(0,0,0,.05);
}
.sub-card.pending { border-left-color: #f59e0b; }
.sub-card.auto    { border-left-color: #3b82f6; }
.sub-hd   { font-weight: 700; font-size: 1rem; color: #0f172a; margin-bottom: 2px; }
.sub-meta { font-size: .8rem; color: #64748b; margin-bottom: 10px; }
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: .68rem; font-weight: 700; letter-spacing: .04em;
    text-transform: uppercase; margin-left: 6px; vertical-align: middle;
}
.badge.paid   { background: #dcfce7; color: #15803d; }
.badge.auto   { background: #dbeafe; color: #1d4ed8; }
.badge.pend   { background: #fef9c3; color: #854d0e; }

/* ── Info row inside sub card ── */
.info-row { display: flex; gap: 24px; flex-wrap: wrap; margin: 8px 0; }
.info-item { min-width: 120px; }
.info-lbl  { font-size: .67rem; font-weight: 700; color: #94a3b8;
              text-transform: uppercase; letter-spacing: .05em; }
.info-val  { font-size: .9rem; font-weight: 600; color: #1e293b; margin-top: 1px; }

/* ── Report file row ── */
.rfile {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 12px 16px; margin: 6px 0;
    display: flex; align-items: center; justify-content: space-between;
}
.rfile-name { font-family: 'JetBrains Mono', monospace; font-size: .8rem; color: #334155; }
.rfile-meta { font-size: .72rem; color: #94a3b8; margin-top: 2px; }

/* ── Section title ── */
.astl {
    font-family: 'DM Serif Display', serif; font-size: 1.25rem; color: #0f2d52;
    margin: 22px 0 12px; padding-bottom: 6px; border-bottom: 2px solid #e2e8f0;
}

/* ── Admin hero ── */
.admin-hero {
    background: linear-gradient(135deg, #0f2d52 0%, #0e6b4a 100%);
    border-radius: 16px; padding: 28px 36px; color: white; margin-bottom: 24px;
}
.admin-hero h2 { font-family:'DM Serif Display',serif; font-size:2rem;
                  margin:0 0 4px; color:white; }
.admin-hero p  { margin:0; opacity:.75; font-size:.88rem; }

/* ── Empty state ── */
.empty-state {
    background: #f8fafc; border: 2px dashed #e2e8f0; border-radius: 14px;
    padding: 40px; text-align: center; margin: 16px 0;
}
.empty-icon  { font-size: 2.4rem; margin-bottom: 10px; }
.empty-title { font-weight: 600; color: #475569; font-size: 1rem; }
.empty-sub   { font-size: .82rem; color: #94a3b8; margin-top: 4px; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────
def render():
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)

    # ── Hero Banner ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="admin-hero">
      <h2>🛡️ Admin Dashboard</h2>
      <p>Yash Wankar · FinSight Internal Portal · All user data & reports</p>
    </div>""", unsafe_allow_html=True)

    users = all_users()
    subs  = _load_submissions()
    pdfs  = sorted(REPORTS_DIR.glob("*.pdf"), reverse=True)

    paid_subs  = [s for s in subs if s.get("paid")]
    auto_subs  = [s for s in subs if s.get("auto_save")]
    pend_subs  = [s for s in subs if not s.get("paid") and not s.get("auto_save")]
    total_rev  = len(paid_subs) * 100

    # ── KPI Row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f'<div class="akpi b"><div class="akpi-lbl">Registered Users</div><div class="akpi-val">{len(users)}</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="akpi"><div class="akpi-lbl">Auto-Saved Reports</div><div class="akpi-val">{len(auto_subs)}</div><div class="akpi-sub">Dashboard visited</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="akpi"><div class="akpi-lbl">Paid Reports</div><div class="akpi-val">{len(paid_subs)}</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="akpi p"><div class="akpi-lbl">Revenue Collected</div><div class="akpi-val">₹{total_rev:,}</div></div>', unsafe_allow_html=True)
    with k5:
        st.markdown(f'<div class="akpi a"><div class="akpi-lbl">Total PDF Files</div><div class="akpi-val">{len(pdfs)}</div><div class="akpi-sub">in data/reports/</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        f"📋 All Reports  ({len(subs)})",
        f"💰 Paid Only  ({len(paid_subs)})",
        f"👥 Users  ({len(users)})",
        f"📁 PDF Files  ({len(pdfs)})",
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1 — ALL REPORTS (auto-saved + paid)
    # ═════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown('<div class="astl">All Reports — newest first</div>', unsafe_allow_html=True)

        # Filter bar
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            ftype = st.selectbox("Filter by type", ["All", "Auto-Saved (unpaid)", "Paid", "Pending screenshot"], key="t1f1")
        with fc2:
            fsearch = st.text_input("Search by name / username / city", placeholder="type to search…", key="t1f2")
        with fc3:
            fsort = st.selectbox("Sort", ["Newest first", "Oldest first", "Score ↓", "Score ↑"], key="t1f3")

        # Apply filters
        filtered = list(reversed(subs))
        if ftype == "Auto-Saved (unpaid)":
            filtered = [s for s in filtered if s.get("auto_save")]
        elif ftype == "Paid":
            filtered = [s for s in filtered if s.get("paid")]
        elif ftype == "Pending screenshot":
            filtered = [s for s in filtered if not s.get("paid") and not s.get("auto_save")]
        if fsearch.strip():
            q = fsearch.strip().lower()
            filtered = [s for s in filtered if
                        q in s.get("name","").lower() or
                        q in s.get("full_name","").lower() or
                        q in s.get("username","").lower() or
                        q in s.get("city","").lower() or
                        q in s.get("email","").lower()]
        if fsort == "Oldest first":
            filtered = list(reversed(filtered))
        elif fsort == "Score ↓":
            filtered = sorted(filtered, key=lambda x: int(x.get("score",0)), reverse=True)
        elif fsort == "Score ↑":
            filtered = sorted(filtered, key=lambda x: int(x.get("score",0)))

        if not filtered:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-icon">📭</div>
              <div class="empty-title">No reports yet</div>
              <div class="empty-sub">Reports appear here automatically as soon as any user opens the Dashboard page.</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"**Showing {len(filtered)} record(s)**")

            for i, sub in enumerate(filtered):
                is_paid = sub.get("paid", False)
                is_auto = sub.get("auto_save", False)

                card_cls = "paid" if is_paid else "auto" if is_auto else "pending"
                if is_paid:
                    badge_html = '<span class="badge paid">✅ PAID</span>'
                elif is_auto:
                    badge_html = '<span class="badge auto">🔵 AUTO-SAVED</span>'
                else:
                    badge_html = '<span class="badge pend">⏳ PENDING</span>'

                name_disp = sub.get("full_name") or sub.get("name") or "Unknown"
                dt_disp   = sub.get("saved_at","")[:16].replace("_"," ") or "—"

                with st.expander(f"{name_disp}  ·  {dt_disp}  {badge_html}", expanded=(i==0)):
                    # Row 1: personal details
                    st.markdown('<div class="info-row">', unsafe_allow_html=True)
                    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                    with r1c1:
                        st.markdown(f"**👤 Name**  \n{name_disp}")
                        st.markdown(f"**🔑 Username**  \n`{sub.get('username','—')}`")
                    with r1c2:
                        st.markdown(f"**📧 Email**  \n{sub.get('email','—')}")
                        st.markdown(f"**📱 Phone**  \n{sub.get('phone','—') or '—'}")
                    with r1c3:
                        st.markdown(f"**📍 City**  \n{sub.get('city','—')}")
                        st.markdown(f"**🎂 Age**  \n{sub.get('age','—')}")
                    with r1c4:
                        st.markdown(f"**💰 Salary**  \n{fmt_amt(sub.get('salary',0))}/mo")
                        st.markdown(f"**🏛️ Net Worth**  \n{fmt_amt(sub.get('net_worth',0))}")

                    st.markdown("---")

                    # Row 2: score + payment + download
                    r2c1, r2c2, r2c3 = st.columns(3)
                    with r2c1:
                        st.markdown(f"**📊 Health Score**  \n{_score_badge(sub.get('score',0))}")
                        st.markdown(f"**🗓️ Saved at**  \n{dt_disp}")
                    with r2c2:
                        st.markdown(f"**💳 UPI**  \n{sub.get('upi_id','—') or '—'}")
                        pf = sub.get("pdf_file","")
                        st.markdown(f"**📄 PDF File**  \n`{pf or 'not saved'}`")
                    with r2c3:
                        # ── Download PDF ──────────────────────────────────────
                        pf = sub.get("pdf_file","")
                        if pf:
                            pdf_path = REPORTS_DIR / pf
                            if pdf_path.exists():
                                st.download_button(
                                    "⬇️ Download PDF Report",
                                    data=pdf_path.read_bytes(),
                                    file_name=pf,
                                    mime="application/pdf",
                                    key=f"t1_dl_{i}_{pf[:20]}",
                                    use_container_width=True,
                                )
                            else:
                                st.warning(f"PDF not found on disk:\n`{pf}`")
                        else:
                            st.info("No PDF linked to this record.")

                        # ── Payment Screenshot ────────────────────────────────
                        sf = sub.get("screenshot_file","")
                        if sf:
                            ss_path = REPORTS_DIR / sf
                            if ss_path.exists():
                                st.image(str(ss_path), caption="💳 Payment Screenshot", use_column_width=True)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2 — PAID ONLY
    # ═════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown('<div class="astl">Paid Reports — Confirmed Payments</div>', unsafe_allow_html=True)
        if not paid_subs:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-icon">💰</div>
              <div class="empty-title">No paid reports yet</div>
              <div class="empty-sub">Once a user uploads their payment screenshot and confirms, it appears here.</div>
            </div>""", unsafe_allow_html=True)
        else:
            # Summary table
            rows = []
            for sub in reversed(paid_subs):
                rows.append({
                    "Name":      sub.get("full_name") or sub.get("name","—"),
                    "Username":  sub.get("username","—"),
                    "Score":     f"{sub.get('score','—')}/100",
                    "Salary":    fmt_amt(sub.get("salary",0)),
                    "Phone":     sub.get("phone","—"),
                    "City":      sub.get("city","—"),
                    "Date":      sub.get("saved_at","")[:16].replace("_"," "),
                    "PDF":       "✅" if sub.get("pdf_file") and (REPORTS_DIR/sub["pdf_file"]).exists() else "❌",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("**Download individual reports:**")
            for i, sub in enumerate(reversed(paid_subs)):
                pf = sub.get("pdf_file","")
                name = sub.get("full_name") or sub.get("name","Client")
                if pf:
                    pdf_path = REPORTS_DIR / pf
                    if pdf_path.exists():
                        pc1, pc2 = st.columns([5,2])
                        with pc1:
                            st.markdown(f"📄 **{name}** — {sub.get('saved_at','')[:16].replace('_',' ')}")
                        with pc2:
                            st.download_button(
                                "⬇️ Download",
                                data=pdf_path.read_bytes(),
                                file_name=pf,
                                mime="application/pdf",
                                key=f"t2_dl_{i}",
                                use_container_width=True,
                            )

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 3 — USERS
    # ═════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="astl">All Registered Users</div>', unsafe_allow_html=True)
        if not users:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-icon">👥</div>
              <div class="empty-title">No users yet</div>
              <div class="empty-sub">Users appear here after they create an account.</div>
            </div>""", unsafe_allow_html=True)
        else:
            rows = []
            for uname, u in users.items():
                n_rpts = len(u.get("reports",[]))
                rows.append({
                    "Username":   uname,
                    "Full Name":  u.get("full_name","—"),
                    "Email":      u.get("email","—"),
                    "Joined":     u.get("created_at","—")[:10],
                    "Reports":    n_rpts,
                    "Status":     "✅ Active" if n_rpts > 0 else "🆕 New",
                })
            df_u = pd.DataFrame(rows)
            st.dataframe(df_u, use_container_width=True, hide_index=True)

            st.markdown("---")
            sel = st.selectbox("🔍 View a specific user's reports:", ["— select user —"] + list(users.keys()), key="t3_sel")
            if sel != "— select user —":
                u = users[sel]
                st.markdown(f"### 👤 {u.get('full_name',sel)}")
                uc1, uc2, uc3 = st.columns(3)
                with uc1: st.markdown(f"**Email:** {u.get('email','—')}")
                with uc2: st.markdown(f"**Joined:** {u.get('created_at','—')[:10]}")
                with uc3: st.markdown(f"**Reports:** {len(u.get('reports',[]))}")

                reps = u.get("reports",[])
                if reps:
                    for r in reversed(reps):
                        pf = r.get("pdf_file","")
                        rc1, rc2, rc3 = st.columns([3,2,2])
                        with rc1:
                            label = "AUTO-SAVE" if r.get("auto_save") else "PAID"
                            st.markdown(f"📄 `{pf}` — [{label}]")
                        with rc2:
                            st.markdown(f"Score: **{_score_badge(r.get('score','—'))}**")
                        with rc3:
                            if pf:
                                pp = REPORTS_DIR / pf
                                if pp.exists():
                                    st.download_button(
                                        "⬇️ Download",
                                        data=pp.read_bytes(),
                                        file_name=pf,
                                        mime="application/pdf",
                                        key=f"t3_dl_{sel}_{pf[:15]}",
                                        use_container_width=True,
                                    )
                                else:
                                    st.caption("File not on disk")
                else:
                    st.info("This user hasn't visited the Dashboard yet.")

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 4 — ALL PDF FILES ON DISK
    # ═════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown('<div class="astl">All PDF Files in data/reports/</div>', unsafe_allow_html=True)
        st.caption(f"📁 Folder: `{REPORTS_DIR.resolve()}`")

        pdfs = sorted(REPORTS_DIR.glob("*.pdf"), reverse=True)
        if not pdfs:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-icon">📂</div>
              <div class="empty-title">No PDF files on disk yet</div>
              <div class="empty-sub">
                PDFs are saved automatically when any logged-in user opens the Dashboard page.<br>
                Ask a test user to fill in their data and click Dashboard to see a file appear here.
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(pdfs)} PDF file(s) found:**")
            for pdf_path in pdfs:
                size_kb = pdf_path.stat().st_size / 1024
                is_auto = pdf_path.name.startswith("AUTO_")
                fc1, fc2, fc3 = st.columns([5, 1, 1])
                with fc1:
                    label = "🔵 AUTO" if is_auto else "💰 PAID"
                    st.markdown(f"**{label}** · `{pdf_path.name}`  \n<span style='font-size:.75rem;color:#94a3b8'>{size_kb:.1f} KB</span>", unsafe_allow_html=True)
                with fc2:
                    st.caption(f"{size_kb:.0f} KB")
                with fc3:
                    st.download_button(
                        "⬇️",
                        data=pdf_path.read_bytes(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"t4_dl_{pdf_path.name}",
                        use_container_width=True,
                    )

        # Screenshot files too
        screenshots = list(REPORTS_DIR.glob("*_ss.*")) + list(REPORTS_DIR.glob("*_screenshot.*"))
        if screenshots:
            st.markdown("---")
            st.markdown(f"**{len(screenshots)} payment screenshot(s):**")
            for i, ss in enumerate(sorted(screenshots, reverse=True)):
                sc1, sc2 = st.columns([4,1])
                with sc1: st.markdown(f"🖼️ `{ss.name}`")
                with sc2:
                    if st.button("👁️ View", key=f"ss_view_{i}"):
                        st.image(str(ss), caption=ss.name, use_column_width=True)
