"""
Performance Load Testing script for Phase 5.
Simulates 100 concurrent users submitting symptoms to measure API latency.

Usage:
    python backend/tests/performance/load_test.py --users 100 --requests 1000
"""

import asyncio
import time
import argparse
import statistics
import httpx


async def submit_symptoms(client: httpx.AsyncClient, patient_id: str) -> float:
    """Submit a symptom analysis request and return the latency in seconds."""
    payload = {
        "patient_id": patient_id,
        "symptoms": ["chest pain", "shortness of breath", "nausea"],
        "duration_days": 2,
        "severity": "high",
    }
    
    start_time = time.perf_counter()
    response = await client.post("/api/v1/analyze/symptoms", json=payload)
    end_time = time.perf_counter()
    
    # We only care if it was accepted or not
    if response.status_code not in (200, 202):
        raise httpx.RequestError(f"Failed with status: {response.status_code}")
        
    return end_time - start_time


async def worker(client: httpx.AsyncClient, num_requests: int, patient_id: str, results: list[float], errors: list[str]) -> None:
    for _ in range(num_requests):
        try:
            latency = await submit_symptoms(client, patient_id)
            results.append(latency)
        except Exception as e:
            errors.append(str(e))


async def run_load_test(base_url: str, num_users: int, total_requests: int) -> None:
    print(f"Starting load test on {base_url} with {num_users} users for {total_requests} requests.")
    
    requests_per_user = total_requests // num_users
    results: list[float] = []
    errors: list[str] = []
    
    # Normally we would fetch the mock patient ID from DB, using a hardcoded valid ID format or random object id
    # Since this hits the endpoint, it will either get 404 or 422 if auth isn't provided.
    # To bypass auth/validation in load test, we'll assume testing endpoint handles valid tokens/ids if needed
    # For now, we simulate the HTTP roundtrip latency.
    fake_patient_id = "507f1f77bcf86cd799439011" 

    start_time = time.perf_counter()
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        tasks = [
            worker(client, requests_per_user, fake_patient_id, results, errors)
            for _ in range(num_users)
        ]
        await asyncio.gather(*tasks)
        
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    _print_report(results, errors, total_time)


def _print_report(results: list[float], errors: list[str], total_time: float) -> None:
    print("\n--- Load Test Results ---")
    if not results:
        print("No successful requests.")
        if errors:
            print(f"Errors encountered (first 5): {errors[:5]}")
        return

    req_count = len(results)
    throughput = req_count / total_time
    
    # Calculate Latencies
    p50 = statistics.median(results)
    p95 = statistics.quantiles(results, n=20)[18] if len(results) >= 20 else max(results)
    p99 = statistics.quantiles(results, n=100)[98] if len(results) >= 100 else max(results)
    
    print(f"Total Requests  : {req_count + len(errors)}")
    print(f"Successful      : {req_count}")
    print(f"Failed          : {len(errors)}")
    print(f"Total Time      : {total_time:.2f} s")
    print(f"Throughput      : {throughput:.2f} req/s\n")
    
    print(f"Latency P50     : {p50:.4f} s")
    print(f"Latency P95     : {p95:.4f} s (Target: < 1.5s)")
    print(f"Latency P99     : {p99:.4f} s (Target: < 5.0s)")

    if errors:
        print(f"\nErrors: {len(errors)} errors recorded. Example: {errors[0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API Load Tester")
    parser.add_argument("--url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--requests", type=int, default=1000, help="Total number of requests")
    args = parser.parse_args()

    asyncio.run(run_load_test(args.url, args.users, args.requests))
