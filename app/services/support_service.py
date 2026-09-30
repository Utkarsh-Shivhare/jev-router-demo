"""Support workflow simulation service."""
from app.models.schemas import SupportCategory


def get_workflow_name(category: SupportCategory) -> str:
    """Get workflow identifier from category."""
    return f"{category.value}_workflow"


def refund_workflow(message: str) -> str:
    """Handle refund requests."""
    return (
        "Refund workflow initiated. "
        "A support agent will review your request and process the refund within 3-5 business days. "
        "You will receive a confirmation email shortly."
    )


def order_status_workflow(message: str) -> str:
    """Handle order status inquiries."""
    return (
        "Order status workflow initiated. "
        "Retrieving tracking information for your order. "
        "Your package is currently in transit and estimated to arrive within 2-3 business days."
    )


def billing_workflow(message: str) -> str:
    """Handle billing issues."""
    return (
        "Billing workflow initiated. "
        "Our billing team will investigate the charge discrepancy. "
        "You should receive a response within 24 hours. "
        "If a billing error is confirmed, corrections will be applied immediately."
    )


def technical_support_workflow(message: str) -> str:
    """Handle technical support requests."""
    return (
        "Technical support workflow initiated. "
        "A technical specialist will assist you with troubleshooting. "
        "Please ensure you have the latest version of the app installed. "
        "Expected response time: 1-2 hours."
    )


def general_support_workflow(message: str) -> str:
    """Handle general support inquiries."""
    return (
        "General support workflow initiated. "
        "Your inquiry has been logged and will be reviewed by our support team. "
        "You should receive a detailed response within 24-48 hours."
    )


def execute_workflow(category: SupportCategory, message: str) -> str:
    """Execute the appropriate workflow based on category."""
    workflow_map = {
        SupportCategory.REFUND: refund_workflow,
        SupportCategory.ORDER_STATUS: order_status_workflow,
        SupportCategory.BILLING: billing_workflow,
        SupportCategory.TECHNICAL_SUPPORT: technical_support_workflow,
        SupportCategory.GENERAL_SUPPORT: general_support_workflow,
    }
    
    workflow_func = workflow_map.get(category, general_support_workflow)
    return workflow_func(message)
