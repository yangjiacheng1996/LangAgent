"""Performance benchmark for emit() function.

Validates SC-004: emit() should complete in <5ms per call.
"""
import time
from langagent.cross_cutting import emit


def benchmark_emit():
    """Benchmark emit() performance with 1000 sequential calls."""
    iterations = 1000
    
    # Warmup
    for _ in range(10):
        emit("la.runtime.dir_load.ok", {"data": "warmup"})
    
    # Benchmark
    start_time = time.perf_counter()
    for i in range(iterations):
        emit("la.runtime.dir_load.ok", {"iteration": i, "data": "benchmark"})
    end_time = time.perf_counter()
    
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / iterations
    
    print(f"Total time: {total_time_ms:.2f}ms")
    print(f"Average time per emit(): {avg_time_ms:.3f}ms")
    print(f"Target: <5ms per emit()")
    
    if avg_time_ms < 5.0:
        print(f"✓ PASS: {avg_time_ms:.3f}ms < 5ms")
        return True
    else:
        print(f"✗ FAIL: {avg_time_ms:.3f}ms >= 5ms")
        return False


if __name__ == "__main__":
    success = benchmark_emit()
    exit(0 if success else 1)
