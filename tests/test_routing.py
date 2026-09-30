"""Tests for routing logic."""
import pytest

from app.models.schemas import SupportCategory
from app.services.support_service import (
    execute_workflow,
    get_workflow_name,
    refund_workflow,
)


class TestWorkflowMapping:
    """Tests for workflow mapping."""

    def test_workflow_name_generation(self):
        """Test workflow name generation from category."""
        assert get_workflow_name(SupportCategory.REFUND) == "refund_workflow"
        assert get_workflow_name(SupportCategory.ORDER_STATUS) == "order_status_workflow"
        assert get_workflow_name(SupportCategory.BILLING) == "billing_workflow"
        assert (
            get_workflow_name(SupportCategory.TECHNICAL_SUPPORT)
            == "technical_support_workflow"
        )
        assert (
            get_workflow_name(SupportCategory.GENERAL_SUPPORT)
            == "general_support_workflow"
        )

    def test_workflow_execution(self):
        """Test workflow execution returns a response."""
        message = "Test message"
        for category in SupportCategory:
            response = execute_workflow(category, message)
            assert isinstance(response, str)
            assert len(response) > 0

    def test_refund_workflow_returns_string(self):
        """Test refund workflow returns expected response."""
        response = refund_workflow("My product is broken")
        assert isinstance(response, str)
        assert "refund" in response.lower()


class TestCategoryValidation:
    """Tests for category validation."""

    def test_all_categories_have_workflows(self):
        """Test that all categories have corresponding workflows."""
        for category in SupportCategory:
            workflow_name = get_workflow_name(category)
            assert workflow_name.endswith("_workflow")
            
            # Execute workflow should not raise
            result = execute_workflow(category, "test")
            assert isinstance(result, str)
