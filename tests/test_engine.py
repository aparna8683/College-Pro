import pandas as pd

from engine import analyze, policy_gate, run_batch


def sample():
    return pd.DataFrame([{
        "transaction_id": "txn_test",
        "customer_id": "cust_test",
        "amount": 4999.0,
        "payment_method": "card",
        "failure_reason": "bank_timeout",
        "failure_label": "Temporary bank/network timeout",
        "customer_orders": 7,
        "customer_ltv": 45000.0,
        "risk_score": .20,
        "retry_count": 0,
        "days_since_failure": 1,
    }])


def test_analyze_has_best_action():
    out = analyze(sample())
    assert out.iloc[0].best_action
    assert out.iloc[0].expected_recovery > 0


def test_policy_blocks_high_value_autonomous_action():
    out = analyze(sample())
    row = out.iloc[0].copy()
    row["amount"] = 50000
    ok, _ = policy_gate(row, row.actions[0])
    assert ok is False


def test_batch_is_reproducible():
    out = analyze(sample())
    first, _ = run_batch(out)
    second, _ = run_batch(out)
    assert first.iloc[0].recovered == second.iloc[0].recovered
