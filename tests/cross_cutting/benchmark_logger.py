"""Performance benchmark for logger emit() function (T058, SC-004).

Success Criterion: emit() call must complete in <20ms per call.
Measurement: 1000 sequential emissions with all operations included.

Run: python3 -m tests.cross_cutting.benchmark_logger
"""

import time
from langagent.cross_cutting import emit


def benchmark_emit_performance():
    """Benchmark emit() performance over 1000 calls.
    
    SC-004: Logging overhead must be under 20ms per emit() call.
    Measurement includes all operations:
    - Tag validation
    - Lock acquisition
    - JSON serialization
    - Stderr writes
    - Lock release
    """
    iterations = 1000
    tag = "la.runtime.main_loop.turn.start"
    payload = {
        "message": "benchmark test",
        "iteration": 0,
        "data": {"key": "value", "nested": {"a": 1, "b": 2}},
    }
    
    # Warm-up (exclude from measurement)
    for _ in range(10):
        emit(tag, payload)
    
    # Actual benchmark
    start_time = time.perf_counter()
    
    for i in range(iterations):
        payload["iteration"] = i
        emit(tag, payload)
    
    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / iterations
    
    print(f"\n{'='*60}")
    print(f"Logger Performance Benchmark (SC-004)")
    print(f"{'='*60}")
    print(f"Iterations: {iterations}")
    print(f"Total time: {total_time_ms:.2f} ms")
    print(f"Average per emit(): {avg_time_ms:.3f} ms")
    print(f"Target: <20.000 ms")
    print(f"Status: {'✓ PASS' if avg_time_ms < 20 else '✗ FAIL'}")
    print(f"{'='*60}\n")
    
    assert avg_time_ms < 20, f"Performance target not met: {avg_time_ms:.3f} ms > 20 ms"
    return avg_time_ms


if __name__ == "__main__":
    benchmark_emit_performance()
    print("✓ Benchmark complete. Performance within target.")
