"""Tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError

from app.models.schemas import Decision, RoutingResponse, SupportCategory, SupportRequest


class TestSupportRequest:
    """Tests for SupportRequest schema."""

    def test_valid_request(self):
        """Test valid support request."""
        request = SupportRequest(message="Help me with my order")
        assert request.message == "Help me with my order"

    def test_empty_message_fails(self):
        """Test that empty message is rejected."""
        with pytest.raises(ValidationError):
            SupportRequest(message="")


class TestSupportCategory:
    """Tests for SupportCategory enum."""

    def test_valid_categories(self):
        """Test all valid categories."""
        assert SupportCategory.REFUND.value == "refund"
        assert SupportCategory.ORDER_STATUS.value == "order_status"
        assert SupportCategory.BILLING.value == "billing"
        assert SupportCategory.TECHNICAL_SUPPORT.value == "technical_support"
        assert SupportCategory.GENERAL_SUPPORT.value == "general_support"

    def test_category_from_string(self):
        """Test creating category from string."""
        category = SupportCategory("refund")
        assert category == SupportCategory.REFUND


class TestDecision:
    """Tests for Decision schema."""

    def test_valid_decision(self):
        """Test valid decision."""
        decision = Decision(
            choice=SupportCategory.REFUND,
            probability=0.95,
        )
        assert decision.choice == SupportCategory.REFUND
        assert decision.probability == 0.95

    def test_probability_range_validation(self):
        """Test probability must be between 0 and 1."""
        # Valid probabilities
        Decision(choice=SupportCategory.REFUND, probability=0.0)
        Decision(choice=SupportCategory.REFUND, probability=0.5)
        Decision(choice=SupportCategory.REFUND, probability=1.0)
        
        # Invalid probabilities
        with pytest.raises(ValidationError):
            Decision(choice=SupportCategory.REFUND, probability=-0.1)
        
        with pytest.raises(ValidationError):
            Decision(choice=SupportCategory.REFUND, probability=1.1)

    def test_invalid_category(self):
        """Test that invalid category is rejected."""
        with pytest.raises(ValidationError):
            Decision(choice="invalid_category", probability=0.5)


class TestRoutingResponse:
    """Tests for RoutingResponse schema."""

    def test_valid_routing_response(self):
        """Test valid routing response."""
        decision = Decision(choice=SupportCategory.REFUND, probability=0.95)
        response = RoutingResponse(
            router="jev",
            decision=decision,
            workflow="refund_workflow",
            latency_ms=123.45,
        )
        assert response.router == "jev"
        assert response.decision.choice == SupportCategory.REFUND
        assert response.workflow == "refund_workflow"
        assert response.latency_ms == 123.45

    def test_invalid_router_type(self):
        """Test that invalid router type is rejected."""
        decision = Decision(choice=SupportCategory.REFUND, probability=0.95)
        with pytest.raises(ValidationError):
            RoutingResponse(
                router="unknown",
                decision=decision,
                workflow="test",
                latency_ms=100.0,
            )

    def test_negative_latency_fails(self):
        """Test that negative latency is rejected."""
        decision = Decision(choice=SupportCategory.REFUND, probability=0.95)
        with pytest.raises(ValidationError):
            RoutingResponse(
                router="jev",
                decision=decision,
                workflow="test",
                latency_ms=-10.0,
            )
