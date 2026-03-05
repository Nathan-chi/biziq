import httpx
import asyncio
import json

async def test_whatsapp():
    token = "EAAXjYLOKB2EBQ5aLJjKROXfwlnhU5uxd7zfgIpLzEJj0m5l7koZBcVLShs7Ajrb7qpZBT2801kdFBuodDKZBmQb1C3VjKBY7h0T3ZAzhvZAPWh8eL9oKaoWSwV6YP9F6rtvFWvHE2EGuSUTzTjey84y3BBcdZBqWXqnj16IJdp84rnVDq4VKsxG8Xr7z0eoMpZAFmYriWe3abXUYVttinHvNE4gPLmdzmxE81PXJTcbBBsowYpaj6iDWOSUTew6YZAvTRfqLP088cKXp0ENENLsM"
    phone_id = "939835195888737"
    to_phone = "2348077299974"
    
    url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {
                "code": "en_US"
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        print("-" * 20)
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

if __name__ == "__main__":
    asyncio.run(test_whatsapp())
