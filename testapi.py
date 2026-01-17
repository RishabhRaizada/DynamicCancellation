# import requests

# def get_anonymous_token():
#     url = "https://dotrezapi.test.6e.navitaire.com/api/auth/v1-beta/token/anonymous"
    
#     headers = {
#         "accept": "application/json",
#         "Content-Type": "application/json"
#     }
    
#     payload = {
#         "applicationName": "IndiGoUAT",
#         "cultureCode": "en-IN",
#         "newSession": True
#     }
    
#     response = requests.post(url, json=payload, headers=headers, timeout=30)
    
#     if response.status_code != 200:
#         raise Exception(f"Token request failed: {response.status_code} - {response.text}")
    
#     data = response.json()
#     return data["token"]   # short-lived anonymous JWT
import requests

try:
    r = requests.get("https://dotrezapi.test.6e.navitaire.com/health", timeout=10)
    print("Reachable:", r.status_code)
except Exception as e:
    print("Connection error:", e)
