"""Concurrency stress test for logger (T059, SC-007).

Success Criterion: Handle 10,000 concurrent emit() calls from 100 threads without deadlock.

Run: python3 -m tests.cross_cutting.stress_test_logger
"""

import threading
import time
from langagent.cross_cutting import emit


def stress_test_concurrent_emits():
    """Stress test with 10,000 concurrent emits from 100 threads.
    
    SC-007: Logger must handle high concurrency without deadlock or data race.
    """
    num_threads = 100
    emits_per_thread = 100
    total_emits = num_threads * emits_per_thread
    
    completed_count = [0]  # Mutable container for thread-safe counter
    lock = threading.Lock()
    
    def worker(thread_id: int):
        """Worker function: emit 100 times."""
        for i in range(emits_per_thread):
            emit("la.runtime.main_loop.model_call", {
                "thread": thread_id,
                "iteration": i,
                "message": f"stress test {thread_id}-{i}",
            })
        
        with lock:
            completed_count[0] += emits_per_thread
    
    print(f"\n{'='*60}")
    print(f"Logger Concurrency Stress Test (SC-007)")
    print(f"{'='*60}")
    print(f"Threads: {num_threads}")
    print(f"Emits per thread: {emits_per_thread}")
    print(f"Total emits: {total_emits}")
    print(f"Starting stress test...")
    
    start_time = time.perf_counter()
    
    # Launch all threads
    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=30)  # 30 second timeout per thread
    
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    
    # Check for deadlocks
    alive_threads = [t for t in threads if t.is_alive()]
    
    print(f"Completed: {completed_count[0]} / {total_emits} emits")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Throughput: {total_emits / elapsed_time:.0f} emits/second")
    print(f"Deadlocked threads: {len(alive_threads)}")
    print(f"Status: {'✓ PASS' if len(alive_threads) == 0 else '✗ FAIL (deadlock detected)'}")
    print(f"{'='*60}\n")
    
    assert len(alive_threads) == 0, f"Deadlock detected: {len(alive_threads)} threads still alive"
    assert completed_count[0] == total_emits, f"Lost emits: {completed_count[0]} != {total_emits}"
    
    return elapsed_time


if __name__ == "__main__":
    stress_test_concurrent_emits()
    print("✓ Stress test complete. No deadlocks detected.")
