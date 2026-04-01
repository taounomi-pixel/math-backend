import requests

def test_register():
    url = "http://localhost:8000/api/register"
    payload = {
        "username": "test_unbound_user",
        "password": "testpassword123",
        "email": "test@example.com"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Note: This requires the server to be running locally at port 8000.
    test_register()
