from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class RazorpayTestAdapter:
    """Small optional adapter for Razorpay test-mode order creation.

    The hackathon demo defaults to simulation. This adapter is deliberately
    isolated so credentials never appear in the decision engine or frontend.
    """

    def __init__(self) -> None:
        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        self.base_url = "https://api.razorpay.com/v1"

    @property
    def configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def create_test_order(self, amount_inr: float, receipt: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "Razorpay test credentials are not configured."}
        response = requests.post(
            f"{self.base_url}/orders",
            auth=(self.key_id, self.key_secret),
            json={"amount": int(round(amount_inr * 100)), "currency": "INR", "receipt": receipt},
            timeout=15,
        )
        response.raise_for_status()
        return {"ok": True, "order": response.json()}
