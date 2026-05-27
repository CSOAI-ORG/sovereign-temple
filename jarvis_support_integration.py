#!/usr/bin/env python3
"""
JARVIS Customer Support Integration
Features:
- Intercom integration for AI-powered support
- Fin AI agent (LLM-powered support)
- Ticket classification and routing
- Automated responses with human handoff

Run: python jarvis_support_integration.py demo

Note: Requires Intercom API key (set INTERCOM_ACCESS_TOKEN env var)
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import base64


class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(Enum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class SupportTicket:
    """Support ticket representation"""

    ticket_id: str
    subject: str
    description: str
    customer_email: str
    customer_name: str
    priority: TicketPriority
    status: TicketStatus
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    assigned_agent: Optional[str] = None


@dataclass
class SupportResponse:
    """Response to a support ticket"""

    response_id: str
    ticket_id: str
    message: str
    is_auto_response: bool
    confidence: float
    created_at: str
    suggested_actions: List[str] = field(default_factory=list)


class IntercomClient:
    """Intercom API client wrapper"""

    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv("INTERCOM_ACCESS_TOKEN")
        self.base_url = "https://api.intercom.io"
        self.headers = (
            {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if self.access_token
            else {}
        )
        self._available = bool(self.access_token)

    def is_available(self) -> bool:
        return self._available

    def create_conversation(self, user_id: str, message: str) -> Dict:
        """Create a new conversation"""
        # Placeholder - would use actual Intercom API
        return {"id": f"conv_{int(time.time())}", "state": "open"}

    def reply_to_conversation(
        self, conversation_id: str, message: str, admin_id: str = None
    ) -> Dict:
        """Reply to an existing conversation"""
        return {"id": f"reply_{int(time.time())}", "conversation_id": conversation_id}

    def get_conversation(self, conversation_id: str) -> Dict:
        """Get conversation details"""
        return {"id": conversation_id, "state": "open"}

    def close_conversation(self, conversation_id: str) -> Dict:
        """Close a conversation"""
        return {"id": conversation_id, "state": "closed"}


class TicketClassifier:
    """Classifies support tickets using LLM or rules"""

    def __init__(self, llm_client: Callable = None):
        self.llm_client = llm_client

    def classify(self, subject: str, description: str) -> Dict:
        """Classify ticket priority and type"""

        subject_lower = subject.lower()
        desc_lower = description.lower()

        # Rule-based classification
        priority = TicketPriority.MEDIUM
        tags = []

        # Priority detection
        urgent_keywords = [
            "urgent",
            "asap",
            "emergency",
            "critical",
            "down",
            "broken",
            "can't access",
        ]
        high_keywords = ["important", "bug", "error", "issue", "problem", "not working"]

        if any(kw in subject_lower or kw in desc_lower for kw in urgent_keywords):
            priority = TicketPriority.URGENT
            tags.append("urgent")
        elif any(kw in subject_lower or kw in desc_lower for kw in high_keywords):
            priority = TicketPriority.HIGH
            tags.append("high-priority")

        # Type detection
        if any(
            kw in desc_lower
            for kw in ["billing", "invoice", "payment", "charge", "refund"]
        ):
            tags.append("billing")
        if any(kw in desc_lower for kw in ["bug", "error", "crash", "broken"]):
            tags.append("bug")
        if any(
            kw in desc_lower
            for kw in ["how to", "help", "explain", "what is", "question"]
        ):
            tags.append("how-to")
        if any(
            kw in desc_lower
            for kw in ["feature", "request", "suggestion", "would be nice"]
        ):
            tags.append("feature-request")
        if any(kw in desc_lower for kw in ["account", "login", "password", "access"]):
            tags.append("account")

        return {
            "priority": priority,
            "tags": tags,
            "category": tags[0] if tags else "general",
        }


class AutoResponseGenerator:
    """Generates automated responses to support tickets"""

    def __init__(
        self, llm_client: Callable = None, ollama_base: str = "http://localhost:11434"
    ):
        self.llm_client = llm_client
        self.ollama_base = ollama_base
        self.response_templates = {
            "greeting": "Hi {name}, thanks for reaching out! I'm here to help.",
            "billing": "I understand you have a billing question. Let me look into that for you.",
            "bug": "I'm sorry to hear you're experiencing issues. Can you tell me more about what happened?",
            "how-to": "Great question! Here's some help with that:",
            "feature-request": "Thank you for the suggestion! I've logged this with our team.",
            "account": "I can help you with your account. Let me look into that.",
            "closing": "Is there anything else I can help you with?",
        }

    async def generate_response(
        self, ticket: SupportTicket, conversation_history: List[Dict] = None
    ) -> SupportResponse:
        """Generate an appropriate response"""

        import httpx

        # Use LLM if available
        if self.llm_client:
            try:
                response_text = await self._generate_llm_response(
                    ticket, conversation_history
                )
                return SupportResponse(
                    response_id=f"resp_{int(time.time())}",
                    ticket_id=ticket.ticket_id,
                    message=response_text,
                    is_auto_response=True,
                    confidence=0.85,
                    created_at=datetime.now().isoformat(),
                    suggested_actions=self._get_suggested_actions(ticket),
                )
            except Exception as e:
                print(f"LLM response failed: {e}")

        # Fall back to templates
        return self._generate_template_response(ticket)

    async def _generate_llm_response(
        self, ticket: SupportTicket, history: List[Dict]
    ) -> str:
        """Generate response using LLM"""
        import httpx

        context = f"Customer: {ticket.customer_name}\nSubject: {ticket.subject}\nDescription: {ticket.description}"

        prompt = f"""You are a helpful customer support agent. Generate a friendly, helpful response.

Customer info: {ticket.customer_name}
Ticket: {ticket.subject}
Description: {ticket.description}

Write a helpful response (2-3 sentences):"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.ollama_base}/api/chat",
                    json={
                        "model": "qwen2.5:14b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
                if response.status_code == 200:
                    return response.json().get("message", {}).get("content", "")
        except:
            pass

        return ""

    def _generate_template_response(self, ticket: SupportTicket) -> SupportResponse:
        """Generate response using templates"""

        # Find matching template
        template_key = "greeting"
        for tag in ticket.tags:
            if tag in self.response_templates:
                template_key = tag
                break

        template = self.response_templates[template_key]

        # Build response
        parts = [
            template.format(name=ticket.customer_name),
        ]

        # Add specific help based on tags
        if "billing" in ticket.tags:
            parts.append(self.response_templates["billing"])
        elif "bug" in ticket.tags:
            parts.append(self.response_templates["bug"])
        elif "how-to" in ticket.tags:
            parts.append(self.response_templates["how-to"])

        parts.append(self.response_templates["closing"])

        return SupportResponse(
            response_id=f"resp_{int(time.time())}",
            ticket_id=ticket.ticket_id,
            message=" ".join(parts),
            is_auto_response=True,
            confidence=0.6,
            created_at=datetime.now().isoformat(),
            suggested_actions=self._get_suggested_actions(ticket),
        )

    def _get_suggested_actions(self, ticket: SupportTicket) -> List[str]:
        """Get suggested actions based on ticket"""
        actions = []

        if ticket.priority == TicketPriority.URGENT:
            actions.append("Escalate to human agent immediately")
            actions.append("Send to engineering emergency channel")
        elif ticket.priority == TicketPriority.HIGH:
            actions.append("Priority queue")

        if "bug" in ticket.tags:
            actions.append("Create bug report")
            actions.append("Check error logs")

        if "billing" in ticket.tags:
            actions.append("Review billing history")
            actions.append("Check payment status")

        return actions


class SupportIntegration:
    """
    Main support integration combining Intercom, classification, and auto-response
    """

    def __init__(self, ollama_base: str = "http://localhost:11434"):
        self.intercom = IntercomClient()
        self.classifier = TicketClassifier()
        self.response_generator = AutoResponseGenerator(ollama_base=ollama_base)

        # Local ticket storage (would be DB in production)
        self.tickets: Dict[str, SupportTicket] = {}
        self.conversations: Dict[str, List[SupportResponse]] = {}

    async def create_ticket(
        self, subject: str, description: str, customer_email: str, customer_name: str
    ) -> SupportTicket:
        """Create a new support ticket"""

        # Classify ticket
        classification = self.classifier.classify(subject, description)

        # Create ticket
        ticket = SupportTicket(
            ticket_id=f"ticket_{int(time.time())}",
            subject=subject,
            description=description,
            customer_email=customer_email,
            customer_name=customer_name,
            priority=classification["priority"],
            status=TicketStatus.OPEN,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=classification["tags"],
        )

        self.tickets[ticket.ticket_id] = ticket
        self.conversations[ticket.ticket_id] = []

        # Auto-respond if enabled
        if self.intercom.is_available():
            await self._auto_respond(ticket)

        return ticket

    async def _auto_respond(self, ticket: SupportTicket):
        """Generate and send auto-response"""
        response = await self.response_generator.generate_response(ticket)

        # Store response
        self.conversations[ticket.ticket_id].append(response)

        # Send via Intercom if available
        if self.intercom.is_available():
            self.intercom.create_conversation(ticket.customer_email, response.message)

    async def respond_to_ticket(
        self, ticket_id: str, message: str, is_auto: bool = False
    ) -> Optional[SupportResponse]:
        """Add a response to a ticket"""

        if ticket_id not in self.tickets:
            return None

        ticket = self.tickets[ticket_id]

        response = SupportResponse(
            response_id=f"resp_{int(time.time())}",
            ticket_id=ticket_id,
            message=message,
            is_auto_response=is_auto,
            confidence=1.0 if not is_auto else 0.9,
            created_at=datetime.now().isoformat(),
        )

        self.conversations[ticket_id].append(response)

        # Update ticket
        ticket.updated_at = datetime.now().isoformat()

        return response

    def get_ticket(self, ticket_id: str) -> Optional[SupportTicket]:
        """Get ticket by ID"""
        return self.tickets.get(ticket_id)

    def list_tickets(
        self,
        status: TicketStatus = None,
        priority: TicketPriority = None,
        limit: int = 50,
    ) -> List[SupportTicket]:
        """List tickets with optional filters"""

        tickets = list(self.tickets.values())

        if status:
            tickets = [t for t in tickets if t.status == status]

        if priority:
            tickets = [t for t in tickets if t.priority == priority]

        return sorted(tickets, key=lambda t: t.created_at, reverse=True)[:limit]

    def get_ticket_stats(self) -> Dict:
        """Get support statistics"""
        tickets = list(self.tickets.values())

        return {
            "total": len(tickets),
            "open": sum(1 for t in tickets if t.status == TicketStatus.OPEN),
            "pending": sum(1 for t in tickets if t.status == TicketStatus.PENDING),
            "resolved": sum(1 for t in tickets if t.status == TicketStatus.RESOLVED),
            "closed": sum(1 for t in tickets if t.status == TicketStatus.CLOSED),
            "urgent": sum(1 for t in tickets if t.priority == TicketPriority.URGENT),
            "high": sum(1 for t in tickets if t.priority == TicketPriority.HIGH),
            "medium": sum(1 for t in tickets if t.priority == TicketPriority.MEDIUM),
            "low": sum(1 for t in tickets if t.priority == TicketPriority.LOW),
        }

    def escalate_ticket(self, ticket_id: str, reason: str) -> bool:
        """Escalate a ticket to human agent"""

        if ticket_id not in self.tickets:
            return False

        ticket = self.tickets[ticket_id]
        ticket.priority = TicketPriority.HIGH
        ticket.tags.append("escalated")
        ticket.tags.append(f"escalation_reason: {reason}")
        ticket.updated_at = datetime.now().isoformat()

        return True


async def demo():
    """Demo the support integration"""
    print("=" * 50)
    print("Customer Support Integration Demo")
    print("=" * 50)

    support = SupportIntegration()

    # Create tickets
    print("\n1. Creating tickets...")

    ticket1 = await support.create_ticket(
        subject="Can't access my account",
        description="I keep getting an error when I try to log in. It says 'invalid credentials' but I'm sure my password is correct.",
        customer_email="john@example.com",
        customer_name="John Doe",
    )
    print(
        f"   Created: {ticket1.ticket_id} (priority: {ticket1.priority.value}, tags: {ticket1.tags})"
    )

    ticket2 = await support.create_ticket(
        subject="Billing question",
        description="I was charged twice for my subscription this month. Can you help me get a refund?",
        customer_email="jane@example.com",
        customer_name="Jane Smith",
    )
    print(
        f"   Created: {ticket2.ticket_id} (priority: {ticket2.priority.value}, tags: {ticket2.tags})"
    )

    ticket3 = await support.create_ticket(
        subject="URGENT: System down",
        description="Our entire team can't access the platform. This is critical and affecting our business!",
        customer_email="bob@company.com",
        customer_name="Bob Wilson",
    )
    print(
        f"   Created: {ticket3.ticket_id} (priority: {ticket3.priority.value}, tags: {ticket3.tags})"
    )

    # Show auto-responses
    print("\n2. Auto-responses generated:")
    for ticket_id, responses in support.conversations.items():
        if responses:
            print(f"   {ticket_id}: {responses[0].message[:60]}...")

    # List tickets
    print("\n3. All tickets:")
    for ticket in support.list_tickets():
        print(
            f"   [{ticket.priority.value}] {ticket.subject[:40]} - {ticket.status.value}"
        )

    # Stats
    print("\n4. Statistics:")
    stats = support.get_ticket_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Manual response
    print("\n5. Adding manual response...")
    await support.respond_to_ticket(
        ticket1.ticket_id,
        "I've reset your password. Please check your email for the reset link.",
        is_auto=False,
    )
    print("   Response added")

    # Escalate
    print("\n6. Escalating urgent ticket...")
    support.escalate_ticket(ticket3.ticket_id, "critical_business_impact")
    print("   Escalated")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        import asyncio

        asyncio.run(demo())
    else:
        print("Usage: python jarvis_support_integration.py demo")
        print("\nEnvironment variables:")
        print("  INTERCOM_ACCESS_TOKEN - Your Intercom API token")
