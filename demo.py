"""Interactive CLI demo for AI Support Router."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.models.schemas import SupportRequest
from app.routers.jev_router import JevRouter
from app.routers.llm_router import LLMRouter
from app.services.support_service import execute_workflow


async def demo():
    """Run interactive demo."""
    print("\n" + "=" * 70)
    print("AI SUPPORT ROUTER - INTERACTIVE DEMO")
    print("=" * 70)
    print()
    print("This demo compares Jev (TypeSafe AI) and traditional LLM routing.")
    print()
    
    # Check configuration
    jev_configured = (
        settings.OPENROUTER_API_KEY
        or settings.TYPESAFE_API_KEY
        or settings.AI_GATEWAY_API_KEY
    )
    if not jev_configured:
        print("⚠️  WARNING: No Jev API key configured")
        print("   Set OPENROUTER_API_KEY, TYPESAFE_API_KEY, or AI_GATEWAY_API_KEY")
        print()
    
    if not settings.LLM_API_KEY:
        print("⚠️  WARNING: LLM_API_KEY not set")
        print("   LLM routing will not work. Set it in .env file.")
        print()
    
    # Example messages
    examples = [
        "My order arrived damaged and I want a refund.",
        "Where is my package? It hasn't arrived yet.",
        "I was charged twice for the same order.",
        "The app keeps crashing when I try to checkout.",
        "How do I change my account details?",
    ]
    
    print("Example messages:")
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. {ex}")
    print()
    
    while True:
        # Get input
        print("-" * 70)
        user_input = input("\nEnter support request (or 'quit' to exit): ").strip()
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break
        
        if not user_input:
            print("Please enter a message.")
            continue
        
        # Handle example selection
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(examples):
                user_input = examples[idx]
                print(f"Using example: {user_input}")
            else:
                print("Invalid example number.")
                continue
        
        request = SupportRequest(message=user_input)
        
        print(f"\n{'─' * 70}")
        print(f"REQUEST: {user_input}")
        print(f"{'─' * 70}")
        
        # Initialize routers
        jev_router = JevRouter()
        llm_router = LLMRouter()
        
        try:
            # Try Jev
            if jev_configured:
                jev_provider = getattr(jev_router, 'provider', 'unknown')
                print(f"\n┌─ JEV (via {jev_provider}) ──────────────────────────────────────────────┐"[:65]+"┐")
                try:
                    jev_result = await jev_router.route(request)
                    print(f"│ Decision:     {jev_result.decision.choice.value:<43} │")
                    print(f"│ Confidence:   {jev_result.decision.probability:.2%}{'':<41} │")
                    print(f"│ Latency:      {jev_result.latency_ms:.2f}ms{'':<39} │")
                    print(f"│ Workflow:     {jev_result.workflow:<43} │")
                    print("└──────────────────────────────────────────────────────────────┘")
                except Exception as e:
                    print(f"│ ERROR: {str(e):<52} │")
                    print("└──────────────────────────────────────────────────────────────┘")
            else:
                print("\n[Jev routing skipped - no API key configured]")
            
            # Try LLM
            if settings.LLM_API_KEY:
                print("\n┌─ LLM (Traditional) ─────────────────────────────────────────┐")
                try:
                    llm_result = await llm_router.route(request)
                    print(f"│ Decision:     {llm_result.decision.choice.value:<43} │")
                    print(f"│ Confidence:   {llm_result.decision.probability:.2%}{'':<41} │")
                    print(f"│ Latency:      {llm_result.latency_ms:.2f}ms{'':<39} │")
                    print(f"│ Workflow:     {llm_result.workflow:<43} │")
                    print("└──────────────────────────────────────────────────────────────┘")
                except Exception as e:
                    print(f"│ ERROR: {str(e):<52} │")
                    print("└──────────────────────────────────────────────────────────────┘")
            else:
                print("\n[LLM routing skipped - no API key configured]")
            
            # Show workflow execution (if at least one succeeded)
            category = None
            if jev_configured:
                try:
                    category = jev_result.decision.choice
                except:
                    pass
            if not category and settings.LLM_API_KEY:
                try:
                    category = llm_result.decision.choice
                except:
                    pass
            
            if category:
                print("\n┌─ SELECTED WORKFLOW ─────────────────────────────────────────┐")
                workflow_response = execute_workflow(category, user_input)
                # Wrap text
                words = workflow_response.split()
                lines = []
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= 57:
                        current_line += (" " if current_line else "") + word
                    else:
                        lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                
                for line in lines:
                    print(f"│ {line:<58} │")
                print("└──────────────────────────────────────────────────────────────┘")
        
        finally:
            # Cleanup
            jev_router.close()
            await llm_router.close()
        
        print()


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
