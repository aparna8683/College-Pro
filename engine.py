from __future__ import annotations

from dataclasses import dataclass
import hashlib
import pandas as pd


@dataclass
class Action:
    name: str
    score: float
    expected_recovery: float
    reason: str
    auto_allowed: bool


BASE_SUCCESS = {
    "bank_timeout": 0.80,
    "insufficient_balance": 0.36,
    "expired_card": 0.48,
    "upi_declined": 0.62,
    "auth_failed": 0.45,
    "customer_abandoned": 0.58,
    "subscription_failed": 0.66,
}

DEFAULT_AMOUNT_LIMIT = 10000.0
DEFAULT_RISK_LIMIT = 0.65
MAX_RETRIES = 2


def revenue_risk(row: pd.Series) -> float:
    amount_factor = min(float(row.amount) / 50000, 1.0)
    loyalty_factor = min(float(row.customer_orders) / 10, 1.0)
    base = BASE_SUCCESS[row.failure_reason]
    return round(max(0.0, min(1.0, 0.45 * base + 0.25 * loyalty_factor + 0.20 * amount_factor - 0.20 * row.risk_score)), 3)


def diagnose(row: pd.Series) -> list[str]:
    reasons = []
    if row.failure_reason == "bank_timeout":
        reasons.append("temporary bank/network issue")
    elif row.failure_reason == "insufficient_balance":
        reasons.append("insufficient balance is likely blocking payment")
    elif row.failure_reason == "expired_card":
        reasons.append("card credentials need updating")
    elif row.failure_reason == "upi_declined":
        reasons.append("UPI issuer declined the attempt")
    elif row.failure_reason == "auth_failed":
        reasons.append("authentication challenge was not completed")
    elif row.failure_reason == "customer_abandoned":
        reasons.append("customer left before completing checkout")
    elif row.failure_reason == "subscription_failed":
        reasons.append("recurring charge needs recovery")
    if row.customer_orders >= 5:
        reasons.append("repeat customer with strong payment history")
    if row.amount >= 20000:
        reasons.append("high-value transaction")
    return reasons


def candidate_actions(row: pd.Series) -> list[Action]:
    base = BASE_SUCCESS[row.failure_reason]
    actions = []

    def add(name, multiplier, why, allowed=True):
        success = max(0.05, min(0.97, base * multiplier + min(row.customer_orders, 10) * .012 - row.risk_score * .08))
        actions.append(Action(name, success, round(float(row.amount) * success, 2), why, allowed))

    if row.failure_reason in {"bank_timeout", "upi_declined", "auth_failed", "subscription_failed"} and row.retry_count < MAX_RETRIES:
        add("Smart retry", 1.00, "Transient or retryable failure with retry budget available")
    if row.payment_method != "upi":
        add("Offer UPI", 0.88, "Alternate payment rail can bypass the failed method")
    if row.failure_reason in {"expired_card", "auth_failed"}:
        add("Update payment method", 0.92, "Customer needs a corrected payment credential")
    if row.failure_reason in {"customer_abandoned", "insufficient_balance", "subscription_failed"}:
        add("Send recovery link", 0.90, "Customer can complete payment asynchronously")
    escalation = max(.15, min(.95, .50 + row.amount / 100000 - row.risk_score * .25))
    actions.append(Action("Human escalation", escalation, round(float(row.amount) * escalation, 2), "Use when value/risk justifies assisted recovery", False))
    return sorted(actions, key=lambda x: x.expected_recovery, reverse=True)


def policy_gate(
    row: pd.Series,
    action: Action,
    amount_limit: float = DEFAULT_AMOUNT_LIMIT,
    risk_limit: float = DEFAULT_RISK_LIMIT,
) -> tuple[bool, list[str]]:
    checks = []
    ok = True
    if float(row.amount) <= amount_limit:
        checks.append(f"amount ₹{float(row.amount):,.0f} ≤ limit ₹{amount_limit:,.0f}")
    else:
        checks.append(f"amount ₹{float(row.amount):,.0f} exceeds limit ₹{amount_limit:,.0f}")
        ok = False
    if int(row.retry_count) < MAX_RETRIES:
        checks.append(f"retry budget available ({int(row.retry_count)}/{MAX_RETRIES})")
    else:
        checks.append("retry stopping rule reached")
        if action.name == "Smart retry":
            ok = False
    if float(row.risk_score) < risk_limit:
        checks.append(f"risk {float(row.risk_score):.0%} < threshold {risk_limit:.0%}")
    else:
        checks.append(f"risk {float(row.risk_score):.0%} requires review")
        ok = False
    if action.name == "Human escalation":
        checks.append("human escalation cannot self-approve")
        ok = False
    if not action.auto_allowed:
        checks.append("action is not autonomous")
        ok = False
    return ok, checks


def analyze(
    df: pd.DataFrame,
    amount_limit: float = DEFAULT_AMOUNT_LIMIT,
    risk_limit: float = DEFAULT_RISK_LIMIT,
) -> pd.DataFrame:
    out = df.copy()
    out["recovery_score"] = out.apply(revenue_risk, axis=1)
    out["diagnosis"] = out.apply(lambda r: "; ".join(diagnose(r)), axis=1)
    out["actions"] = out.apply(candidate_actions, axis=1)
    out["best_action"] = out["actions"].apply(lambda xs: xs[0].name)
    out["expected_recovery"] = out["actions"].apply(lambda xs: xs[0].expected_recovery)
    out["recommendation_reason"] = out["actions"].apply(lambda xs: xs[0].reason)
    out["auto_approved"] = out.apply(lambda r: policy_gate(r, r.actions[0], amount_limit, risk_limit)[0], axis=1)
    out["policy_checks"] = out.apply(lambda r: policy_gate(r, r.actions[0], amount_limit, risk_limit)[1], axis=1)
    return out


def stable_success(transaction_id: str, probability: float) -> bool:
    digest = hashlib.sha256(transaction_id.encode()).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return value < probability


def run_batch(
    df: pd.DataFrame,
    amount_limit: float = DEFAULT_AMOUNT_LIMIT,
    risk_limit: float = DEFAULT_RISK_LIMIT,
) -> tuple[pd.DataFrame, dict]:
    results = []
    for _, row in df.iterrows():
        action = row.actions[0]
        approved, checks = policy_gate(row, action, amount_limit, risk_limit)
        recovered = 0.0
        status = "blocked"
        if approved:
            success = stable_success(row.transaction_id, action.expected_recovery / max(row.amount, 1))
            recovered = float(row.amount) if success else 0.0
            status = "recovered" if success else "attempted_no_recovery"
        results.append({
            "transaction_id": row.transaction_id,
            "amount": row.amount,
            "action": action.name,
            "approved": approved,
            "status": status,
            "recovered": recovered,
            "checks": " | ".join(checks),
            "diagnosis": row.diagnosis,
        })
    result = pd.DataFrame(results)
    metrics = {
        "revenue_at_risk": float(df.amount.sum()),
        "expected_recovery": float(df.expected_recovery.sum()),
        "recovered": float(result.recovered.sum()),
        "approved": int(result.approved.sum()),
        "blocked": int((~result.approved).sum()),
    }
    metrics["recovery_rate"] = metrics["recovered"] / metrics["revenue_at_risk"] if metrics["revenue_at_risk"] else 0
    return result, metrics
