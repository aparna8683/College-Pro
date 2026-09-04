# RecoverAI Architecture

## Components

1. **Data layer** — normalizes transaction, customer and failure context.
2. **Revenue Risk Engine** — interpretable score combining failure recoverability, transaction value, loyalty and risk.
3. **Root-Cause Agent** — converts failure codes into merchant-readable explanations.
4. **Next-Best-Action Engine** — estimates recovery probability for retry, alternate method, recovery link, payment-method update and human escalation.
5. **Policy Gate** — enforces amount limits, retry stopping rules, risk thresholds and human approval.
6. **Execution layer** — deterministic simulation for the hackathon demo; optional Razorpay test-mode adapter for order creation.
7. **Outcome + audit layer** — records action, approval, result and recovered amount; outcomes can be fed back to improve action selection.

## Why the LLM is not the financial authority

LLMs are useful for explanations and workflow orchestration, but the prototype keeps financial authorization deterministic. The policy gate is the final authority for autonomous execution. This prevents a generated response from bypassing amount limits, risk controls or stopping rules.

## Extension to production

- Replace synthetic events with merchant webhook/event streams.
- Train a calibrated recovery-probability model on historical outcomes.
- Add idempotency keys and event-sourcing for every action.
- Integrate notification/payment-link providers through audited adapters.
- Add merchant-specific policies and approval workflows.
- Measure precision/recall for recovery eligibility and incremental recovered revenue against a control group.
