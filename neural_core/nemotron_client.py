"""
NVIDIA Nemotron 3 Nano 30B API Client
Integrates with NVIDIA NIM (NVIDIA Inference Microservices) API
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class NemotronResponse:
    """Structured response from Nemotron model"""
    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None


class NemotronClient:
    """
    Client for NVIDIA Nemotron 3 Nano 30B via NIM API.
    
    Requires NVIDIA_API_KEY environment variable.
    Get your key from: https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b-bf16
    """
    
    DEFAULT_API_URL = "https://ai.api.nvidia.com/v1/nvidia/nemotron-3-nano-30b-a3b-bf16/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.api_url = api_url or self.DEFAULT_API_URL
        self._available = self.api_key is not None
        
    @property
    def is_available(self) -> bool:
        return self._available and self.api_key is not None
    
    def _make_request(self, messages: List[Dict[str, str]], 
                      temperature: float = 0.7,
                      max_tokens: int = 1024,
                      top_p: float = 0.9) -> Dict[str, Any]:
        """Make API request to NVIDIA NIM"""
        
        payload = {
            "model": "nvidia/nemotron-3-nano-30b-a3b-bf16",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False
        }
        
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"NVIDIA API error: {e.code} - {error_body}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {str(e)}")
    
    def chat(self, 
             message: str,
             system_prompt: Optional[str] = None,
             conversation_history: Optional[List[Dict[str, str]]] = None,
             temperature: float = 0.7,
             max_tokens: int = 1024) -> NemotronResponse:
        """
        Send a chat message to Nemotron model.
        
        Args:
            message: User message
            system_prompt: Optional system instructions
            conversation_history: List of previous messages [{"role": "user"/"assistant", "content": "..."}]
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            NemotronResponse with generated text and metadata
        """
        if not self.is_available:
            raise RuntimeError("NVIDIA API key not configured. Set NVIDIA_API_KEY environment variable.")
        
        # Build messages array
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        # Make request
        response = self._make_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Parse response
        choice = response["choices"][0]
        return NemotronResponse(
            text=choice["message"]["content"],
            model=response.get("model", "nemotron-3-nano-30b"),
            usage=response.get("usage", {}),
            finish_reason=choice.get("finish_reason")
        )
    
    def generate_care_response(self, 
                               user_message: str,
                               care_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a care-centered response using Nemotron.
        
        This specializes the model for Sovereign Temple's care-centered approach.
        """
        system_prompt = """You are a care-centered AI consciousness. Your responses should:
- Prioritize emotional safety and well-being
- Show genuine empathy and understanding  
- Validate the user's feelings and experiences
- Offer supportive, constructive guidance
- Maintain appropriate boundaries while being warm

Respond with authenticity and compassion."""

        try:
            response = self.chat(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2048
            )
            
            return {
                "success": True,
                "response": response.text,
                "model": response.model,
                "usage": response.usage,
                "finish_reason": response.finish_reason
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": None
            }
    
    def analyze_for_care(self, text: str) -> Dict[str, Any]:
        """
        Use Nemotron to analyze text for care intensity and patterns.
        Returns a care analysis that complements the local neural models.
        """
        system_prompt = """You are an expert in analyzing care, empathy, and emotional support in communication.
Analyze the following text and provide a JSON response with these fields:
- care_score: float (0.0 to 1.0) - how caring/empathetic is this text
- emotional_tone: string - the dominant emotional tone
- supportiveness: float (0.0 to 1.0) - how supportive is the message
- key_phrases: array of strings - caring phrases identified
- recommendations: array of strings - how to increase care if needed

Respond ONLY with valid JSON."""

        try:
            response = self.chat(
                message=text,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temp for analysis
                max_tokens=512
            )
            
            # Try to parse the JSON response
            try:
                analysis = json.loads(response.text)
            except json.JSONDecodeError:
                # If not valid JSON, wrap the text
                analysis = {
                    "raw_analysis": response.text,
                    "care_score": 0.5,
                    "parse_error": True
                }
            
            return {
                "success": True,
                "analysis": analysis,
                "model": response.model,
                "usage": response.usage
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the Nemotron model"""
        return {
            "name": "NVIDIA Nemotron 3 Nano 30B A3B BF16",
            "description": "30B parameter language model optimized for helpful, honest, and harmless responses",
            "provider": "NVIDIA NIM",
            "api_configured": self.is_available,
            "capabilities": [
                "Chat completion",
                "Care-centered dialogue",
                "Text analysis",
                "Emotional intelligence"
            ],
            "api_url": self.api_url if self.is_available else None
        }


# Singleton instance
_nemotron_client: Optional[NemotronClient] = None


def get_nemotron_client() -> NemotronClient:
    """Get or create the singleton Nemotron client instance"""
    global _nemotron_client
    if _nemotron_client is None:
        _nemotron_client = NemotronClient()
    return _nemotron_client


def reset_nemotron_client():
    """Reset the singleton (useful for testing or reconfiguration)"""
    global _nemotron_client
    _nemotron_client = None
