"""LLM-based routing using OpenAI-compatible API."""
import json
import logging
import time
from typing import Any, Optional

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

# GPT-4o-mini pricing (OpenAI actual prices)
GPT4O_MINI_INPUT_PRICE_PER_MILLION = 0.15  # $0.15 per million input tokens
GPT4O_MINI_OUTPUT_PRICE_PER_MILLION = 0.60  # $0.60 per million output tokens


class LLMRouter:
    """Router using traditional LLM for classification."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize LLM router.
        
        Args:
            api_key: LLM API key. Falls back to settings if not provided.
            model: Model name. Falls back to settings if not provided.
            base_url: API base URL. Falls back to settings if not provided.
        """
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url or settings.LLM_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def route(self, request: SupportRequest) -> RoutingResponse:
        """Route support request using LLM.
        
        Args:
            request: Support request to route.
            
        Returns:
            RoutingResponse with decision and metadata.
            
        Raises:
            RuntimeError: If API key is not configured or API call fails.
        """
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not configured. "
                "Set it in your .env file or environment."
            )
        
        start_time = time.perf_counter()
        
        try:
            # Build the prompt for classification
            system_prompt = """You are a support ticket classifier.
Analyze the customer message and classify it into exactly ONE category.

Categories:
- refund: Customer wants money back or product return
- order_status: Customer asking about delivery or shipment tracking
- billing: Customer has payment or charge questions
- technical_support: Customer needs help with product functionality or bugs
- general_support: General questions or other requests

Respond with valid JSON only:
{
  "category": "<one of the categories above>",
  "reasoning": "<brief explanation>"
}"""

            user_prompt = f"Customer message: {request.message}"
            
            # Make API call
            response = await self.client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                },
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the classification
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            category_str = parsed["category"]
            
            # Map to our enum
            choice = SupportCategory(category_str)
            
            # Extract token usage
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            # Calculate cost using real OpenAI pricing
            input_cost = (prompt_tokens / 1_000_000) * GPT4O_MINI_INPUT_PRICE_PER_MILLION
            output_cost = (completion_tokens / 1_000_000) * GPT4O_MINI_OUTPUT_PRICE_PER_MILLION
            total_cost = input_cost + output_cost
            
            # Note: Most LLMs don't provide reliable probability scores
            # for classification tasks in this format. We use 1.0 to indicate
            # this is the model's definitive choice, but this is a limitation
            # of traditional LLM routing compared to specialized decision models.
            probability = 1.0
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            decision = Decision(choice=choice, probability=probability)
            workflow = get_workflow_name(choice)
            
            return RoutingResponse(
                router="llm",
                decision=decision,
                workflow=workflow,
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
            
        except httpx.HTTPStatusError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"LLM API error after {elapsed_ms:.2f}ms: {e.response.text}")
            raise RuntimeError(f"LLM API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"LLM routing failed after {elapsed_ms:.2f}ms: {e}")
            raise RuntimeError(f"LLM routing failed: {str(e)}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_llm_router_instance: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create singleton LLM router instance."""
    global _llm_router_instance
    if _llm_router_instance is None:
        _llm_router_instance = LLMRouter()
    return _llm_router_instance
