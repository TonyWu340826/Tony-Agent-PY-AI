import logging
from typing import List, Dict, Any
import json
import aiohttp
from model.openAI import chat_completion
from config.config import config
import re

'''
分析用户需求，提取意图和参数
'''
async def analyze_user_intent(user_query: str) -> Dict[str, Any]:

    logging.info(f"[第一步]用户需求分析开始：{user_query}")
    """
    分析用户需求，提取意图和参数
    返回：{intent, entities, operations}
    """
    prompt = f"""
    用户查询：{user_query}

    请分析用户意图并提取关键信息：
    1. 主要意图是什么？（如：查询、创建、修改）
    2. 需要哪些关键参数？（如：用户ID、订单号、日期）
    3. 需要哪些操作步骤？

    返回严格的JSON格式：
    {{
        "intent": "主要意图描述",
        "entities": {{"参数名": "参数值或参数类型"}},
        "required_operations": ["操作1", "操作2"],
        "missing_info": ["缺失的参数"]
    }}

    注意事项：
    1. 严格按照上述JSON格式返回结果
    2. 如果某些字段没有相关信息，使用空数组或空对象
    3. 不要添加任何额外的文本或解释
    """

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]


    logging.info(f"用户需求分析请求：{prompt}")
    try:
        reply = await chat_completion(messages)
        # 清理返回的内容，去掉可能的代码格式包装
        cleaned_reply = reply.strip()
        if cleaned_reply.startswith('```json') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[7:-3].strip()
        elif cleaned_reply.startswith('```') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[3:-3].strip()
        # 尝试解析返回的JSON
        return json.loads(cleaned_reply)
    except json.JSONDecodeError:
        # 如果解析失败，返回原始响应和错误信息
        return {
            "intent": "解析失败",
            "entities": {},
            "required_operations": [],
            "missing_info": [],
            "raw_response": reply
        }
    except Exception as e:
        # 处理其他可能的异常
        return {
            "intent": "调用失败",
            "entities": {},
            "required_operations": [],
            "missing_info": [],
            "error": str(e)
        }





'''
AI匹配：根据用户意图选择最合适的接口
'''
async def match_endpoints_with_ai(
        user_intent: Dict[str, Any],
        endpoints: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    logging.info(f"[第三步]AI匹配开始：{user_intent}")
    """
    AI匹配：根据用户意图选择最合适的接口
    返回：匹配的接口列表（带调用参数）
    """
    # 准备接口描述
    endpoints_desc = []
    for i, ep in enumerate(endpoints):
        desc = f"{i + 1}. {ep['method']} {ep['path']} - {ep['summary']}"
        if ep.get('parameters'):
            # 正确提取参数名
            if 'parameter_details' in ep and ep['parameter_details']:
                # 为不同类型的接口提供清晰的参数描述
                params_info = []
                for param_detail in ep['parameter_details']:
                    param_name = param_detail.get('name', '')
                    param_location = param_detail.get('in', '')
                    param_type = param_detail.get('schema', {}).get('type', 'unknown')
                    # 处理复杂类型定义
                    if 'anyOf' in param_detail.get('schema', {}):
                        types = [item.get("type", "unknown") for item in param_detail["schema"]["anyOf"]]
                        param_type = "|".join(types)
                    required_mark = "必需" if param_detail.get('required', False) else "可选"
                    params_info.append(f"{param_name}({param_location}:{param_type},{required_mark})")
                desc += f" (参数: {', '.join(params_info)})"
            else:
                params = ', '.join(ep.get('parameters', []))
                if params:
                    desc += f" (参数: {params})"
        endpoints_desc.append(desc)

    endpoints_text = "\n".join(endpoints_desc)

    prompt = f"""
    用户需求分析：
    - 意图: {user_intent.get('intent', '未知')}
    - 参数: {user_intent.get('entities', {})}
    - 操作: {user_intent.get('required_operations', [])}

    可用接口列表：
    {endpoints_text}

    请选择最匹配的接口，并返回调用计划：
    1. 选择最相关的接口（可多个）
    2. 为每个接口填充参数，参数名必须与接口定义完全一致
    3. 如果需要多个接口，说明调用顺序

    返回严格的JSON格式：
    {{
        "selected_endpoints": [
            {{
                "endpoint_index": 1,
                "call_parameters": {{"user_id": "1"}},
                "reason": "选择理由"
            }}
        ],
        "call_sequence": [1],
        "missing_params": ["参数名"]
    }}

    重要注意事项：
    1. 严格按照上述JSON格式返回结果
    2. endpoint_index对应上面接口列表的序号（从1开始）
    3. call_parameters中的参数名必须与接口定义中的参数名完全一致
       - 仔细查看接口列表中每个接口的参数描述
       - 参数描述格式为: paramName(location:type,required|optional)
       - location可以是path(路径参数)、query(查询参数)、body(请求体参数)、header(头部参数)
       - 必须使用接口定义中确切的参数名，不要使用别名或近似名称
    4. 如果需要从前一个接口结果中获取数据，使用通用占位符"[前一接口结果数据]"
    5. 如果某些字段没有相关信息，使用空数组或空对象
    6. 不要添加任何额外的文本或解释
    """

    messages = [
        {"role": "system", "content": "You are a helpful assistant that matches user intents to API endpoints."},
        {"role": "user", "content": prompt}
    ]

    logging.info(f"AI匹配请求：{prompt}")
    try:
        reply = await chat_completion(messages)
        # 清理返回的内容，去掉可能的代码格式包装
        cleaned_reply = reply.strip()
        if cleaned_reply.startswith('```json') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[7:-3].strip()
        elif cleaned_reply.startswith('```') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[3:-3].strip()
        # 尝试解析返回的JSON
        result = json.loads(cleaned_reply)
        return result
    except json.JSONDecodeError as e:
        # 如果解析失败，返回错误信息
        return {
            "selected_endpoints": [],
            "call_sequence": [],
            "error": "JSON解析失败",
            "raw_response": reply
        }
    except Exception as e:
        # 处理其他可能的异常
        return {
            "selected_endpoints": [],
            "call_sequence": [],
            "error": f"AI调用失败: {str(e)}"
        }





'''
执行单个API调用
'''
async def execute_api_call(endpoint: Dict[str, Any], params: Dict[str, Any], previous_result: Dict[str, Any] = None) -> Dict[str, Any]:
    logging.info(f"[第四步]执行API调用：{endpoint}")
    """
    执行单个API调用
    endpoint: 接口信息
    params: 调用参数
    previous_result: 前一个API调用的结果（用于参数替换）
    """
    try:
        # 直接使用相对路径，避免前缀重复问题
        path = endpoint['path']
        
        # 替换路径参数（路径中的参数）
        path_params = {}
        for key, value in params.items():
            if f"{{{key}}}" in path:
                path = path.replace(f"{{{key}}}", str(value))
                path_params[key] = value
        
        # 如果有前一个结果，处理参数替换
        processed_params = params.copy()
        if previous_result and previous_result.get("success") and previous_result.get("data"):
            # 替换参数中的占位符
            for key, value in processed_params.items():
                if isinstance(value, str) and "[前一接口结果数据]" in value:
                    # 从第一个接口结果中获取最合适的字符串数据
                    user_data = previous_result.get("data", {})
                    replacement = ""
                    if isinstance(user_data, dict):
                        # 查找可能的名称字段，不再硬编码具体字段名
                        replacement = find_first_string_field(user_data, ["name", "username", "user_name", "fullName", "full_name", "title"])
                        # 如果仍然没有找到字符串字段，就用整个字典的字符串表示
                        if not replacement:
                            replacement = str(user_data)
                    else:
                        replacement = str(user_data)
                    processed_params[key] = value.replace("[前一接口结果数据]", replacement)
        
        # 从配置中获取端口号，不再硬编码
        port = config.get("app.port", "8889")
        url = f"http://localhost:{port}{path}"

        logging.info(f"API调用URL：{url}")
        # 发送请求
        method = endpoint["method"].lower()
        logging.info(f"API调用方法：{method}")
        logging.info(f"接收到的参数: {processed_params}")

        # 使用异步HTTP客户端避免阻塞事件循环
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 基于参数的"in"属性分离参数
                query_params = {}
                body_params = {}
                header_params = {}
                
                # 创建参数名到值的映射
                param_values = processed_params
                
                # 根据参数详细信息分离参数
                if "parameter_details" in endpoint:
                    logging.info(f"使用参数详细信息处理参数")
                    for param_detail in endpoint["parameter_details"]:
                        param_name = param_detail["name"]
                        param_location = param_detail["in"]
                        logging.info(f"处理参数: {param_name}, 位置: {param_location}")
                        if param_name in param_values:
                            param_value = param_values[param_name]
                            logging.info(f"参数 {param_name} 的值: {param_value}")
                            if param_location == "path":
                                # 路径参数已在前面处理
                                logging.info(f"参数 {param_name} 是路径参数，已处理")
                                pass
                            elif param_location == "query":
                                query_params[param_name] = param_value
                                logging.info(f"参数 {param_name} 添加到查询参数")
                            elif param_location == "body":
                                body_params[param_name] = param_value
                                logging.info(f"参数 {param_name} 添加到请求体")
                            elif param_location == "header":
                                header_params[param_name] = param_value
                                logging.info(f"参数 {param_name} 添加到头部")
                            else:
                                # 默认情况下，GET请求用查询参数，POST/PUT请求用请求体
                                if method == "get":
                                    query_params[param_name] = param_value
                                elif method in ["post", "put"]:
                                    body_params[param_name] = param_value
                                else:
                                    query_params[param_name] = param_value
                                logging.info(f"参数 {param_name} 使用默认处理方式")
                        else:
                            logging.info(f"参数 {param_name} 不在提供的参数中")
                else:
                    logging.info(f"没有参数详细信息，使用简单规则处理参数")
                    # 如果没有参数详细信息，使用简单规则
                    for param_name, param_value in processed_params.items():
                        if param_name not in path_params:  # 不是路径参数
                            # 特殊处理：对于有requestBody的接口，参数应该放在请求体中
                            if "requestBody" in endpoint and method in ["post", "put"]:
                                body_params[param_name] = param_value
                            elif method == "get":
                                query_params[param_name] = param_value
                            elif method in ["post", "put"]:
                                body_params[param_name] = param_value
                            else:
                                query_params[param_name] = param_value
                # 设置头部信息
                headers = {}
                for header_name, header_value in header_params.items():
                    headers[header_name] = header_value
                
                # 打印调试信息
                logging.info(f"查询参数: {query_params}")
                logging.info(f"请求体参数: {body_params}")
                logging.info(f"头部参数: {header_params}")
                
                # 对于POST/PUT请求，正确处理参数位置
                if method == "get":
                    async with session.get(url, params=query_params, headers=headers) as response:
                        status_code = response.status
                        data = await response.json() if response.content_length else {}
                elif method == "post":
                    # 根据Swagger定义正确处理POST请求参数
                    if body_params:
                        async with session.post(url, params=query_params, json=body_params, headers=headers) as response:
                            status_code = response.status
                            data = await response.json() if response.content_length else {}
                    else:
                        # 如果没有明确的body参数，将所有非路径参数放入body
                        async with session.post(url, params=query_params, json=processed_params, headers=headers) as response:
                            status_code = response.status
                            data = await response.json() if response.content_length else {}
                elif method == "put":
                    # 根据Swagger定义正确处理PUT请求参数
                    if body_params:
                        async with session.put(url, params=query_params, json=body_params, headers=headers) as response:
                            status_code = response.status
                            data = await response.json() if response.content_length else {}
                    else:
                        # 如果没有明确的body参数，将所有非路径参数放入body
                        async with session.put(url, params=query_params, json=processed_params, headers=headers) as response:
                            status_code = response.status
                            data = await response.json() if response.content_length else {}
                elif method == "delete":
                    async with session.delete(url, params=query_params, headers=headers) as response:
                        status_code = response.status
                        data = await response.json() if response.content_length else {}
                else:
                    return {"success": False, "error": f"不支持的HTTP方法: {method}"}
                
            logging.info(f"[第四步]API调用结果：状态码 {status_code}")
            return {
                "success": True,
                "status_code": status_code,
                "data": data,
                "endpoint": endpoint["path"]
            }
        except Exception as e:
            logging.error(f"API调用失败：{e}")
            return {"success": False, "error": str(e), "endpoint": endpoint["path"]}
        
    except Exception as e:
        return {"success": False, "error": str(e), "endpoint": endpoint["path"]}

# 辅助函数：查找第一个字符串类型的字段
def find_first_string_field(data_dict: Dict[str, Any], priority_fields: List[str] = None) -> str:
    """
    从字典中查找第一个字符串类型的字段
    
    Args:
        data_dict: 要搜索的字典
        priority_fields: 优先查找的字段名列表
        
    Returns:
        找到的字符串值，如果没找到返回空字符串
    """
    if not isinstance(data_dict, dict):
        return ""
    
    # 首先按优先级查找指定字段
    if priority_fields:
        for field in priority_fields:
            if field in data_dict and isinstance(data_dict[field], str):
                return str(data_dict[field])
    
    # 如果没找到优先字段，查找第一个字符串类型的字段
    for key, value in data_dict.items():
        if isinstance(value, str):
            return value
            
    return ""
