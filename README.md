# RecoverAI — Autonomous Revenue Recovery Agent

**Razorpay AI Buildathon 2026 · Track 3: AI Revenue Recovery**

RecoverAI is a merchant-side AI decision engine that finds revenue leakage, diagnoses why money is at risk, chooses the next-best recovery action, applies safety policies, simulates/executes a bounded recovery workflow, and records the outcome in an audit trail.

> Built as a hackathon prototype using synthetic transaction data. Razorpay integration is isolated behind an adapter so the demo works without exposing credentials or making live-money decisions.

## Why this fits Track 3

The official track asks builders to detect revenue at risk, determine the right intervention, and execute a bounded recovery workflow with measured money recovered, compliant escalation, stopping rules and an audit trail. RecoverAI implements that complete loop rather than stopping at prediction.

## Core flow

```text
Merchant transactions
        ↓
Revenue leakage detector
        ↓
Root-cause diagnosis
        ↓
Next-best-action engine
        ↓
Policy / safety gate
        ↓
Bounded recovery executor
        ↓
Outcome + recovered revenue
        ↓
Audit trail + learning feedback
```

## What is different

- **Revenue-at-risk view:** failed payments, checkout abandonment and subscription failures are unified into one leakage map.
- **Next-best action:** retry, alternate method, payment link, reminder, or human escalation are ranked using transaction/customer context.
- **Policy gate:** action amount, retry count, risk score and escalation rules are checked before execution.
- **Outcome simulation:** every action has a probabilistic success model, allowing the demo to show measurable recovered revenue across a batch.
- **Explainability:** every recommendation includes reason codes and expected recovery value.
- **Auditability:** decisions, policy checks and outcomes are persisted in an append-only JSONL log.
- **Razorpay adapter:** optional test-mode order creation can be enabled with environment variables; default mode is safe simulation.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

## Optional Razorpay test mode

Create a Razorpay test-mode account and put credentials in `.env`:

```env
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=xxx
```

Never commit `.env`. The prototype uses the adapter only for test-mode order creation; recovery decisions remain policy-gated.

## Demo scenario

The dashboard ships with deterministic synthetic data containing:

- high-value repeat customers with temporary bank failures
- abandoned checkouts
- failed subscriptions
- low-value failures where escalation would cost more than the recovery
- repeated failures that hit stopping rules
- risky cases that require human approval

Click **Run recovery batch** to process the queue and compare revenue at risk with simulated revenue recovered.

## Project structure

```text
recoverai/
├── app.py                 # Streamlit merchant dashboard
├── engine.py              # detection, diagnosis, action ranking and policy gate
├── data.py                # synthetic merchant dataset
├── razorpay_adapter.py    # optional Razorpay test-mode adapter
├── audit.py               # append-only decision/outcome audit log
├── requirements.txt
├── Dockerfile
├── tests/
│   └── test_engine.py
└── docs/
    └── architecture.md
```

## Important demo claims

Metrics shown by the dashboard are generated from a synthetic benchmark designed for the prototype. They are not Razorpay production statistics. In the pitch, present them as **measured prototype results** and explain the synthetic-data setup.

## License

MIT
