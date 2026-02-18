import requests

url = "http://127.0.0.1:5000/chat"

data = {
    "message": "I feel overwhelmed with my tasks today.",
    "condition": "safety"  # or 'default'
}

response = requests.post(url, json=data)
print(response.json())
