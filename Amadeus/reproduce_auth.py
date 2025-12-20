import requests
import sys

BASE_URL = "http://localhost:8080"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind4dW5rb3ZlbWJ5Znllb2NkeG5oIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjE0NzQyNSwiZXhwIjoyMDc3NzIzNDI1fQ.Kkt1hED9jlXILTpgdg4hGnckiRZroXW3_n_lJt_BI88"

def test_health():
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error testing /health: {e}")

def test_auth():
    print("\nTesting /user/info endpoint with token...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        response = requests.get(f"{BASE_URL}/user/info", headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error testing /user/info: {e}")

if __name__ == "__main__":
    test_health()
    test_auth()
