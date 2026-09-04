from __future__ import annotations

import numpy as np
import pandas as pd


FAILURE_PROFILES = {
    "bank_timeout": (0.80, "Temporary bank/network timeout"),
    "insufficient_balance": (0.36, "Insufficient balance"),
    "expired_card": (0.48, "Card has expired"),
    "upi_declined": (0.62, "UPI payment declined"),
    "auth_failed": (0.45, "Authentication failed"),
    "customer_abandoned": (0.58, "Checkout abandoned before payment"),
    "subscription_failed": (0.66, "Recurring subscription payment failed"),
}


def make_demo_transactions(seed: int = 42, n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    methods = rng.choice(["upi", "card", "netbanking", "wallet"], n, p=[.48, .32, .15, .05])
    failures = rng.choice(list(FAILURE_PROFILES), n, p=[.18, .14, .13, .18, .10, .15, .12])
    amounts = np.round(rng.lognormal(mean=7.1, sigma=.8, size=n), -1)
    amounts = np.clip(amounts, 299, 75000)
    repeat = rng.integers(0, 12, n)
    ltv = np.round(amounts * (repeat + 1) * rng.uniform(1.0, 2.5, n), 0)
    risk = np.round(rng.uniform(.03, .72, n), 2)
    retry_count = rng.integers(0, 3, n)

    rows = []
    for i in range(n):
        failure = failures[i]
        rows.append(
            {
                "transaction_id": f"txn_{100001 + i}",
                "customer_id": f"cust_{1000 + rng.integers(1, 180)}",
                "amount": float(amounts[i]),
                "payment_method": methods[i],
                "failure_reason": failure,
                "failure_label": FAILURE_PROFILES[failure][1],
                "customer_orders": int(repeat[i]),
                "customer_ltv": float(ltv[i]),
                "risk_score": float(risk[i]),
                "retry_count": int(retry_count[i]),
                "days_since_failure": int(rng.integers(0, 8)),
            }
        )
    return pd.DataFrame(rows)
