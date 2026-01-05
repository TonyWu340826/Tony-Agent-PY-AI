import os
import requests
import json

# 测试配置
BASE_URL = "http://127.0.0.1:8889"
TEST_FILE_PATH = r"C:\Users\17867\Desktop\宝塔\demo.txt"

def test_document_upload():
    """
    测试文档上传接口
    """
    print("开始测试文档上传接口...")
    
    # 检查测试文件是否存在
    if not os.path.exists(TEST_FILE_PATH):
        print(f"错误: 测试文件不存在: {TEST_FILE_PATH}")
        return False
    
    # 准备上传参数
    params = {
        'doc_type': '1',
        'doc_subject': '测试文档',
        'org_code': 'TEST1000001',
        'chunk_size': 512
    }
    
    # 准备文件
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': f}
        try:
            response = requests.post(
                f"{BASE_URL}/api/embedding/document/upload",
                params=params,
                files=files
            )
            
            print(f"上传接口响应状态码: {response.status_code}")
            print(f"上传接口响应内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ 文档上传测试成功!")
                    return True
                else:
                    print(f"❌ 文档上传失败: {result.get('message', '未知错误')}")
                    return False
            else:
                print(f"❌ 文档上传请求失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 文档上传请求异常: {str(e)}")
            return False

def test_document_search():
    """
    测试文档搜索接口
    """
    print("\n开始测试文档搜索接口...")
    
    # 准备搜索参数
    search_data = {
        "query": "测试搜索关键词",  # 替换为实际的搜索词
        "org_code": "TEST1000001",
        "top_k": 5
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/embedding/document/search",
            json=search_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"搜索接口响应状态码: {response.status_code}")
        print(f"搜索接口响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 文档搜索测试成功!")
                print(f"返回结果数量: {len(result.get('results', []))}")
                return True
            else:
                print(f"❌ 文档搜索失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ 文档搜索请求失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 文档搜索请求异常: {str(e)}")
        return False

def main():
    """
    主测试函数
    """
    print("开始执行文档向量功能测试...")
    print(f"测试文件路径: {TEST_FILE_PATH}")
    print(f"基础URL: {BASE_URL}")
    
    # 确保服务器正在运行
    try:
        health_check = requests.get(f"{BASE_URL}/docs", timeout=5)
        if health_check.status_code != 200:
            print("⚠️  服务器可能未运行，请先启动服务器")
            return
    except requests.exceptions.ConnectionError:
        print("⚠️  无法连接到服务器，请先启动服务器: python -m uvicorn main:app --reload --port 8889")
        return
    
    # 执行测试
    upload_success = test_document_upload()
    search_success = test_document_search()
    
    # 输出测试结果总结
    print("\n" + "="*50)
    print("测试结果总结:")
    print(f"文档上传: {'✅ 通过' if upload_success else '❌ 失败'}")
    print(f"文档搜索: {'✅ 通过' if search_success else '❌ 失败'}")
    
    if upload_success and search_success:
        print("\n🎉 所有测试通过!")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查服务器日志")
        return False

if __name__ == "__main__":
    main()