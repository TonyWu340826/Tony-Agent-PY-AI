import requests
import json
import time

def test_workflow_directly(query):
    """直接测试工作流引擎"""
    print(f"\n=== 测试查询: {query} ===")
    
    response = requests.post(
        "http://localhost:8889/api/chat/active/chat",
        json={
            "query": query
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"成功: {result.get('success', False)}")
        
        # 打印执行结果
        execution_results = result.get('execution_results', [])
        for i, res in enumerate(execution_results, 1):
            print(f"  步骤{i}: {res.get('endpoint', 'Unknown')} - 状态码 {res.get('status_code', 'N/A')}")
            if res.get('success'):
                data = res.get('data', {})
                # 如果数据太大，只显示前100个字符
                data_str = json.dumps(data, ensure_ascii=False)
                if len(data_str) > 100:
                    data_str = data_str[:100] + "..."
                print(f"    数据: {data_str}")
            else:
                print(f"    错误: {res.get('error', 'Unknown')}")
    else:
        print(f"错误: {response.text}")
    
    return response

def main():
    """主测试函数"""
    print("=== 工作流引擎测试 ===")
    
    # 测试不同复杂度的工作流
    test_cases = [
        # 单步骤工作流
        "查询ID为1的用户信息",
        
        # 双步骤工作流
        "查询ID为1的用户信息，然后分析用户名'云杉'的文化内涵",
        
        # 多步骤工作流
        "查询ID为1的用户信息，然后获取所有用户列表",
        
        # 复杂工作流 - 这个可能需要特殊处理
        "查询ID为2的用户信息"
    ]
    
    for i, query in enumerate(test_cases, 1):
        test_workflow_directly(query)
        # 添加延迟避免请求过快
        if i < len(test_cases):
            time.sleep(1)
    
    print("\n=== 所有测试完成 ===")

if __name__ == "__main__":
    main()