from __future__ import annotations

import pandas as pd
import streamlit as st

from audit import append_event, read_events
from data import make_demo_transactions
from engine import analyze, run_batch

st.set_page_config(page_title="RecoverAI", page_icon="↗", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {max-width: 1400px; padding-top: 2rem;}
.hero {padding: 24px 28px; border: 1px solid rgba(128,128,128,.22); border-radius: 20px; background: linear-gradient(135deg, rgba(99,102,241,.10), rgba(16,185,129,.08)); margin-bottom: 22px;}
.card {padding: 18px; border: 1px solid rgba(128,128,128,.20); border-radius: 16px; background: rgba(128,128,128,.045);}
.small {color: #6b7280; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

if "df" not in st.session_state:
    st.session_state.df = make_demo_transactions(seed=42)
if "amount_limit" not in st.session_state:
    st.session_state.amount_limit = 10000.0
if "risk_limit" not in st.session_state:
    st.session_state.risk_limit = 0.65

with st.sidebar:
    st.header("Merchant policy")
    st.caption("These controls are enforced by the policy gate before any autonomous action.")
    st.session_state.amount_limit = st.slider("Autonomous action limit (₹)", 1000, 25000, int(st.session_state.amount_limit), 1000)
    st.session_state.risk_limit = st.slider("Maximum autonomous risk", 0.10, 0.90, float(st.session_state.risk_limit), 0.05)
    st.divider()
    if st.button("Regenerate demo data", use_container_width=True):
        st.session_state.df = make_demo_transactions(seed=99)
        append_event("dataset_regenerated", {"seed": 99})
        st.rerun()
    st.info("Demo mode only: no live-money action is performed. Razorpay test-mode integration is isolated in razorpay_adapter.py.")

an = analyze(st.session_state.df, st.session_state.amount_limit, st.session_state.risk_limit)

st.markdown('<div class="hero"><h1>RecoverAI</h1><p style="font-size:1.15rem;margin-bottom:8px"><b>Autonomous Revenue Recovery Agent</b></p><p>Detect revenue leakage → diagnose → decide → safely act → measure recovery</p><p class="small">Razorpay AI Buildathon 2026 • Track 3 • Synthetic benchmark environment</p></div>', unsafe_allow_html=True)

risk = an[an.recovery_score > 0]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Revenue at risk", f"₹{risk.amount.sum():,.0f}")
col2.metric("Expected recoverable", f"₹{risk.expected_recovery.sum():,.0f}")
col3.metric("High-priority cases", f"{int((risk.recovery_score >= .55).sum())}")
col4.metric("Auto-eligible", f"{int(risk.auto_approved.sum())}")

st.caption(f"Active safety policy: actions ≤ ₹{st.session_state.amount_limit:,.0f} and risk < {st.session_state.risk_limit:.0%}; Smart retry stops after 2 attempts.")
st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["Command Center", "Decision Engine", "Recovery Run", "Audit & Metrics"])

with tab1:
    st.markdown("### Where is money leaking?")
    leak = an.groupby("failure_label", as_index=False).agg(
        transactions=("transaction_id", "count"),
        amount_at_risk=("amount", "sum"),
        expected_recovery=("expected_recovery", "sum"),
    ).sort_values("amount_at_risk", ascending=False)
    st.bar_chart(leak.set_index("failure_label")["amount_at_risk"])
    st.dataframe(leak.style.format({"amount_at_risk": "₹{:,.0f}", "expected_recovery": "₹{:,.0f}"}), use_container_width=True, hide_index=True)

    st.markdown("### Priority queue")
    view = an[["transaction_id", "amount", "failure_label", "customer_orders", "customer_ltv", "risk_score", "recovery_score", "best_action", "expected_recovery", "auto_approved"]].copy()
    view = view.sort_values("expected_recovery", ascending=False).head(15)
    st.dataframe(view.style.format({"amount":"₹{:,.0f}", "customer_ltv":"₹{:,.0f}", "expected_recovery":"₹{:,.0f}", "risk_score":"{:.0%}", "recovery_score":"{:.0%}"}), use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### AI decision engine")
    st.caption("The agent proposes the next-best action; deterministic policy rules make the final autonomous decision.")
    selected = st.selectbox("Select a transaction", an.transaction_id.tolist())
    row = an[an.transaction_id == selected].iloc[0]
    approved, checks = (row.auto_approved, row.policy_checks)

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown(f"**Transaction:** `{row.transaction_id}`  ·  **Amount:** ₹{row.amount:,.0f}")
        st.markdown("#### Diagnosis")
        st.write(row.diagnosis)
        st.markdown("#### Next-best action")
        if approved:
            st.success(f"✓ {row.best_action} — expected recovery ₹{row.expected_recovery:,.0f}")
        else:
            st.warning(f"⚠ {row.best_action} — human approval required")
        st.write(row.recommendation_reason)
    with right:
        st.markdown("#### Policy gate")
        for check in checks:
            st.write(f"• {check}")
        st.markdown("**Decision:** " + ("AUTONOMOUS" if approved else "ESCALATE"))

    st.markdown("#### Ranked actions")
    action_table = pd.DataFrame([{"action": a.name, "success_probability": a.score, "expected_recovery": a.expected_recovery, "autonomous": a.auto_allowed} for a in row.actions])
    st.dataframe(action_table.style.format({"success_probability":"{:.0%}", "expected_recovery":"₹{:,.0f}"}), hide_index=True, use_container_width=True)

with tab3:
    st.markdown("### Execute a bounded recovery batch")
    st.write("Run the same decision policy across the portfolio. Outcomes are deterministic synthetic simulations, so your pitch demo is reproducible.")
    if st.button("▶ Run recovery agent", type="primary", use_container_width=True):
        results, metrics = run_batch(an, st.session_state.amount_limit, st.session_state.risk_limit)
        st.session_state.results = results
        st.session_state.metrics = metrics
        append_event("recovery_batch", {"approved": metrics["approved"], "blocked": metrics["blocked"], "recovered": metrics["recovered"]})
        st.success(f"Batch complete — ₹{metrics['recovered']:,.0f} simulated revenue recovered.")

    if "results" in st.session_state:
        m = st.session_state.metrics
        a,b,c,d = st.columns(4)
        a.metric("Recovered", f"₹{m['recovered']:,.0f}")
        b.metric("Recovery rate", f"{m['recovery_rate']:.1%}")
        c.metric("Approved actions", m["approved"])
        d.metric("Blocked / escalated", m["blocked"])
        st.dataframe(st.session_state.results, use_container_width=True, hide_index=True)

with tab4:
    st.markdown("### Measurement & audit trail")
    if "results" not in st.session_state:
        st.info("Run a recovery batch to populate outcome metrics.")
    else:
        r = st.session_state.results
        m = st.session_state.metrics
        st.write("Figures are benchmark results from synthetic data, not production Razorpay statistics.")
        status = r.groupby("status", as_index=False).agg(count=("transaction_id", "count"), recovered=("recovered", "sum"))
        st.dataframe(status.style.format({"recovered":"₹{:,.0f}"}), use_container_width=True, hide_index=True)
        st.markdown("#### Recent audit events")
        events = read_events()
        if events:
            st.dataframe(pd.DataFrame(events[-20:]).iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.caption("No audit events yet. Run the recovery agent to create one.")

st.divider()
st.caption("RecoverAI is a hackathon prototype. Never place production credentials in source control; keep financial actions policy-gated and use test mode while demonstrating.")
