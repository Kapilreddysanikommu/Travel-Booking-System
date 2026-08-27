"""
Before/after cache benchmark for GET /flights/{id} and GET /hotels/{id}.

Compares average response time with the Redis cache forced cold (deleted
before every request, so every hit goes to MySQL) against the cache left
warm (populated once, then read repeatedly) - showing cache-aside's actual
effect on this project's seeded data, not a synthetic number.

Requires the stack running (docker-compose up) and seed_data.py already
run at least once. Needs the `redis` package on the host:
    pip install redis

Run from the repo root:
    python benchmark_cache.py flight
    python benchmark_cache.py hotel
"""

import http.client
import json
import sys
import time
from urllib.parse import urlsplit

from redis import Redis

NUM_REQUESTS = 100

RESOURCES = {
    "flight": {
        "base_url": "http://localhost:8002",
        "list_path": "/flights",
        "id_field": "flight_id",
        "cache_key_prefix": "flight",
    },
    "hotel": {
        "base_url": "http://localhost:8003",
        "list_path": "/hotels",
        "id_field": "hotel_id",
        "cache_key_prefix": "hotel",
    },
}


def open_connection(base_url: str) -> http.client.HTTPConnection:
    """
    One persistent HTTP/1.1 (keep-alive) connection, reused for every
    request in a phase. urlopen()-per-request would pay a fresh TCP
    handshake (a few ms on loopback) on every single call, which is bigger
    than the MySQL-vs-Redis difference we're actually trying to measure -
    reusing one connection removes that noise from both phases equally.
    """
    parts = urlsplit(base_url)
    return http.client.HTTPConnection(parts.hostname, parts.port)


def fetch_json(conn: http.client.HTTPConnection, path: str):
    conn.request("GET", path)
    response = conn.getresponse()
    return json.loads(response.read())


def pick_sample_id(conn: http.client.HTTPConnection, resource: dict) -> str:
    """Grab one real id from live seeded data instead of hardcoding one."""
    items = fetch_json(conn, f"{resource['list_path']}?limit=1")
    if not items:
        raise SystemExit(
            f"No {resource['cache_key_prefix']} records found - has seed_data.py been run?"
        )
    return items[0][resource["id_field"]]


def timed_get(conn: http.client.HTTPConnection, path: str) -> float:
    """One GET request over the given connection, returned as elapsed seconds."""
    start = time.perf_counter()
    fetch_json(conn, path)
    return time.perf_counter() - start


def benchmark(resource_name: str) -> None:
    resource = RESOURCES[resource_name]
    conn = open_connection(resource["base_url"])
    sample_id = pick_sample_id(conn, resource)
    item_path = f"{resource['list_path']}/{sample_id}"
    cache_key = f"{resource['cache_key_prefix']}:{sample_id}"
    redis_client = Redis(host="localhost", port=6379, db=0)

    print(f"Benchmarking {resource_name} {sample_id} ({NUM_REQUESTS} requests per phase)...")

    cold_times = []
    for _ in range(NUM_REQUESTS):
        redis_client.delete(cache_key)
        cold_times.append(timed_get(conn, item_path))

    timed_get(conn, item_path)  # populate the cache once before timing warm requests
    warm_times = []
    for _ in range(NUM_REQUESTS):
        warm_times.append(timed_get(conn, item_path))

    conn.close()

    avg_cold_ms = (sum(cold_times) / len(cold_times)) * 1000
    avg_warm_ms = (sum(warm_times) / len(warm_times)) * 1000

    print(f"Average without cache (MySQL every time): {avg_cold_ms:.2f} ms")
    print(f"Average with cache warm (Redis hit):       {avg_warm_ms:.2f} ms")
    print(f"Speedup: {avg_cold_ms / avg_warm_ms:.1f}x")


if __name__ == "__main__":
    resource_name = sys.argv[1] if len(sys.argv) > 1 else "flight"
    if resource_name not in RESOURCES:
        raise SystemExit(f"Unknown resource '{resource_name}' - choose 'flight' or 'hotel'")
    benchmark(resource_name)
