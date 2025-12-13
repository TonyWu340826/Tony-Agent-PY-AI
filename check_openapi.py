import requests
import json

url = "http://localhost:8889/openapi.json"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Keys in openapi.json: {list(data.keys())}")
    
    # 检查paths字段
    if "paths" in data:
        print(f"Number of paths: {len(data['paths'])}")
        # 显示前几个路径
        paths = list(data["paths"].keys())[:5]
        print(f"First 5 paths: {paths}")
        
        # 检查第一个路径的详细信息
        if paths:
            first_path = paths[0]
            print(f"\nDetails of first path '{first_path}':")
            print(json.dumps(data["paths"][first_path], indent=2, ensure_ascii=False))
    else:
        print("No 'paths' key found in openapi.json")
        
    # 检查info字段
    if "info" in data:
        print(f"\nInfo section: {data['info']}")
    else:
        print("No 'info' key found in openapi.json")
        
except Exception as e:
    print(f"Error: {e}")