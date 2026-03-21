"""Payment processing service for e-commerce transactions.

Handles charge creation, refund processing, and webhook verification
for a Stripe-like payment gateway.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

WEBHOOK_TOLERANCE_SECONDS = 300  # 5 minutes
MAX_REFUND_WINDOW_DAYS = 30
CURRENCY_DECIMALS = {"USD": 2, "EUR": 2, "JPY": 0, "BTC": 8}


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


@dataclass
class PaymentIntent:
    """Represents a payment intent through its lifecycle."""

    intent_id: str
    amount: Decimal
    currency: str
    customer_id: str
    status: PaymentStatus = PaymentStatus.PENDING
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    captured_at: float | None = None
    refunded_amount: Decimal = Decimal("0")


class PaymentProcessor:
    """Processes payments against an in-memory ledger."""

    def __init__(self, webhook_secret: str) -> None:
        self._ledger: dict[str, PaymentIntent] = {}
        self._customer_balances: dict[str, Decimal] = {}
        self._webhook_secret = webhook_secret

    def create_intent(
        self,
        intent_id: str,
        amount: Decimal,
        currency: str,
        customer_id: str,
        metadata: dict[str, str] | None = None,
    ) -> PaymentIntent:
        """Create a new payment intent."""
        decimals = CURRENCY_DECIMALS.get(currency.upper())
        if decimals is None:
            raise ValueError(f"Unsupported currency: {currency}")

        # Quantize to correct decimal places
        quantized = amount.quantize(Decimal(10) ** -decimals)

        intent = PaymentIntent(
            intent_id=intent_id,
            amount=quantized,
            currency=currency.upper(),
            customer_id=customer_id,
            metadata=metadata or {},
        )
        self._ledger[intent_id] = intent
        return intent

    def capture(self, intent_id: str) -> PaymentIntent:
        """Capture an authorized payment."""
        intent = self._get_intent(intent_id)

        if intent.status != PaymentStatus.AUTHORIZED:
            raise ValueError(
                f"Cannot capture intent in status {intent.status}"
            )

        balance = self._customer_balances.get(intent.customer_id, Decimal("0"))
        if balance < intent.amount:
            intent.status = PaymentStatus.FAILED
            raise ValueError("Insufficient balance")

        self._customer_balances[intent.customer_id] = balance - intent.amount
        intent.status = PaymentStatus.CAPTURED
        intent.captured_at = time.time()
        return intent

    def refund(
        self, intent_id: str, amount: Decimal | None = None
    ) -> PaymentIntent:
        """Process a full or partial refund."""
        intent = self._get_intent(intent_id)

        if intent.status != PaymentStatus.CAPTURED:
            raise ValueError("Can only refund captured payments")

        # Check refund window
        days_since_capture = (time.time() - intent.captured_at) / 86400
        if days_since_capture > MAX_REFUND_WINDOW_DAYS:
            raise ValueError("Refund window has expired")

        refund_amount = amount or intent.amount
        remaining = intent.amount - intent.refunded_amount

        if refund_amount > remaining:
            raise ValueError(
                f"Refund amount {refund_amount} exceeds remaining {remaining}"
            )

        # Credit back to customer
        balance = self._customer_balances.get(intent.customer_id, Decimal("0"))
        self._customer_balances[intent.customer_id] = balance + refund_amount
        intent.refunded_amount += refund_amount

        if intent.refunded_amount == intent.amount:
            intent.status = PaymentStatus.REFUNDED

        logger.info(
            f"Refund processed: intent={intent_id} amount={refund_amount} "
            f"card=*{intent.metadata.get('card_last4', '****')}"
        )
        return intent

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """Verify and parse an incoming webhook payload.

        Validates the HMAC signature and checks timestamp freshness.
        """
        parts = signature.split(",")
        sig_dict = {}
        for part in parts:
            key, _, value = part.strip().partition("=")
            sig_dict[key] = value

        timestamp = sig_dict.get("t", "")
        provided_sig = sig_dict.get("v1", "")

        # Verify timestamp freshness
        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            raise ValueError("Invalid webhook timestamp")

        if abs(time.time() - ts) > WEBHOOK_TOLERANCE_SECONDS:
            raise ValueError("Webhook timestamp outside tolerance window")

        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            self._webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, provided_sig):
            raise ValueError("Invalid webhook signature")

        import json
        return json.loads(payload)

    def get_customer_balance(self, customer_id: str) -> Decimal:
        """Get the current balance for a customer."""
        return self._customer_balances.get(customer_id, Decimal("0"))

    def set_customer_balance(
        self, customer_id: str, amount: Decimal
    ) -> None:
        """Set the balance for a customer (e.g., after deposit)."""
        self._customer_balances[customer_id] = amount

    def _get_intent(self, intent_id: str) -> PaymentIntent:
        """Retrieve a payment intent or raise."""
        intent = self._ledger.get(intent_id)
        if intent is None:
            raise KeyError(f"Payment intent not found: {intent_id}")
        return intent
