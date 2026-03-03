
import requests

API_BASE = "http://localhost:8000"

endpoints = [
    "/transactions?limit=10",
    "/analytics/summary",
    "/market/trends",
    "/ai/advice",
    "/analytics/by-day",
    "/profile",
    "/ai/health-score",
    "/ai/recommendations",
    "/ai/predict/revenue",
    "/ai/predict/expenses"
]

for ep in endpoints:
    try:
        r = requests.get(f"{API_BASE}{ep}")
        print(f"Endpoint: {ep} - Status: {r.status_code}")
        if r.status_code != 200:
            print(f"  Error: {r.text}")
    except Exception as e:
        print(f"Endpoint: {ep} - Failed to connect: {e}")
