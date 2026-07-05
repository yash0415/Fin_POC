"""
admin.py — Self-contained Admin Dashboard for FinSight
All CSS is injected here — does not depend on app.py styles.
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from auth import all_users, delete_user, admin_update_user, get_user
from db import (load_submissions, REPORTS_DIR, DATA_DIR, SUBS_FILE,
                 is_supabase_connected, get_connection_error, reset_connection)

# DATA_DIR, REPORTS_DIR, SUBS_FILE come from db.py imports


# ─────────────────────────────────────────────────────────────────────────────
# DB HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────
def run_db_check():
    """
    Runs a full Supabase connection test.
    Returns a dict of results for each test step.
    """
    results = {}
    from db import _get_sb, get_connection_error, DATA_DIR, REPORTS_DIR
    _get_supabase = _get_sb  # alias for readability

    # ── Test 1: Supabase secrets configured ──────────────────────────────────
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        if url and key and "supabase" in url:
            results["secrets"] = ("✅", "Secrets configured", f"URL: {url[:40]}...")
        else:
            results["secrets"] = ("❌", "Secrets incomplete", "URL or KEY appears empty")
    except KeyError as e:
        results["secrets"] = ("❌", "Secret missing", f"{e} not found in Streamlit Secrets")
    except Exception as e:
        results["secrets"] = ("❌", "Cannot read secrets", str(e))

    # ── Test 2: Supabase client creation ─────────────────────────────────────
    try:
        sb = _get_supabase()
        if sb:
            results["client"] = ("✅", "Client created", "Direct REST API connected successfully")
        else:
            err = get_connection_error() or "Could not connect to Supabase"
            results["client"] = ("❌", "Client failed", err)
    except Exception as e:
        results["client"] = ("❌", "Client error", str(e))

    # ── Test 3: Read from users table ─────────────────────────────────────────
    try:
        from db import _get_sb
        sb = _get_sb()
        if sb:
            rows = sb.select("users", cols="username", limit=1)
            results["read_users"] = ("✅", "Users table readable", f"Query successful — {len(rows)} row(s) returned")
        else:
            results["read_users"] = ("⚠️", "Skipped", "No Supabase client")
    except Exception as e:
        results["read_users"] = ("❌", "Users table error", f"{e} — Did you run supabase_setup.sql?")

    # ── Test 4: Read from submissions table ──────────────────────────────────
    try:
        from db import _get_sb
        sb = _get_sb()
        if sb:
            rows = sb.select("submissions", cols="id", limit=1)
            results["read_subs"] = ("✅", "Submissions table readable", f"Query successful — {len(rows)} row(s) returned")
        else:
            results["read_subs"] = ("⚠️", "Skipped", "No Supabase client")
    except Exception as e:
        results["read_subs"] = ("❌", "Submissions table error", f"{e} — Did you run supabase_setup.sql?")

    # ── Test 5: Write + delete test row ──────────────────────────────────────
    try:
        from db import _get_sb
        sb = _get_sb()
        if sb:
            test_user = {
                "username":   "__db_test__",
                "full_name":  "DB Test",
                "email":      "test@finsight-internal.test",
                "mobile":     "0000000000",
                "dob":        "2000-01-01",
                "age":        0,
                "password":   "test",
                "created_at": datetime.now().isoformat(),
                "reports":    [],
                "finance":    {},
            }
            sb.upsert("users", test_user)
            rows = sb.select("users", cols="username", filters={"username":"__db_test__"})
            if rows:
                sb.delete("users", {"username":"__db_test__"})
                results["write"] = ("✅", "Write & delete successful", "Inserted, read back, and deleted test row — DB fully working!")
            else:
                results["write"] = ("❌", "Write failed", "Row inserted but could not be read back")
        else:
            results["write"] = ("⚠️", "Skipped", "No Supabase client")
    except Exception as e:
        results["write"] = ("❌", "Write error", str(e))

    # ── Test 6: Local file system ─────────────────────────────────────────────
    try:
        DATA_DIR.mkdir(exist_ok=True)
        test_file = DATA_DIR / "_fs_test.txt"
        test_file.write_text("ok")
        test_file.read_text()
        test_file.unlink()
        results["filesystem"] = ("✅", "Local filesystem writable", str(DATA_DIR.resolve()))
    except Exception as e:
        results["filesystem"] = ("⚠️", "Filesystem not writable", f"{e} — On Streamlit Cloud, local files are ephemeral anyway")

    # ── Test 7: User count ────────────────────────────────────────────────────
    try:
        from db import get_all_users
        users = get_all_users()
        results["user_count"] = ("✅", f"{len(users)} registered user(s) in DB", 
                                  ", ".join(list(users.keys())[:5]) + ("..." if len(users)>5 else "") or "none yet")
    except Exception as e:
        results["user_count"] = ("❌", "Could not count users", str(e))

    return results


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

# _load_submissions removed — use db.load_submissions() instead

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
    db_tag = "🟢 Supabase — permanent" if is_supabase_connected() else "🟡 Local JSON — add Supabase"
    st.markdown(f"""<div class="admin-hero"><h2>🛡️ Admin Dashboard</h2><p>Yash Wankar · FinSight Portal</p><p style="font-size:.78rem;opacity:.8;margin-top:6px">{db_tag}</p></div>""", unsafe_allow_html=True)

    users = all_users()
    subs  = load_submissions()
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"📋 All Reports  ({len(subs)})",
        f"💰 Paid Only  ({len(paid_subs)})",
        f"👥 Users  ({len(users)})",
        f"📁 PDF Files  ({len(pdfs)})",
        "⚙️ Manage Users",
        "🔌 DB Status",
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


    # ═════════════════════════════════════════════════════════════════════════
    # TAB 6 — DB STATUS & HEALTH CHECK
    # ═════════════════════════════════════════════════════════════════════════
    with tab6:
        st.markdown('<div class="astl">🔌 Database Connection Status</div>', unsafe_allow_html=True)

        # Live status badge
        if is_supabase_connected():
            st.markdown("""
            <div style="background:#f0fdf4;border:2px solid #86efac;border-radius:14px;
                        padding:20px 28px;margin:12px 0;display:flex;align-items:center;gap:16px">
              <div style="font-size:2.5rem">🟢</div>
              <div>
                <div style="font-weight:700;color:#15803d;font-size:1.1rem">Supabase Connected</div>
                <div style="color:#166534;font-size:.85rem;margin-top:2px">
                  User data is stored permanently in the cloud database. 
                  Accounts will NOT be lost on app restart or redeploy.
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            conn_err = get_connection_error()
            err_html = f"<div style=\'background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:8px 12px;margin-top:8px;font-family:monospace;font-size:.8rem;color:#991b1b\'>{conn_err}</div>" if conn_err else ""
            st.markdown(f"""
            <div style="background:#fffbeb;border:2px solid #fcd34d;border-radius:14px;
                        padding:20px 28px;margin:12px 0">
              <div style="display:flex;align-items:center;gap:16px">
                <div style="font-size:2.5rem">🟡</div>
                <div>
                  <div style="font-weight:700;color:#92400e;font-size:1.1rem">Not Connected to Supabase</div>
                  <div style="color:#78350f;font-size:.85rem;margin-top:2px">
                    Data stored in local files only — users lost on Streamlit Cloud restart.
                  </div>
                </div>
              </div>
              {err_html}
            </div>""", unsafe_allow_html=True)

        # Show secrets status
        st.markdown('<div class="astl">🔑 Secrets Configuration</div>', unsafe_allow_html=True)
        secret_keys = ["ADMIN_USER","ADMIN_PASS","SUPABASE_URL","SUPABASE_KEY","TWILIO_SID","TWILIO_TOKEN","TWILIO_VERIFY_SID"]
        sc1, sc2 = st.columns(2)
        for i, key in enumerate(secret_keys):
            col = sc1 if i % 2 == 0 else sc2
            with col:
                try:
                    val = st.secrets[key]
                    if val:
                        # Show partially masked value
                        masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "****"
                        st.markdown(f"""
                        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
                                    padding:10px 14px;margin:4px 0">
                          <div style="font-size:.68rem;font-weight:700;color:#94a3b8;text-transform:uppercase">{key}</div>
                          <div style="font-size:.9rem;font-weight:600;color:#15803d">✅ Set &nbsp;<span style="font-family:monospace;font-size:.8rem;color:#64748b">{masked}</span></div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;
                                    padding:10px 14px;margin:4px 0">
                          <div style="font-size:.68rem;font-weight:700;color:#94a3b8;text-transform:uppercase">{key}</div>
                          <div style="font-size:.9rem;font-weight:600;color:#ef4444">❌ Not set</div>
                        </div>""", unsafe_allow_html=True)
                except Exception:
                    st.markdown(f"""
                    <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;
                                padding:10px 14px;margin:4px 0">
                      <div style="font-size:.68rem;font-weight:700;color:#94a3b8;text-transform:uppercase">{key}</div>
                      <div style="font-size:.9rem;color:#ef4444">❌ Not set</div>
                    </div>""", unsafe_allow_html=True)

        # Run full check button
        st.markdown('<div class="astl">🧪 Run Full Connection Test</div>', unsafe_allow_html=True)
        st.caption("Tests each step: secrets → client → read users table → read submissions table → write test row → delete test row")

        bc1, bc2 = st.columns([2,1])
        with bc1: run_check = st.button("▶️ Run DB Health Check Now", type="primary", use_container_width=True, key="btn_run_dbcheck")
        with bc2:
            if st.button("🔄 Reset Connection", use_container_width=True, key="btn_reset_conn"):
                reset_connection()
                st.success("Connection reset — run health check again.")
                st.rerun()
        if run_check:
            with st.spinner("Running connection tests..."):
                reset_connection()  # force fresh connection test
                results = run_db_check()

            test_labels = {
                "secrets":      "Secrets configured",
                "client":       "Supabase client created",
                "read_users":   "Read from users table",
                "read_subs":    "Read from submissions table",
                "write":        "Write + delete test row",
                "filesystem":   "Local filesystem",
                "user_count":   "Users in database",
            }
            all_passed = all(v[0] == "✅" for v in results.values())

            if all_passed:
                st.success("✅ All tests passed! Database is fully connected and working.")
            else:
                failed = [k for k, v in results.items() if v[0] == "❌"]
                st.error(f"❌ {len(failed)} test(s) failed: {', '.join(failed)}")

            for key, (icon, title, detail) in results.items():
                bg    = "#f0fdf4" if icon=="✅" else "#fef2f2" if icon=="❌" else "#fffbeb"
                bord  = "#86efac" if icon=="✅" else "#fca5a5" if icon=="❌" else "#fcd34d"
                tcolor= "#15803d" if icon=="✅" else "#991b1b" if icon=="❌" else "#92400e"
                dcolor= "#166534" if icon=="✅" else "#7f1d1d" if icon=="❌" else "#78350f"
                label = test_labels.get(key, key)
                st.markdown(f"""
                <div style="background:{bg};border:1px solid {bord};border-radius:10px;
                            padding:12px 18px;margin:5px 0">
                  <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:1.2rem">{icon}</span>
                    <div>
                      <div style="font-weight:700;color:{tcolor};font-size:.9rem">{label}</div>
                      <div style="color:{dcolor};font-size:.8rem;margin-top:2px">{detail}</div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # Quick fix guide
        st.markdown('<div class="astl">🛠️ Troubleshooting</div>', unsafe_allow_html=True)
        with st.expander("❌ Users table or submissions table errors"):
            st.markdown("""
1. Go to your **Supabase project → SQL Editor**
2. Open the file `supabase_setup.sql` (included in the zip)
3. Paste the contents and click **Run**
4. This creates the `users` and `submissions` tables with correct structure
5. Re-run the health check above
            """)
        with st.expander("❌ Secrets not set / client failed — click to fix"):
            st.markdown("""
**The most common cause:** Wrong Supabase key type.

Supabase now shows two keys in Settings → API:
- ❌ `sb_publishable_...` — this is the NEW format publishable key — **DO NOT USE**
- ✅ `eyJhbGci...` — this is the JWT anon key — **USE THIS ONE**

**Steps to get the correct key:**
1. Go to your Supabase project
2. Click **Settings** (gear icon) → **API**
3. Scroll to **Project API keys**
4. Copy the key labelled **anon** / **public** — it starts with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
5. Go to Streamlit Cloud → your app → **Settings → Secrets**
6. Update `SUPABASE_KEY` with the `eyJ...` key
7. Click **Save** → **Reboot app**
            """)
            st.warning("⚠️ If your key starts with `sb_pub` or `sb_publishable` — that is the wrong key. You need the long JWT key starting with `eyJ`.")
        with st.expander("✅ Connected but users still disappear?"):
            st.markdown("""
- Make sure `SUPABASE_URL` and `SUPABASE_KEY` are set in Streamlit Secrets
- The 🟢 badge at the top of the sidebar confirms Supabase is active
- If you see 🟡 (local mode), secrets are missing — add them and reboot the app
- Run the health check above and look for any ❌ failed tests
            """)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 5 — MANAGE USERS (edit / delete)
    # ═════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown('<div class="astl">⚙️ Manage Users — Edit or Remove</div>', unsafe_allow_html=True)

        users_fresh = all_users()
        if not users_fresh:
            st.markdown("""
            <div class="empty-state"><div class="empty-icon">👥</div>
              <div class="empty-title">No users yet</div></div>""", unsafe_allow_html=True)
        else:
            sel_manage = st.selectbox("Select user to manage:", ["— select —"] + list(users_fresh.keys()), key="t5_sel")
            if sel_manage != "— select —":
                u = users_fresh[sel_manage]
                st.markdown(f"### Managing: **{u.get('full_name', sel_manage)}** (`{sel_manage}`)")

                action = st.radio("Action:", ["✏️ Edit Info", "🔑 Reset Password", "🗑️ Delete User"],
                                   horizontal=True, key="t5_action")

                if action == "✏️ Edit Info":
                    st.markdown("**Edit user details:**")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        new_name  = st.text_input("Full Name",    value=u.get("full_name",""),  key="t5_name")
                        new_email = st.text_input("Email",        value=u.get("email",""),       key="t5_email")
                    with ec2:
                        new_mob   = st.text_input("Mobile (10 digits)", value=u.get("mobile",""), key="t5_mob")
                        new_dob   = st.text_input("Date of Birth (YYYY-MM-DD)", value=u.get("dob",""), key="t5_dob")
                    if st.button("💾 Save Changes", type="primary", key="t5_save"):
                        ok, msg = admin_update_user(sel_manage, {
                            "full_name": new_name, "email": new_email,
                            "mobile": new_mob, "dob": new_dob,
                        })
                        if ok: st.success(f"✅ {msg}")
                        else:  st.error(f"❌ {msg}")

                elif action == "🔑 Reset Password":
                    st.markdown("**Set a new password for this user:**")
                    new_pw  = st.text_input("New Password (min 6 chars)", type="password", key="t5_pw1")
                    new_pw2 = st.text_input("Confirm Password", type="password", key="t5_pw2")
                    if st.button("🔐 Reset Password", type="primary", key="t5_pw_btn"):
                        if new_pw != new_pw2:
                            st.error("❌ Passwords do not match.")
                        elif len(new_pw) < 6:
                            st.error("❌ Password must be at least 6 characters.")
                        else:
                            ok, msg = admin_update_user(sel_manage, {"new_password": new_pw})
                            if ok: st.success(f"✅ Password reset for {sel_manage}.")
                            else:  st.error(f"❌ {msg}")

                elif action == "🗑️ Delete User":
                    st.markdown(f"""
                    <div style="background:#fef2f2;border:2px solid #fca5a5;border-radius:12px;
                                padding:20px 24px;margin:12px 0">
                      <div style="font-weight:700;color:#991b1b;font-size:1rem;margin-bottom:8px">
                        ⚠️ Delete User: {u.get("full_name", sel_manage)}
                      </div>
                      <div style="color:#7f1d1d;font-size:.88rem">
                        This will permanently delete the user account and all their data from users.json.
                        PDF reports on disk will <b>not</b> be deleted. This action cannot be undone.
                      </div>
                    </div>""", unsafe_allow_html=True)
                    confirm = st.text_input(f"Type the username `{sel_manage}` to confirm deletion:", key="t5_confirm")
                    if st.button("🗑️ Permanently Delete User", key="t5_del_btn"):
                        if confirm.strip() != sel_manage:
                            st.error("❌ Username does not match. Deletion cancelled.")
                        else:
                            ok, msg = delete_user(sel_manage)
                            if ok:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")