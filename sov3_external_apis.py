#!/usr/bin/env python3
"""
SOV3 External API Integrations
Features:
- Stripe payment processing
- Clerk authentication
- Vapi.ai voice calls
- Webhook management

Run: python sov3_external_apis.py demo

Note: Requires API keys to be set in environment:
- STRIPE_SECRET_KEY
- CLERK_SECRET_KEY
- VAPI_API_KEY
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PaymentStatus(Enum):
    """Payment status"""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class WebhookEvent(Enum):
    """Webhook event types"""

    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    USER_SIGNED_UP = "user.signed_up"
    USER_LOGGED_IN = "user.logged_in"
    AGENT_COMPLETED = "agent.completed"
    TASK_TRIGGERED = "task.triggered"


@dataclass
class Payment:
    """Payment record"""

    payment_id: str
    amount: float
    currency: str
    status: PaymentStatus
    customer_email: str
    created_at: str
    description: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class Webhook:
    """Webhook configuration"""

    webhook_id: str
    url: str
    events: List[WebhookEvent]
    secret: str
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_triggered: Optional[str] = None


class StripeIntegration:
    """Stripe payment integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        self.base_url = "https://api.stripe.com/v1"
        self._available = bool(self.api_key)

    def is_available(self) -> bool:
        return self._available

    def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        customer_email: str = None,
        description: str = "",
    ) -> Optional[Payment]:
        """Create a payment intent"""
        if not self._available:
            return None

        # In production would call Stripe API
        # Simulated for demo
        payment_id = f"pi_{int(time.time() * 1000)}"

        return Payment(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
            customer_email=customer_email or "unknown",
            created_at=datetime.now().isoformat(),
            description=description,
        )

    def confirm_payment(self, payment_id: str) -> bool:
        """Confirm a payment (simulated)"""
        return True

    def refund_payment(self, payment_id: str, amount: float = None) -> bool:
        """Refund a payment"""
        return True

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment details"""
        return Payment(
            payment_id=payment_id,
            amount=99.00,
            currency="usd",
            status=PaymentStatus.SUCCEEDED,
            customer_email="user@example.com",
            created_at=datetime.now().isoformat(),
        )


class ClerkIntegration:
    """Clerk authentication integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CLERK_SECRET_KEY")
        self.base_url = "https://api.clerk.com/v1"
        self._available = bool(self.api_key)
        self.users: Dict[str, Dict] = {}  # Simulated user store

    def is_available(self) -> bool:
        return self._available

    def create_user(self, email: str, name: str = None) -> Optional[str]:
        """Create a new user"""
        user_id = f"user_{int(time.time() * 1000)}"
        self.users[user_id] = {
            "email": email,
            "name": name,
            "created_at": datetime.now().isoformat(),
        }
        return user_id

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        return self.users.get(user_id)

    def verify_session(self, session_token: str) -> Optional[str]:
        """Verify session and return user ID"""
        # Simulated - would validate with Clerk
        for user_id, user in self.users.items():
            return user_id
        return None


class VapiIntegration:
    """Vapi.ai voice call integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("VAPI_API_KEY")
        self.base_url = "https://api.vapi.ai"
        self._available = bool(self.api_key)
        self.calls: List[Dict] = []

    def is_available(self) -> bool:
        return self._available

    def initiate_call(
        self, to_number: str, from_number: str = None, workflow: str = "sales"
    ) -> Optional[str]:
        """Start a voice call"""
        if not self._available:
            return None

        call_id = f"call_{int(time.time() * 1000)}"

        self.calls.append(
            {
                "call_id": call_id,
                "to": to_number,
                "workflow": workflow,
                "status": "initiated",
                "started_at": datetime.now().isoformat(),
            }
        )

        return call_id

    def end_call(self, call_id: str) -> bool:
        """End a call"""
        for call in self.calls:
            if call["call_id"] == call_id:
                call["status"] = "ended"
                call["ended_at"] = datetime.now().isoformat()
                return True
        return False

    def get_call_status(self, call_id: str) -> Optional[str]:
        """Get call status"""
        for call in self.calls:
            if call["call_id"] == call_id:
                return call.get("status")
        return None


class WebhookManager:
    """Webhook management system"""

    def __init__(self):
        self.webhooks: Dict[str, Webhook] = {}
        self.event_history: List[Dict] = []

    def register_webhook(self, url: str, events: List[str], secret: str = None) -> str:
        """Register a new webhook"""
        webhook_id = f"wh_{len(self.webhooks) + 1}"

        # Convert string events to WebhookEvent enums
        webhook_events = []
        for event_str in events:
            try:
                webhook_events.append(WebhookEvent(event_str))
            except ValueError:
                pass

        webhook = Webhook(
            webhook_id=webhook_id,
            url=url,
            events=webhook_events,
            secret=secret or f"secret_{webhook_id}",
        )

        self.webhooks[webhook_id] = webhook
        return webhook_id

    def trigger_event(self, event_type: str, payload: Dict):
        """Trigger an event for all subscribed webhooks"""
        event_entry = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        }

        self.event_history.append(event_entry)

        # Trigger matching webhooks
        triggered = []
        for webhook in self.webhooks.values():
            if not webhook.active:
                continue

            # Check if webhook subscribes to this event type
            for subscribed_event in webhook.events:
                if subscribed_event.value == event_type:
                    triggered.append(webhook.url)
                    webhook.last_triggered = datetime.now().isoformat()
                    break

        return triggered

    def list_webhooks(self) -> List[Dict]:
        """List all registered webhooks"""
        return [
            {
                "id": w.webhook_id,
                "url": w.url,
                "events": [e.value for e in w.events],
                "active": w.active,
                "last_triggered": w.last_triggered,
            }
            for w in self.webhooks.values()
        ]

    def toggle_webhook(self, webhook_id: str, active: bool) -> bool:
        """Enable or disable a webhook"""
        if webhook_id in self.webhooks:
            self.webhooks[webhook_id].active = active
            return True
        return False


class ExternalAPIManager:
    """
    Unified external API manager
    Combines all external integrations
    """

    def __init__(self):
        self.stripe = StripeIntegration()
        self.clerk = ClerkIntegration()
        self.vapi = VapiIntegration()
        self.webhooks = WebhookManager()

    def get_status(self) -> Dict:
        """Get status of all integrations"""
        return {
            "stripe": {
                "available": self.stripe.is_available(),
                "configured": bool(self.stripe.api_key),
            },
            "clerk": {
                "available": self.clerk.is_available(),
                "configured": bool(self.clerk.api_key),
                "users": len(self.clerk.users),
            },
            "vapi": {
                "available": self.vapi.is_available(),
                "configured": bool(self.vapi.api_key),
                "calls": len(self.vapi.calls),
            },
            "webhooks": {
                "registered": len(self.webhooks.webhooks),
                "active": sum(1 for w in self.webhooks.webhooks.values() if w.active),
            },
        }

    def create_checkout_session(
        self, amount: float, email: str, description: str
    ) -> Optional[str]:
        """Create Stripe checkout session"""
        payment = self.stripe.create_payment_intent(
            amount=amount, customer_email=email, description=description
        )

        if payment:
            # Trigger webhook
            self.webhooks.trigger_event(
                "payment.success", {"payment_id": payment.payment_id, "amount": amount}
            )

        return payment.payment_id if payment else None

    def handle_user_signup(self, email: str, name: str = None) -> Optional[str]:
        """Handle new user signup"""
        user_id = self.clerk.create_user(email, name)

        if user_id:
            self.webhooks.trigger_event(
                "user.signed_up", {"user_id": user_id, "email": email}
            )

        return user_id

    def start_sales_call(self, phone_number: str) -> Optional[str]:
        """Start Vapi sales call"""
        call_id = self.vapi.initiate_call(phone_number, workflow="sales")

        if call_id:
            self.webhooks.trigger_event(
                "task.triggered", {"task_type": "sales_call", "call_id": call_id}
            )

        return call_id


def demo():
    """Demo external APIs"""
    print("=" * 50)
    print("SOV3 External API Integrations Demo")
    print("=" * 50)

    api = ExternalAPIManager()

    # Show status
    print("\n1. Integration status:")
    status = api.get_status()
    for service, info in status.items():
        available = "✅" if info.get("available", False) else "⚠️ "
        print(f"   {available} {service}: {info}")

    # Create payment
    print("\n2. Creating payment...")
    session_id = api.create_checkout_session(
        99.00, "customer@example.com", "MEOK Pro Plan"
    )
    print(f"   Session ID: {session_id}")

    # User signup
    print("\n3. Handling signup...")
    user_id = api.handle_user_signup("newuser@example.com", "New User")
    print(f"   User ID: {user_id}")

    # Start call (won't work without API key but shows integration)
    print("\n4. Starting sales call...")
    call_id = api.start_sales_call("+1234567890")
    print(f"   Call ID: {call_id}")

    # Webhooks
    print("\n5. Registering webhook...")
    wh_id = api.webhooks.register_webhook(
        url="https://example.com/webhook",
        events=["payment.success", "user.signed_up"],
        secret="my_secret",
    )
    print(f"   Webhook ID: {wh_id}")

    # List webhooks
    print("\n6. Webhooks:")
    for wh in api.webhooks.list_webhooks():
        print(f"   - {wh['id']}: {wh['url']} (active: {wh['active']})")

    # Trigger event
    print("\n7. Triggering event...")
    triggered = api.webhooks.trigger_event(
        "payment.success", {"amount": 99.00, "customer": "test@example.com"}
    )
    print(f"   Triggered webhooks: {triggered}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("Usage: python sov3_external_apis.py demo")
        print("\nEnvironment variables to set:")
        print("  STRIPE_SECRET_KEY")
        print("  CLERK_SECRET_KEY")
        print("  VAPI_API_KEY")
