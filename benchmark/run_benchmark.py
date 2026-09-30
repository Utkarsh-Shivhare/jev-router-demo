"""Benchmark script comparing Jev and LLM routing."""
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.schemas import SupportCategory, SupportRequest
from app.routers.jev_router import JevRouter
from app.routers.llm_router import LLMRouter


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.correct = 0
        self.total = 0
        self.errors = 0
        self.latencies: list[float] = []

    def add_success(self, latency_ms: float, is_correct: bool):
        """Record a successful routing."""
        self.total += 1
        if is_correct:
            self.correct += 1
        self.latencies.append(latency_ms)

    def add_error(self):
        """Record a routing error."""
        self.errors += 1
        self.total += 1

    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage."""
        if self.total == 0:
            return 0.0
        return (self.correct / self.total) * 100

    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)

    @property
    def median_latency(self) -> float:
        """Calculate median latency."""
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)

    @property
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency."""
        if len(self.latencies) < 2:
            return self.avg_latency
        sorted_latencies = sorted(self.latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[p95_index]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "accuracy": round(self.accuracy, 2),
            "correct": self.correct,
            "total": self.total,
            "errors": self.errors,
            "avg_latency_ms": round(self.avg_latency, 2),
            "median_latency_ms": round(self.median_latency, 2),
            "p95_latency_ms": round(self.p95_latency, 2),
        }


async def benchmark_router(
    router: JevRouter | LLMRouter,
    name: str,
    dataset: list[dict[str, str]],
) -> BenchmarkResult:
    """Benchmark a single router.
    
    Args:
        router: Router instance to benchmark.
        name: Name of the router.
        dataset: List of test cases.
        
    Returns:
        BenchmarkResult with statistics.
    """
    result = BenchmarkResult(name)
    
    print(f"\n{'=' * 60}")
    print(f"Benchmarking {name}")
    print(f"{'=' * 60}")
    
    for i, test_case in enumerate(dataset, 1):
        message = test_case["message"]
        expected = SupportCategory(test_case["expected"])
        
        print(f"\n[{i}/{len(dataset)}] Testing: {message[:60]}...")
        
        try:
            request = SupportRequest(message=message)
            start_time = time.perf_counter()
            response = await router.route(request)
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            is_correct = response.decision.choice == expected
            result.add_success(latency_ms, is_correct)
            
            status = "✓" if is_correct else "✗"
            print(
                f"  {status} Predicted: {response.decision.choice.value} "
                f"(Expected: {expected.value}) "
                f"| Confidence: {response.decision.probability:.2f} "
                f"| Latency: {latency_ms:.2f}ms"
            )
            
        except Exception as e:
            result.add_error()
            print(f"  ✗ ERROR: {str(e)}")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.1)
    
    print(f"\n{name} Results:")
    print(f"  Accuracy: {result.accuracy:.2f}%")
    print(f"  Avg Latency: {result.avg_latency:.2f}ms")
    print(f"  Median Latency: {result.median_latency:.2f}ms")
    print(f"  P95 Latency: {result.p95_latency:.2f}ms")
    print(f"  Errors: {result.errors}")
    
    return result


def print_comparison_table(jev_result: BenchmarkResult, llm_result: BenchmarkResult):
    """Print formatted comparison table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print()
    print(f"{'Metric':<20} {'Jev':<20} {'LLM':<20} {'Difference':<20}")
    print("-" * 80)
    
    # Accuracy
    jev_acc = jev_result.accuracy
    llm_acc = llm_result.accuracy
    acc_diff = jev_acc - llm_acc
    print(
        f"{'Accuracy':<20} "
        f"{jev_acc:>6.2f}%{'':<13} "
        f"{llm_acc:>6.2f}%{'':<13} "
        f"{acc_diff:>+6.2f}%"
    )
    
    # Average Latency
    jev_avg = jev_result.avg_latency
    llm_avg = llm_result.avg_latency
    avg_diff = jev_avg - llm_avg
    avg_pct = ((llm_avg - jev_avg) / llm_avg * 100) if llm_avg > 0 else 0
    print(
        f"{'Avg Latency':<20} "
        f"{jev_avg:>6.2f}ms{'':<12} "
        f"{llm_avg:>6.2f}ms{'':<12} "
        f"{avg_diff:>+6.2f}ms ({avg_pct:+.1f}%)"
    )
    
    # Median Latency
    jev_med = jev_result.median_latency
    llm_med = llm_result.median_latency
    med_diff = jev_med - llm_med
    print(
        f"{'Median Latency':<20} "
        f"{jev_med:>6.2f}ms{'':<12} "
        f"{llm_med:>6.2f}ms{'':<12} "
        f"{med_diff:>+6.2f}ms"
    )
    
    # P95 Latency
    jev_p95 = jev_result.p95_latency
    llm_p95 = llm_result.p95_latency
    p95_diff = jev_p95 - llm_p95
    print(
        f"{'P95 Latency':<20} "
        f"{jev_p95:>6.2f}ms{'':<12} "
        f"{llm_p95:>6.2f}ms{'':<12} "
        f"{p95_diff:>+6.2f}ms"
    )
    
    # Errors
    print(
        f"{'Errors':<20} "
        f"{jev_result.errors:<20} "
        f"{llm_result.errors:<20} "
        f"{jev_result.errors - llm_result.errors:>+20}"
    )
    
    print("-" * 80)
    print()


async def main():
    """Run the benchmark."""
    print("\n" + "=" * 80)
    print("AI SUPPORT ROUTER BENCHMARK")
    print("=" * 80)
    print()
    print("This benchmark compares two routing approaches:")
    print("1. Jev (TypeSafe AI) - Specialized decision model")
    print("2. LLM - Traditional language model with structured output")
    print()
    print("Dataset: 50 realistic support messages across 5 categories")
    print()
    
    # Load dataset
    dataset_path = Path(__file__).parent / "dataset.json"
    with open(dataset_path) as f:
        dataset = json.load(f)
    
    print(f"Loaded {len(dataset)} test cases")
    
    # Check API keys
    jev_configured = (
        settings.OPENROUTER_API_KEY
        or settings.TYPESAFE_API_KEY
        or settings.AI_GATEWAY_API_KEY
    )
    if not jev_configured:
        print("\n⚠️  WARNING: No Jev API key configured. Jev benchmark will fail.")
        print("   Set OPENROUTER_API_KEY, TYPESAFE_API_KEY, or AI_GATEWAY_API_KEY in your .env file.")
    
    if not settings.LLM_API_KEY:
        print("\n⚠️  WARNING: LLM_API_KEY not set. LLM benchmark will fail.")
        print("   Set it in your .env file to run LLM benchmarks.")
    
    # Initialize routers
    jev_router = JevRouter()
    llm_router = LLMRouter()
    
    try:
        # Benchmark Jev
        jev_result = BenchmarkResult("Jev")
        if jev_configured:
            provider_name = getattr(jev_router, 'provider', 'unknown')
            print(f"\nUsing Jev provider: {provider_name}")
            jev_result = await benchmark_router(jev_router, f"Jev ({provider_name})", dataset)
        else:
            print("\n⚠️  Skipping Jev benchmark (no API key)")
        
        # Benchmark LLM
        llm_result = BenchmarkResult("LLM")
        if settings.LLM_API_KEY:
            llm_result = await benchmark_router(llm_router, "LLM", dataset)
        else:
            print("\n⚠️  Skipping LLM benchmark (no API key)")
        
        # Print comparison
        if jev_result.total > 0 and llm_result.total > 0:
            print_comparison_table(jev_result, llm_result)
        
        # Save results
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_size": len(dataset),
            "jev": jev_result.to_dict(),
            "llm": llm_result.to_dict(),
        }
        
        results_path = Path(__file__).parent / "results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {results_path}")
        print()
        
        # Print honest interpretation
        print("=" * 80)
        print("INTERPRETATION")
        print("=" * 80)
        print()
        print("Important notes:")
        print("- These results reflect THIS specific benchmark on THIS dataset")
        print("- Network latency affects both approaches")
        print("- Model selection and prompting significantly impact LLM performance")
        print("- Jev is optimized for structured decisions; LLMs excel at generation")
        print("- Small datasets may not be representative of production workloads")
        print("- Use the right tool for the right job")
        print()
        
    finally:
        # Cleanup
        jev_router.close()
        await llm_router.close()


if __name__ == "__main__":
    asyncio.run(main())
