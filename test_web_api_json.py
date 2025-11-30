"""测试 Web API 的 JSON 请求"""
import requests
import json

url = "http://localhost:5000/api/start-generation"

data = {
    "title": "测试小说",
    "synopsis": "测试剧情",
    "core_setting": "测试设定",
    "core_selling_points": ["测试卖点"],
    "total_chapters": 1
}

headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json"
}

print(f"Sending request to {url}")
print(f"Data: {json.dumps(data, ensure_ascii=False)}")

try:
    response = requests.post(url, json=data, headers=headers)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
