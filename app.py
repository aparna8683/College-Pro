from __future__ import annotations

import streamlit as st
import pandas as pd

from data import make_demo_transactions
from engine import analyze, run_batch

st.set_page_config(page_title="RecoverAI", page_icon="↗", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1400px; padding-top: 2rem;}
.metric-card {padding: 18px; border: 1px solid rgba(128,128,128,.22); border-radius: 16px; background: rgba(128,128,128,.06);}
.small {color: #6b7280; font-size: .9rem;}
.badge {padding: 4px 9px; border-radius: 999px; font-size: .78rem; border: 1px solid rgba(128,128,128,.25);}
</style>
""", unsafe_allow_html=True)

st.title("RecoverAI")
st.subheader("Autonomous Revenue Recovery Agent")
st.markdown("**Detect revenue leakage → diagnose → decide → safely act → measure recovery**")
st.caption("Hackathon prototype • Track 3: AI Revenue Recovery • Synthetic demo data")

if "df" not in st.session_state:
    st.session_state.df = make_demo_transactions()
if "analysis" not in st.session_state:
    st.session_state.analysis = analyze(st.session_state.df)

with st.sidebar:
    st.header("Merchant controls")
    amount_limit = st.slider("Autonomous action limit (₹)", 1000, 25000, 10000, 1000)
    risk_limit = st.slider("Maximum autonomous risk", 0.1, 0.9, 0.65, 0.05)
    st.divider()
    if st.button("Regenerate demo data"):
        st.session_state.df = make_demo_transactions(seed=99)
        st.session_state.analysis = analyze(st.session_state.df)
        st.rerun()
    st.info("No live-money action is performed by the default demo. Razorpay test-mode integration is isolated in razorpay_adapter.py.")

an = st.session_state.analysis

risk = an[an.recovery_score > 0]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Revenue at risk", f"₹{risk.amount.sum():,.0f}")
col2.metric("Expected recoverable", f"₹{risk.expected_recovery.sum():,.0f}")
col3.metric("High-priority cases", f"{int((risk.recovery_score >= .55).sum())}")
col4.metric("Auto-eligible", f"{int(risk.auto_approved.sum())}")

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
    st.dataframe(view.style.format({"amount":"₹{:,.0f}", "customer_ltv":"₹{:,.0f}", "expected_recovery":"₹{:,.0f}", "risk_score":"{:.0%}", "recovery_score":"{:.0%}",}), use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### Next-best-action explanation")
    selected = st.selectbox("Select a transaction", an.transaction_id.tolist())
    row = an[an.transaction_id == selected].iloc[0]
    st.write(f"**Transaction:** {row.transaction_id} · **Amount:** ₹{row.amount:,.0f}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Diagnosis")
        st.write(row.diagnosis)
        st.markdown("#### Recommended action")
        st.success(f"{row.best_action} — expected recovery ₹{row.expected_recovery:,.0f}")
        st.write(row.recommendation_reason)
    with c2:
        st.markdown("#### Ranked actions")
        action_table = pd.DataFrame([{"action": a.name, "success_probability": a.expected_recovery / row.amount, "expected_recovery": a.expected_recovery} for a in row.actions])
        st.dataframe(action_table.style.format({"success_probability":"{:.0%}", "expected_recovery":"₹{:,.0f}"}), hide_index=True, use_container_width=True)
        st.markdown("#### Safety gate")
        st.write("Autonomous" if row.auto_approved else "**Human approval required**")

with tab3:
    st.markdown("### Execute a bounded recovery batch")
    st.write("The executor uses deterministic synthetic outcomes so the demo is reproducible.")
    if st.button("Run recovery batch", type="primary"):
        results, metrics = run_batch(an)
        st.session_state.results = results
        st.session_state.metrics = metrics
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
    st.markdown("### Prototype measurement")
    if "results" not in st.session_state:
        st.info("Run a recovery batch to populate outcome metrics.")
    else:
        r = st.session_state.results
        m = st.session_state.metrics
        st.write("The figures below are benchmark results from the synthetic dataset, not production Razorpay statistics.")
        status = r.groupby("status", as_index=False).agg(count=("transaction_id", "count"), recovered=("recovered", "sum"))
        st.dataframe(status.style.format({"recovered":"₹{:,.0f}"}), use_container_width=True, hide_index=True)
        st.markdown("#### Safety / audit events")
        for _, x in r.head(12).iterrows():
            icon = "✓" if x.approved else "!"
            st.markdown(f"**{icon} {x.transaction_id}** · {x.action} · {x.status} · ₹{x.recovered:,.0f} recovered")

st.divider()
st.caption("RecoverAI is a hackathon prototype. Never place production credentials in source control; keep financial actions policy-gated and use test mode while demonstrating.")
