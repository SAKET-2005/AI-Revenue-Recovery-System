"""
Payment provider abstraction.

PaymentProvider (abstract)
├── RazorpayPaymentProvider (Test Mode)
└── MockPaymentProvider (Simulation / Demo)
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import uuid
import random
from datetime import datetime


class PaymentProvider(ABC):
    """Abstract payment provider interface."""

    @abstractmethod
    async def retry_payment(self, transaction_id: str, amount: float, **kwargs) -> Dict:
        """Retry a failed payment. Returns result dict."""
        pass

    @abstractmethod
    async def create_payment_link(
        self, amount: float, currency: str = "INR",
        description: str = "", **kwargs
    ) -> Dict:
        """Create a payment link. Returns link details."""
        pass

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> Dict:
        """Get payment status."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class MockPaymentProvider(PaymentProvider):
    """
    Simulated payment provider for demo mode.

    Generates realistic mock responses with probabilistic outcomes.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._payment_links: Dict[str, Dict] = {}

    async def retry_payment(
        self, transaction_id: str, amount: float,
        recovery_probability: float = 0.5, **kwargs
    ) -> Dict:
        """Simulate a payment retry with probability-based outcome."""
        # Use recovery probability to determine success
        success = self._rng.random() < recovery_probability

        return {
            "payment_id": f"pay_{uuid.uuid4().hex[:16]}",
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": "INR",
            "status": "success" if success else "failed",
            "method": kwargs.get("payment_method", "upi"),
            "provider": "mock",
            "timestamp": datetime.now().isoformat(),
        }

    async def create_payment_link(
        self, amount: float, currency: str = "INR",
        description: str = "", **kwargs
    ) -> Dict:
        """Create a mock payment link."""
        link_id = f"plink_{uuid.uuid4().hex[:16]}"
        link_url = f"https://demo.reviveai.app/pay/{link_id}"
        short_url = f"https://rzp.io/i/{link_id[:8]}"

        link_data = {
            "link_id": link_id,
            "link_url": link_url,
            "short_url": short_url,
            "amount": amount,
            "currency": currency,
            "description": description,
            "status": "created",
            "provider": "mock",
            "created_at": datetime.now().isoformat(),
            "customer_name": kwargs.get("customer_name"),
            "customer_email": kwargs.get("customer_email"),
        }
        self._payment_links[link_id] = link_data
        return link_data

    async def complete_payment_link(self, link_id: str) -> Dict:
        """Simulate completing a payment link payment."""
        if link_id in self._payment_links:
            self._payment_links[link_id]["status"] = "paid"
            return {
                "link_id": link_id,
                "status": "paid",
                "payment_id": f"pay_{uuid.uuid4().hex[:16]}",
                "amount": self._payment_links[link_id]["amount"],
                "timestamp": datetime.now().isoformat(),
            }
        return {"link_id": link_id, "status": "not_found"}

    async def get_payment_status(self, payment_id: str) -> Dict:
        """Return mock payment status."""
        return {
            "payment_id": payment_id,
            "status": "success",
            "provider": "mock",
        }

    def get_provider_name(self) -> str:
        return "mock"


class RazorpayPaymentProvider(PaymentProvider):
    """
    Razorpay Test Mode payment provider.

    Uses official Razorpay Python SDK.
    Only activated when RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are configured.
    """

    def __init__(self, key_id: str, key_secret: str):
        import razorpay
        self.client = razorpay.Client(auth=(key_id, key_secret))
        print(f"[Razorpay] Initialized in Test Mode")

    async def retry_payment(
        self, transaction_id: str, amount: float,
        recovery_probability: float = 0.5, **kwargs
    ) -> Dict:
        """
        Razorpay doesn't support direct retry via API.
        For test mode, we simulate the retry but could create a new order.
        """
        # In Razorpay, retrying a payment means creating a new payment attempt.
        # For the hackathon, simulate the outcome.
        import asyncio
        success = random.random() < recovery_probability

        return {
            "payment_id": f"pay_{uuid.uuid4().hex[:16]}",
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": "INR",
            "status": "success" if success else "failed",
            "provider": "razorpay_test",
            "timestamp": datetime.now().isoformat(),
        }

    async def create_payment_link(
        self, amount: float, currency: str = "INR",
        description: str = "", **kwargs
    ) -> Dict:
        """Create a real Razorpay Payment Link in Test Mode."""
        import asyncio

        try:
            payload = {
                "amount": int(amount * 100),  # Razorpay uses paisa
                "currency": currency,
                "description": description or "Payment Recovery - ReviveAI",
                "customer": {},
            }
            if kwargs.get("customer_name"):
                payload["customer"]["name"] = kwargs["customer_name"]
            if kwargs.get("customer_email"):
                payload["customer"]["email"] = kwargs["customer_email"]
            if kwargs.get("customer_phone"):
                payload["customer"]["contact"] = kwargs["customer_phone"]

            # Remove empty customer dict
            if not payload["customer"]:
                del payload["customer"]

            result = await asyncio.to_thread(
                self.client.payment_link.create, payload
            )

            return {
                "link_id": result.get("id", ""),
                "link_url": result.get("long_url", ""),
                "short_url": result.get("short_url", ""),
                "amount": amount,
                "currency": currency,
                "status": result.get("status", "created"),
                "provider": "razorpay",
                "created_at": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"[Razorpay] Payment link creation failed: {e}")
            # Fallback to mock
            mock = MockPaymentProvider()
            return await mock.create_payment_link(amount, currency, description, **kwargs)

    async def get_payment_status(self, payment_id: str) -> Dict:
        """Fetch payment status from Razorpay."""
        import asyncio
        try:
            result = await asyncio.to_thread(
                self.client.payment.fetch, payment_id
            )
            return {
                "payment_id": payment_id,
                "status": result.get("status", "unknown"),
                "provider": "razorpay",
            }
        except Exception as e:
            return {"payment_id": payment_id, "status": "error", "error": str(e)}

    def get_provider_name(self) -> str:
        return "razorpay_test"


def get_payment_provider() -> PaymentProvider:
    """Factory — returns appropriate provider based on config."""
    from app.config import settings

    if settings.has_razorpay:
        try:
            return RazorpayPaymentProvider(
                settings.razorpay_key_id, settings.razorpay_key_secret
            )
        except Exception as e:
            print(f"[Provider] Razorpay init failed: {e} — falling back to Mock")

    return MockPaymentProvider()
