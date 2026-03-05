import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

API = "http://localhost:8000"

def test_init_checkout():
    # We need a token. Let's try to login or use a fake one if the backend doesn't validate it strictly (it does).
    # Since I don't have a user, I'll check main_auth.py to see if I can bypass or if I should create one.
    
    # Actually, let's just check if the endpoint exists and what it returns for a bogus token.
    try:
        res = httpx.post(f"{API}/api/paystack/initialize", 
                         headers={"Authorization": "Bearer bogus_token"},
                         json={"planId": "pro"})
        print(f"Status: {res.status_code}")
        print(f"Body: {res.text}")
    except Exception as e:
        print(f"Error connecting: {e}")

if __name__ == "__main__":
    test_init_checkout()
