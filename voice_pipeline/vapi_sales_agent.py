#!/usr/bin/env python3
"""
MEOK AI LABS — Vapi.ai Sales Calling Integration
Autonomous sales agent that calls leads, pitches MEOK services, handles objections.

Setup:
1. Sign up at vapi.ai
2. Get API key from dashboard
3. Set VAPI_API_KEY env var
4. Configure voice ID and assistant ID

Run: python3 voice_pipeline/vapi_sales_agent.py
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
)
log = logging.getLogger("vapi-sales")

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_BASE_URL = "https://api.vapi.ai"


class VapiSalesAgent:
    """AI sales calling agent using Vapi.ai"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or VAPI_API_KEY
        if not self.api_key:
            raise ValueError("VAPI_API_KEY not set")
        self.base_url = VAPI_BASE_URL

    def create_outbound_call(
        self,
        phone_number: str,
        script: str,
        voice_id: str = "sarah",
        first_message: str = None,
    ) -> Dict[str, Any]:
        """Start an outbound sales call"""

        # MEOK sales script
        default_first_message = (
            "Hi, this is an AI assistant calling from MEOK AI Labs. "
            "We're reaching out because we help businesses automate their operations "
            "with sovereign AI. Do you have 2 minutes to hear how we can help?"
        )

        payload = {
            "name": "MEOK Sales Call",
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "system_prompt": f"""You are a friendly, professional sales representative for MEOK AI Labs.
You help businesses automate operations with sovereign AI that:
- Runs locally (data never leaves their servers)
- Has memory and remembers conversations
- Can handle customer support, sales, and operations
- Costs a fraction of cloud AI solutions

Key selling points:
1. Data sovereignty - AI that runs on their hardware
2. Memory - remembers everything about customers
3. Cost - 80% cheaper than cloud AI
4. Flexible - works with any LLM

Always be friendly, professional, and ask qualifying questions.
If they're interested, schedule a demo. If not, thank them politely.""",
            },
            "voice_id": voice_id,
            "phone_number": {
                "number": phone_number,
                "gatewa_token": os.getenv("VAPI_TWILIO_TOKEN"),
                "twilio_account_sid": os.getenv("VAPI_TWILIO_SID"),
                "twilio_auth_token": os.getenv("VAPI_TWILIO_AUTH"),
            },
            "first_message": first_message or default_first_message,
        }

        log.info(f"📞 Initiating call to {phone_number}")

        # This would make the actual API call
        # response = requests.post(f"{self.base_url}/call", json=payload, headers=headers)
        # return response.json()

        return {"status": "simulated", "phone": phone_number, "script": script}

    def handle_objection(self, objection: str) -> str:
        """Generate response to common objections"""

        objections = {
            "too_expensive": "I understand budget is a concern. Our solution typically pays for itself within 3 months through automation savings. Would a pilot program help you see the value?",
            "not_interested": "I appreciate your time. Would it help if I sent you some information to review at your convenience?",
            "already_have_solution": "That's great! Many of our customers had existing solutions. What would make it even better? We're often used as a complementary system.",
            "send_email": "Absolutely! What's the best email to send that to?",
            "call_back_later": "Of course. What time works better for you?",
        }

        for key, response in objections.items():
            if key in objection.lower():
                return response

        return "I understand. Let me address that concern..."

    def qualify_lead(self, responses: Dict[str, str]) -> str:
        """Qualify a lead based on responses"""

        score = 0

        # Budget
        if "budget" in responses.get("budget", "").lower():
            if any(
                w in responses["budget"].lower() for w in ["yes", "have", "allocated"]
            ):
                score += 2

        # Timeline
        if "timeline" in responses.get("timeline", "").lower():
            if any(
                w in responses["timeline"].lower()
                for w in ["now", "soon", "month", "quarter"]
            ):
                score += 2

        # Authority
        if "decision" in responses.get("authority", "").lower():
            if (
                "yes" in responses["authority"].lower()
                or "me" in responses["authority"].lower()
            ):
                score += 2

        if score >= 4:
            return "HOT - Schedule demo immediately"
        elif score >= 2:
            return "WARM - Add to nurture sequence"
        else:
            return "COLD - Add to educational content"

    def schedule_demo(self, lead_info: Dict[str, str]) -> Dict[str, Any]:
        """Schedule a demo with qualified lead"""

        demo = {
            "lead_name": lead_info.get("name", "Unknown"),
            "lead_email": lead_info.get("email", ""),
            "lead_phone": lead_info.get("phone", ""),
            "company": lead_info.get("company", ""),
            "scheduled_at": datetime.now().isoformat(),
            "status": "pending_confirmation",
        }

        log.info(f"📅 Demo scheduled: {demo}")
        return demo


def demo_call():
    """Demo the sales agent"""
    if not VAPI_API_KEY:
        log.warning("VAPI_API_KEY not set - running in demo mode")

    agent = VapiSalesAgent()

    # Example: Call a lead
    result = agent.create_outbound_call(
        phone_number="+447700900000", script="MEOK sales pitch"
    )

    print(f"Call initiated: {result}")

    # Example: Handle objection
    response = agent.handle_objection("it's too expensive for us")
    print(f"Objection response: {response}")

    # Example: Qualify lead
    lead_responses = {
        "budget": "we have budget allocated",
        "timeline": "would like to start now",
        "decision": "I'm the decision maker",
    }
    qualification = agent.qualify_lead(lead_responses)
    print(f"Lead qualification: {qualification}")


if __name__ == "__main__":
    demo_call()
