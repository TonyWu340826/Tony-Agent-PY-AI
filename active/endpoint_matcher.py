import logging
from typing import List, Dict, Any
import json
import aiohttp
from model.openAI import chat_completion
from config.config import config
import re
import sys  # 添加sys导入
import os   # 添加os导入


# 从配置文件读取AI提示词配置
AI_INTENT_CONFIG = config.get("ai_intent_analysis", {})
AI_ENDPOINT_CONFIG = config.get("ai_endpoint_matching", {})
COMMON_INTENTS = config.get("common_intents", [])
KEY_PARAMETERS = config.get("key_parameters", [])


'''
分析用户需求，提取意图和参数
'''
async def analyze_user_intent(user_query: str) -> Dict[str, Any]:

    logging.info(f"[第一步]用户需求分析开始：{user_query}")
    """
    分析用户需求，提取意图和参数
    返回：{intent, entities, operations}
    """
    # 从配置文件获取提示词模板
    prompt_template = AI_INTENT_CONFIG.get("user_prompt_template", "")
    # 从配置文件获取常见意图和参数示例
    common_intents = ", ".join(AI_INTENT_CONFIG.get("common_intents", []))
    key_parameters = ", ".join(AI_INTENT_CONFIG.get("key_parameters", []))

    # 构建完整的提示词，避免双重花括号问题
    # 先替换配置中的变量
    full_prompt = prompt_template.replace("{user_query}", user_query)
    full_prompt = full_prompt.replace("{common_intents}", common_intents)
    full_prompt = full_prompt.replace("{key_parameters}", key_parameters)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that analyzes user queries and extracts intent and key parameters."
        },
        {
            "role": "user",
            "content": full_prompt
        }
    ]

    try:
        reply = await chat_completion(messages)
        # 清理返回的内容
        cleaned_reply = reply.strip()
        if cleaned_reply.startswith('```json') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[7:-3].strip()
        elif cleaned_reply.startswith('```') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[3:-3].strip()

        result = json.loads(cleaned_reply)
        logging.info(f"[第一步]用户需求分析结果：{result}")
        return result
    except Exception as e:
        logging.error(f"[第一步]用户需求分析失败：{e}")
        # 返回默认结果
        return {
            "intent": "未知",
            "entities": {},
            "required_operations": [],
            "missing_info": []
        }


'''
AI匹配接口
'''
async def match_endpoints_with_ai(user_intent: Dict[str, Any], endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    logging.info("[第三步]AI匹配开始")
    
    # 准备接口描述
    endpoints_desc = []
    for i, ep in enumerate(endpoints):
        desc = f"{i + 1}. {ep['method']} {ep['path']} - {ep['summary']}"
        if ep.get('parameters'):
            if 'parameter_details' in ep and ep['parameter_details']:
                params_info = []
                for param_detail in ep['parameter_details']:
                    param_name = param_detail.get('name', '')
                    param_location = param_detail.get('in', '')
                    param_type = param_detail.get('schema', {}).get('type', 'unknown')
                    if 'anyOf' in param_detail.get('schema', {}):
                        types = [item.get("type", "unknown") for item in param_detail["schema"]["anyOf"]]
                        param_type = "|".join(types)
                    required_mark = "必需" if param_detail.get('required', False) else "可选"
                    # 特殊处理additionalProperties标记
                    if param_name == "_additionalPropertiesBody":
                        params_info.append(f"任意JSON对象(body:object,必需)")
                    else:
                        params_info.append(f"{param_name}({param_location}:{param_type},{required_mark})")
                desc += f" (参数: {', '.join(params_info)})"
            else:
                params = ', '.join(ep.get('parameters', []))
                if params:
                    desc += f" (参数: {params})"
        endpoints_desc.append(desc)
    
    endpoints_text = "\n".join(endpoints_desc)
    
    # 构建提示词
    prompt = f"""
用户需求分析：
- 意图: {user_intent.get('intent', '未知')}
- 参数: {user_intent.get('entities', {})}
- 操作: {user_intent.get('required_operations', [])}

可用接口列表：
{endpoints_text}

请根据用户需求，选择最适合的接口并提供调用参数。
注意事项：
1. 对于一般性咨询问题，优先考虑使用大模型接口（如 /api/open/chat, /api/open/deeoSeekChat/model 等）
2. 对于具体业务操作，选择对应的功能接口
3. 如果用户需求涉及多个操作，可以按顺序选择多个接口
4. 为每个选定的接口提供具体的调用参数
5. 特别注意分页参数（page, size）应该是整数类型
6. 搜索参数应该是字符串类型

返回严格的JSON格式：
{{
    "selected_endpoints": [
        {{
            "endpoint_index": 1,
            "call_parameters": {{"param1": "value1"}},
            "reason": "选择理由"
        }}
    ],
    "call_sequence": [1],
    "missing_params": []
}}
"""

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that matches user requirements to API endpoints."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:
        reply = await chat_completion(messages)
        # 清理返回的内容
        cleaned_reply = reply.strip()
        if cleaned_reply.startswith('```json') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[7:-3].strip()
        elif cleaned_reply.startswith('```') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[3:-3].strip()
            
        result = json.loads(cleaned_reply)
        logging.info(f"[第三步]AI匹配结果：{result}")
        return result
    except Exception as e:
        logging.error(f"[第三步]AI匹配失败：{e}")
        # 返回默认结果
        return {
            "selected_endpoints": [],
            "call_sequence": [],
            "missing_params": []
        }


async def execute_api_call(
    endpoint: Dict[str, Any], 
    params: Dict[str, Any] = None,
    previous_result: Dict[str, Any] = None,
    api_url: str = None,
    auth_headers: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    执行API调用
    
    Args:
        endpoint: 接口信息
        params: 调用参数
        previous_result: 上一个调用的结果，用于链式调用
        api_url: API基础URL
        auth_headers: 授权头部信息
        
    Returns:
        调用结果
    """
    logging.info(f"[API调用] 开始执行API调用")
    logging.info(f"  接口: {endpoint.get('method')} {endpoint.get('path')}")
    logging.info(f"  描述: {endpoint.get('summary')}")
    logging.info(f"  服务器: {endpoint.get('server', '默认服务器')}")
    
    try:
        path = endpoint.get("path", "")
        method = endpoint.get("method", "get").lower()

        if api_url is None:
            api_url = endpoint.get("service_base_urls.service", "http://localhost:9876")
        
        # 构建完整URL，处理路径参数替换
        url = api_url + path
        # 替换路径中的参数占位符
        if params:
            for param_name, param_value in params.items():
                placeholder = "{%s}" % param_name
                if placeholder in url:
                    # 对于路径参数，需要进行URL编码
                    import urllib.parse
                    encoded_value = urllib.parse.quote(str(param_value))
                    url = url.replace(placeholder, encoded_value)
        logging.info(f"  完整URL: {url}")
        logging.info(f"  HTTP方法: {method.upper()}")
        logging.info(f"  接收参数: {params}")
        
        # 处理参数
        query_params = {}
        body_params = {}
        headers = {}
        
        # 添加授权头部信息
        if auth_headers:
            headers.update(auth_headers)
        
        # 如果有上一个调用的结果，尝试从中提取有用信息
        if previous_result and previous_result.get("success"):
            prev_data = previous_result.get("data", {})
            # 如果上一个调用返回了token或类似信息，可以添加到headers中
            if isinstance(prev_data, dict):
                # 查找可能的认证信息
                auth_keys = ["token", "auth", "authorization", "access_token"]
                for key in auth_keys:
                    if key in prev_data:
                        headers["Authorization"] = f"Bearer {prev_data[key]}"
                        break
        
        # 处理参数详细信息
        if "parameter_details" in endpoint and endpoint["parameter_details"]:
            logging.info("  使用参数详细信息处理参数")
            for param_detail in endpoint["parameter_details"]:
                param_name = param_detail.get("name")
                param_location = param_detail.get("in")
                param_required = param_detail.get("required", False)
                
                # 特殊处理additionalProperties标记
                if param_name == "_additionalPropertiesBody":
                    logging.info(f"    处理参数: {param_name}, 位置: {param_location}")
                    if param_location == "body":
                        # 将所有参数放入请求体
                        if params:
                            body_params.update(params)
                            logging.info(f"    通用处理additionalProperties，将所有参数放入请求体: {params}")
                        continue
                
                # 检查参数是否在提供的参数中
                if param_name in (params or {}):
                    param_value = params[param_name]
                    logging.info(f"    处理参数: {param_name}, 位置: {param_location}, 值: {param_value}")
                    
                    # 特殊处理分页参数，确保它们是整数类型
                    if param_name in ["page", "size"] and isinstance(param_value, str):
                        try:
                            param_value = int(param_value)
                        except ValueError:
                            # 如果转换失败，使用默认值或0
                            param_value = 0 if param_name == "page" else 10
                    
                    if param_location == "query":
                        query_params[param_name] = param_value
                    elif param_location == "body":
                        body_params[param_name] = param_value
                    elif param_location == "header":
                        headers[param_name] = param_value
                    elif param_location == "path":
                        # 路径参数已经在URL中处理过了，但需要从查询参数中移除
                        if param_name in query_params:
                            del query_params[param_name]
                else:
                    logging.info(f"    参数 {param_name} 不在提供的参数中")
                    # 检查是否有默认值
                    default_value = param_detail.get("schema", {}).get("default")
                    if default_value is not None:
                        logging.info(f"    使用默认值 {default_value} 作为参数 {param_name} 的值")
                        if param_location == "query":
                            query_params[param_name] = default_value
                        elif param_location == "body":
                            body_params[param_name] = default_value
                        elif param_location == "header":
                            headers[param_name] = default_value
        else:
            # 如果没有参数详细信息，使用简单处理方式
            logging.info("  使用简单参数处理方式")
            if params:
                # 尝试智能分配参数到查询参数和请求体
                for key, value in params.items():
                    # 简单规则：数字和小的值可能是查询参数，大的字符串可能是请求体
                    if isinstance(value, (int, float)) or (isinstance(value, str) and len(value) < 50):
                        query_params[key] = value
                    else:
                        body_params[key] = value
        
        logging.info(f"  查询参数: {query_params}")
        logging.info(f"  请求体参数: {body_params}")
        logging.info(f"  头部参数: {headers}")
        if auth_headers:
            logging.info(f"  授权头部: {auth_headers}")
        
        # 执行HTTP请求 - 使用更安全的连接方式
        # 创建connector时避免使用可能导致问题的参数
        # 为Python 3.13兼容性，避免使用可能引起问题的参数
        # 使用更简单的连接器配置来避免Python 3.13兼容性问题
        # 移除可能在Python 3.13中引起问题的eager_start参数
        if sys.version_info >= (3, 13):
            # 在Python 3.13中避免使用eager_start参数
            os.environ["PYTHONASYNCIOTASKS"] = "0"
            
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30, ttl_dns_cache=300, use_dns_cache=True)
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            status_code = 500
            data = {}
            
            try:
                if method == "get":
                    async with session.get(url, params=query_params, headers=headers) as response:
                        status_code = response.status
                        # 尝试解析响应内容
                        try:
                            # 始终尝试读取响应内容
                            raw_text = await response.text()
                            if raw_text and raw_text.strip():
                                try:
                                    data = json.loads(raw_text)
                                except json.JSONDecodeError:
                                    data = {"text": raw_text, "parse_error": "JSON decode failed"}
                            else:
                                data = {}
                        except:
                            data = {"error": "Failed to read response"}
                elif method == "post":
                    # 根据Swagger定义正确处理POST请求参数
                    if body_params:
                        async with session.post(url, params=query_params, json=body_params, headers=headers) as response:
                            status_code = response.status
                            # 尝试解析响应内容
                            try:
                                # 始终尝试读取响应内容
                                raw_text = await response.text()
                                if raw_text and raw_text.strip():
                                    try:
                                        data = json.loads(raw_text)
                                    except json.JSONDecodeError:
                                        data = {"text": raw_text, "parse_error": "JSON decode failed"}
                                else:
                                    data = {}
                            except:
                                data = {"error": "Failed to read response"}
                    else:
                        # 如果没有明确的body参数，将所有非路径参数放入body
                        async with session.post(url, params=query_params, json=params, headers=headers) as response:
                            status_code = response.status
                            # 尝试解析响应内容
                            try:
                                # 始终尝试读取响应内容
                                raw_text = await response.text()
                                if raw_text and raw_text.strip():
                                    try:
                                        data = json.loads(raw_text)
                                    except json.JSONDecodeError:
                                        data = {"text": raw_text, "parse_error": "JSON decode failed"}
                                else:
                                    data = {}
                            except:
                                data = {"error": "Failed to read response"}
                elif method == "put":
                    # 根据Swagger定义正确处理PUT请求参数
                    if body_params:
                        async with session.put(url, params=query_params, json=body_params, headers=headers) as response:
                            status_code = response.status
                            # 尝试解析响应内容
                            try:
                                # 始终尝试读取响应内容
                                raw_text = await response.text()
                                if raw_text and raw_text.strip():
                                    try:
                                        data = json.loads(raw_text)
                                    except json.JSONDecodeError:
                                        data = {"text": raw_text, "parse_error": "JSON decode failed"}
                                else:
                                    data = {}
                            except:
                                data = {"error": "Failed to read response"}
                    else:
                        # 如果没有明确的body参数，将所有非路径参数放入body
                        async with session.put(url, params=query_params, json=params, headers=headers) as response:
                            status_code = response.status
                            # 尝试解析响应内容
                            try:
                                # 始终尝试读取响应内容
                                raw_text = await response.text()
                                if raw_text and raw_text.strip():
                                    try:
                                        data = json.loads(raw_text)
                                    except json.JSONDecodeError:
                                        data = {"text": raw_text, "parse_error": "JSON decode failed"}
                                else:
                                    data = {}
                            except:
                                data = {"error": "Failed to read response"}
                elif method == "delete":
                    async with session.delete(url, params=query_params, headers=headers) as response:
                        status_code = response.status
                        # 尝试解析响应内容
                        try:
                            # 始终尝试读取响应内容
                            raw_text = await response.text()
                            if raw_text and raw_text.strip():
                                try:
                                    data = json.loads(raw_text)
                                except json.JSONDecodeError:
                                    data = {"text": raw_text, "parse_error": "JSON decode failed"}
                            else:
                                data = {}
                        except:
                            data = {"error": "Failed to read response"}
                else:
                    return {"success": False, "error": f"不支持的HTTP方法: {method}"}
                
            except Exception as e:
                logging.error(f"  HTTP请求执行失败: {e}")
                return {"success": False, "error": str(e), "endpoint": endpoint["path"]}
                
            logging.info(f"[API调用完成] API调用结果")
            logging.info(f"  状态码: {status_code}")
            logging.info(f"  响应数据类型: {type(data).__name__}")
            if isinstance(data, dict):
                if 'content' in data:
                    logging.info(f"  响应数据条数: {len(data.get('content', []))}")
                if 'totalElements' in data:
                    logging.info(f"  总元素数: {data.get('totalElements')}")
                if 'totalPages' in data:
                    logging.info(f"  总页数: {data.get('totalPages')}")
                if 'number' in data:
                    logging.info(f"  当前页码: {data.get('number')}")
            
            # 构建返回结果
            result = {
                "success": status_code < 400,  # 状态码小于400才认为成功
                "status_code": status_code,
                "data": data,
                "endpoint": endpoint["path"]
            }
            
            # 如果调用失败，返回详细的错误信息供AI分析
            if status_code >= 400:
                result["error_details"] = {
                    "request": {
                        "url": url,
                        "method": method,
                        "query_params": query_params,
                        "body_params": body_params,
                        "headers": dict(headers) if headers else {}
                    },
                    "response": {
                        "status_code": status_code,
                        "data": data
                    }
                }
                
            return result
    except Exception as e:
        logging.error(f"[API调用异常] API调用失败: {e}")
        return {"success": False, "error": str(e), "endpoint": endpoint["path"]}


async def analyze_api_error_and_retry(
    endpoint: Dict[str, Any], 
    params: Dict[str, Any], 
    error_result: Dict[str, Any],
    endpoints_list: List[Dict[str, Any]],
    api_url: str = None,
    auth_headers: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    分析API调用错误并尝试重新规划调用
    
    Args:
        endpoint: 原始接口信息
        params: 原始调用参数
        error_result: 错误结果
        endpoints_list: 所有可用接口列表
        api_url: API基础URL
        auth_headers: 授权头部信息
        
    Returns:
        重新规划后的调用结果或最终错误结果
    """
    logging.info(f"[AI错误分析] 开始分析API调用错误")
    logging.info(f"  接口: {endpoint.get('method')} {endpoint.get('path')}")
    logging.info(f"  原始参数: {params}")
    logging.info(f"  错误状态码: {error_result.get('status_code', 'N/A')}")
    logging.info(f"  错误成功标识: {error_result.get('success', 'N/A')}")
    
    # 构建错误分析提示词
    error_info = {
        "original_endpoint": endpoint,
        "original_params": params,
        "error_details": error_result.get("error_details", {}),
        "error_message": error_result.get("data", {}).get("message", "Unknown error")
    }
    
    # 准备接口描述（用于重新规划）
    endpoints_desc = []
    for i, ep in enumerate(endpoints_list):
        desc = f"{i + 1}. {ep['method']} {ep['path']} - {ep['summary']}"
        if ep.get('parameters'):
            if 'parameter_details' in ep and ep['parameter_details']:
                params_info = []
                for param_detail in ep['parameter_details']:
                    param_name = param_detail.get('name', '')
                    param_location = param_detail.get('in', '')
                    param_type = param_detail.get('schema', {}).get('type', 'unknown')
                    if 'anyOf' in param_detail.get('schema', {}):
                        types = [item.get("type", "unknown") for item in param_detail["schema"]["anyOf"]]
                        param_type = "|".join(types)
                    required_mark = "必需" if param_detail.get('required', False) else "可选"
                    # 特殊处理additionalProperties标记
                    if param_name == "_additionalPropertiesBody":
                        params_info.append(f"任意JSON对象(body:object,必需)")
                    else:
                        params_info.append(f"{param_name}({param_location}:{param_type},{required_mark})")
                desc += f" (参数: {', '.join(params_info)})"
            else:
                params = ', '.join(ep.get('parameters', []))
                if params:
                    desc += f" (参数: {params})"
        endpoints_desc.append(desc)
    
    endpoints_text = "\n".join(endpoints_desc)
    
    # 构建详细的错误信息用于AI分析
    detailed_error_info = {
        "original_request": {
            "endpoint": f"{endpoint.get('method')} {endpoint.get('path')}",
            "parameters": params
        },
        "response": error_result
    }
    
    # 如果是分页相关的空数据，提供更详细的上下文信息
    data = error_result.get("data", {})
    if isinstance(data, dict) and "content" in data and "totalElements" in data:
        detailed_error_info["pagination_context"] = {
            "current_page": data.get("number"),
            "total_pages": data.get("totalPages"),
            "total_elements": data.get("totalElements"),
            "elements_in_current_page": len(data.get("content", [])),
            "is_empty_page": len(data.get("content", [])) == 0
        }
    
    # 构建错误分析提示词
    error_analysis_prompt = f"""
API调用失败分析：

原始请求信息：
- 接口: {endpoint.get('method')} {endpoint.get('path')}
- 参数: {json.dumps(params, ensure_ascii=False, indent=2)}

响应结果：
{json.dumps(error_result, ensure_ascii=False, indent=2)}

详细错误上下文：
{json.dumps(detailed_error_info, ensure_ascii=False, indent=2)}

可用接口列表：
{endpoints_text}

请分析错误原因并提供修正后的调用计划：
1. 详细分析错误原因（如参数名错误、参数格式问题、分页问题、认证问题等）
2. 如果是分页问题，请特别注意：
   - page参数从0开始计数
   - 如果总共有N页，有效的页码范围是0到N-1
   - 如果请求的页码超出范围，应该调整为有效页码
   - 如果当前页没有数据但总元素数大于0，可能需要调整页码
3. 如果是参数类型问题，请确保参数类型与接口定义一致
4. 如果原接口仍有问题，请选择其他合适的接口
5. 提供修正后的参数和选择理由

返回严格的JSON格式：
{{
    "analysis": "详细的错误原因分析，包括为什么会出现这个问题以及如何解决",
    "retry_plan": {{
        "endpoint_index": 1,
        "call_parameters": {{"corrected_param": "value"}},
        "reason": "为什么要这样修改参数或选择这个接口"
    }},
    "should_retry": true/false
}}
"""
    system_prompt = """You are a helpful assistant that analyzes API call failures and suggests corrections. Based on the error information, you should identify the root cause and provide a corrected calling plan. 

Important guidelines:
1. Always pay special attention to pagination issues where page numbers start from 0 and should be within valid range
2. For empty results with totalElements > 0, suggest adjusting page parameters
3. Make sure parameter types match the API specification
4. Provide detailed analysis of why the error occurred and how to fix it
5. Only suggest retry if you believe the issue can be fixed, otherwise recommend not to retry"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": error_analysis_prompt}
    ]
    
    try:
        logging.info(f"[AI错误分析] 发送错误分析请求到AI")
        logging.debug(f"错误分析提示词: {error_analysis_prompt}")  # 记录详细的错误分析提示词
        reply = await chat_completion(messages)
        
        # 清理返回的内容
        cleaned_reply = reply.strip()
        if cleaned_reply.startswith('```json') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[7:-3].strip()
        elif cleaned_reply.startswith('```') and cleaned_reply.endswith('```'):
            cleaned_reply = cleaned_reply[3:-3].strip()
            
        # 解析AI返回的分析结果
        analysis_result = json.loads(cleaned_reply)
        logging.info(f"[AI错误分析] AI分析完成")
        logging.info(f"  AI分析结果: {json.dumps(analysis_result, ensure_ascii=False, indent=2)}")
        
        # 记录详细的分析结果到日志
        logging.info(f"  错误分析详情 - 原始请求: {detailed_error_info.get('original_request')}")
        logging.info(f"  错误分析详情 - 响应结果: {detailed_error_info.get('response')}")
        logging.info(f"  错误分析详情 - 分页上下文: {detailed_error_info.get('pagination_context', 'N/A')}")
        
        # 如果AI建议重试
        if analysis_result.get("should_retry", False):
            retry_plan = analysis_result.get("retry_plan", {})
            endpoint_index = retry_plan.get("endpoint_index", 0)
            
            # 确保索引有效
            if 1 <= endpoint_index <= len(endpoints_list):
                selected_endpoint = endpoints_list[endpoint_index - 1]
                call_parameters = retry_plan.get("call_parameters", {})
                
                logging.info(f"[AI错误分析] AI建议重试")
                logging.info(f"  重试接口: {selected_endpoint.get('method')} {selected_endpoint.get('path')}")
                logging.info(f"  重试参数: {call_parameters}")
                logging.info(f"  重试理由: {retry_plan.get('reason', 'N/A')}")
                
                # 执行重试调用
                retry_result = await execute_api_call(selected_endpoint, call_parameters, None, api_url, auth_headers)
                logging.info(f"[AI错误分析] 重试调用完成")
                logging.info(f"  重试结果: {'成功' if retry_result.get('success') else '失败'}")
                return retry_result
            else:
                logging.warning(f"[AI错误分析] 无效的接口索引: {endpoint_index}")
                return error_result
        else:
            # AI认为不应该重试，返回原始错误
            logging.info(f"[AI错误分析] AI建议不重试，返回原始错误结果")
            return error_result
            
    except json.JSONDecodeError as e:
        logging.error(f"[AI错误分析] AI返回结果JSON解析失败: {e}")
        logging.error(f"AI原始返回内容: {reply}")
        return error_result
    except Exception as e:
        logging.error(f"[AI错误分析] AI分析失败: {e}")
        logging.exception(e)  # 记录完整的异常堆栈
        return error_result


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