"""Jev-based routing with multiple provider support."""
import json
import logging
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.models.schemas import (
    CostBreakdown,
    Decision,
    RoutingResponse,
    SupportCategory,
    SupportRequest,
    TokenUsage,
)
from app.services.support_service import get_workflow_name

logger = logging.getLogger(__name__)

# Jev pricing (TypeSafe AI actual prices)
JEV_INPUT_PRICE_PER_MILLION = 0.042  # $0.042 per million input tokens
JEV_OUTPUT_PRICE_PER_MILLION = 0.0  # Output tokens are FREE


class JevRouter:
    """Router using Jev model via multiple providers.
    
    Supports:
    - TypeSafe AI direct SDK (provider='typesafe')
    - Vercel AI Gateway (provider='vercel')
    - OpenRouter (provider='openrouter')
    - Auto-detection (provider='auto')
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize Jev router.
        
        Args:
            provider: 'auto', 'typesafe', 'vercel', or 'openrouter'
            api_key: API key for selected provider
            model: Jev model name
        """
        self.provider = provider or settings.JEV_PROVIDER
        self.model = model or settings.JEV_MODEL
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Auto-detect provider if set to 'auto'
        if self.provider == "auto":
            if settings.OPENROUTER_API_KEY or api_key:
                self.provider = "openrouter"
                self.api_key = api_key or settings.OPENROUTER_API_KEY
            elif settings.TYPESAFE_API_KEY:
                self.provider = "typesafe"
                self.api_key = settings.TYPESAFE_API_KEY
            elif settings.AI_GATEWAY_API_KEY:
                self.provider = "vercel"
                self.api_key = settings.AI_GATEWAY_API_KEY
            else:
                self.provider = None
                self.api_key = None
        else:
            # Use specified provider
            if self.provider == "openrouter":
                self.api_key = api_key or settings.OPENROUTER_API_KEY
            elif self.provider == "typesafe":
                self.api_key = api_key or settings.TYPESAFE_API_KEY
            elif self.provider == "vercel":
                self.api_key = api_key or settings.AI_GATEWAY_API_KEY
            else:
                self.api_key = api_key
        
        self._typesafe_client = None

    async def route(self, request: SupportRequest) -> RoutingResponse:
        """Route support request using Jev.
        
        Args:
            request: Support request to route.
            
        Returns:
            RoutingResponse with decision and metadata.
            
        Raises:
            RuntimeError: If API key is not configured or API call fails.
        """
        if not self.api_key and self.provider != "typesafe":
            raise RuntimeError(
                f"No API key configured for Jev. "
                f"Set OPENROUTER_API_KEY, TYPESAFE_API_KEY, or AI_GATEWAY_API_KEY "
                f"in your .env file."
            )
        
        start_time = time.perf_counter()
        
        try:
            if self.provider == "typesafe":
                return await self._route_typesafe(request, start_time)
            elif self.provider == "openrouter":
                return await self._route_openrouter(request, start_time)
            elif self.provider == "vercel":
                return await self._route_vercel(request, start_time)
            else:
                raise RuntimeError(
                    f"Unknown Jev provider: {self.provider}. "
                    f"Use 'typesafe', 'openrouter', or 'vercel'."
                )
                
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Jev routing failed after {elapsed_ms:.2f}ms: {e}")
            raise
    
    async def _route_typesafe(
        self, request: SupportRequest, start_time: float
    ) -> RoutingResponse:
        """Route using direct TypeSafe SDK."""
        try:
            from typesafe_sdk import Choice, TypeSafeClient
            
            if self._typesafe_client is None:
                self._typesafe_client = TypeSafeClient(api_key=self.api_key)
            
            # Build the state and question for Jev
            state = {"message": request.message}
            
            questions = {
                "category": Choice(
                    instructions="What type of support does this customer need?",
                    criteria={
                        "refund": "Customer wants money back or return",
                        "order_status": "Customer asking about delivery or shipment tracking",
                        "billing": "Customer has payment or charge questions",
                        "technical_support": "Customer needs help with product functionality or bugs",
                        "general_support": "General questions or other requests",
                    },
                )
            }
            
            response = self._typesafe_client.system_one(state=state, questions=questions)
            
            category_answer = response.choices["category"]
            choice = SupportCategory(category_answer.choice)
            confidence = category_answer.confidence
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            return RoutingResponse(
                router="jev",
                decision=Decision(choice=choice, probability=confidence),
                workflow=get_workflow_name(choice),
                latency_ms=round(elapsed_ms, 2),
                request=request,
            )
            
        except ImportError:
            raise RuntimeError(
                "TypeSafe SDK not installed. Install with: pip install typesafe-sdk"
            )
    
    async def _route_openrouter(
        self, request: SupportRequest, start_time: float
    ) -> RoutingResponse:
        """Route using OpenRouter."""
        system_prompt = """Classify this support request into exactly ONE category: refund, order_status, billing, technical_support, or general_support.
Respond with ONLY the category name, nothing else."""
        
        response = await self.client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message},
                ],
            },
        )
        
        response.raise_for_status()
        result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip().lower()
        choice = SupportCategory(content)
        
        # Extract token usage
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        
        # Calculate cost using real TypeSafe pricing
        input_cost = (prompt_tokens / 1_000_000) * JEV_INPUT_PRICE_PER_MILLION
        output_cost = (completion_tokens / 1_000_000) * JEV_OUTPUT_PRICE_PER_MILLION
        total_cost = input_cost + output_cost
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return RoutingResponse(
            router="jev",
            decision=Decision(choice=choice, probability=0.95),
            workflow=get_workflow_name(choice),
            latency_ms=round(elapsed_ms, 2),
            tokens=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            cost=CostBreakdown(
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
            ),
            request=request,
        )
    
    async def _route_vercel(
        self, request: SupportRequest, start_time: float
    ) -> RoutingResponse:
        """Route using Vercel AI Gateway."""
        system_prompt = """Classify this support request into exactly ONE category: refund, order_status, billing, technical_support, or general_support.
Respond with ONLY the category name, nothing else."""
        
        response = await self.client.post(
            "https://ai-gateway.vercel.sh/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message},
                ],
            },
        )
        
        response.raise_for_status()
        result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip().lower()
        choice = SupportCategory(content)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return RoutingResponse(
            router="jev",
            decision=Decision(choice=choice, probability=0.95),
            workflow=get_workflow_name(choice),
            latency_ms=round(elapsed_ms, 2),
            request=request,
        )
    
    async def close(self):
        """Close HTTP client and TypeSafe client."""
        await self.client.aclose()
        if self._typesafe_client is not None:
            try:
                self._typesafe_client.close()
            except:
                pass


# Singleton instance
_jev_router_instance: Optional[JevRouter] = None


def get_jev_router() -> JevRouter:
    """Get or create singleton Jev router instance."""
    global _jev_router_instance
    if _jev_router_instance is None:
        _jev_router_instance = JevRouter()
    return _jev_router_instance
