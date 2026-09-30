"""Pydantic schemas for API requests and responses."""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SupportCategory(str, Enum):
    """Valid support routing categories."""

    REFUND = "refund"
    ORDER_STATUS = "order_status"
    BILLING = "billing"
    TECHNICAL_SUPPORT = "technical_support"
    GENERAL_SUPPORT = "general_support"


class SupportRequest(BaseModel):
    """Incoming support request."""

    message: str = Field(..., min_length=1, description="Customer support message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"message": "My order arrived damaged and I want a refund."},
                {"message": "Where is my package?"},
                {"message": "I was charged twice."},
            ]
        }
    }


class Decision(BaseModel):
    """Routing decision with confidence."""

    choice: SupportCategory = Field(..., description="Selected support category")
    probability: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")

    @field_validator("probability")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        """Ensure probability is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Probability must be between 0 and 1")
        return v


class TokenUsage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = Field(..., description="Input tokens used")
    completion_tokens: int = Field(..., description="Output tokens generated")
    total_tokens: int = Field(..., description="Total tokens")


class CostBreakdown(BaseModel):
    """Cost breakdown in USD."""
    
    input_cost: float = Field(..., description="Cost for input tokens")
    output_cost: float = Field(..., description="Cost for output tokens")
    total_cost: float = Field(..., description="Total cost in USD")


class RoutingResponse(BaseModel):
    """Unified routing response."""

    router: Literal["jev", "llm"] = Field(..., description="Which router was used")
    decision: Decision = Field(..., description="Routing decision")
    workflow: str = Field(..., description="Selected workflow identifier")
    latency_ms: float = Field(..., ge=0, description="Request latency in milliseconds")
    tokens: Optional[TokenUsage] = Field(None, description="Token usage")
    cost: Optional[CostBreakdown] = Field(None, description="Cost breakdown")
    request: Optional[SupportRequest] = Field(None, description="Original request (optional)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "router": "jev",
                    "decision": {
                        "choice": "refund",
                        "probability": 0.96,
                    },
                    "workflow": "refund_workflow",
                    "latency_ms": 87.2,
                }
            ]
        }
    }


class CompareResponse(BaseModel):
    """Side-by-side comparison of both routers."""

    input: str = Field(..., description="Original support message")
    jev: RoutingResponse = Field(..., description="Jev router result")
    llm: RoutingResponse = Field(..., description="LLM router result")


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok"] = "ok"
    version: str = Field(..., description="Application version")


class RootResponse(BaseModel):
    """Root endpoint response."""

    name: str = Field(..., description="Application name")
    description: str = Field(..., description="Project description")
    version: str = Field(..., description="Application version")
    docs_url: str = Field(..., description="API documentation URL")
