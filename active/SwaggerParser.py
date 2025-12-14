import aiohttp
import asyncio
from typing import List, Dict, Any
import logging
import os  # 添加os导入


class SwaggerParser:
    """解析Swagger文档，提取接口信息"""

    @staticmethod
    async def parse_swagger(swagger_url: str) -> List[Dict[str, Any]]:
        logging.info("[第二步]开始解析Swagger文档")
        """
        解析Swagger文档，返回接口列表
        返回格式：
        [
            {
                "service": "服务名",
                "path": "/users/{id}",
                "method": "GET",
                "summary": "接口描述",
                "parameters": ["id"],
                "required_params": ["id"],
                "operation_id": "getUserById"
            }
        ]
        """
        try:
            logging.info(f"开始解析Swagger文档: {swagger_url}")
            # 使用异步HTTP客户端，设置适当的超时
            # 为Python 3.13兼容性，避免使用可能引起问题的参数
            connector_kwargs = {
                "limit": 100,
                "limit_per_host": 30,
                "ttl_dns_cache": 300,
                "use_dns_cache": True
            }
            
            # 移除可能在Python 3.13中引起问题的eager_start参数
            import sys
            if sys.version_info >= (3, 13):
                # 在Python 3.13中避免使用eager_start参数
                os.environ["PYTHONASYNCIOTASKS"] = "0"
                if "eager_start" in connector_kwargs:
                    del connector_kwargs["eager_start"]
            
            timeout = aiohttp.ClientTimeout(total=300)
            # 使用更简单的连接器配置来避免Python 3.13兼容性问题
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30, ttl_dns_cache=300, use_dns_cache=True)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(swagger_url) as response:
                    response.raise_for_status()
                    data = await response.json()
            logging.info(f"成功获取Swagger文档，共{len(data.get('paths', {}))}个路径")

            # 提取服务名
            service_name = data.get("info", {}).get("title", "unknown")
            
            # 获取组件定义
            components = data.get("components", {})
            schemas = components.get("schemas", {})

            # 解析接口
            endpoints = []
            paths_data = data.get("paths", {})
            
            logging.info(f"发现 {len(paths_data)} 个路径定义")
            
            for path, methods in paths_data.items():
                logging.debug(f"处理路径: {path}")
                for method, details in methods.items():
                    logging.debug(f"  方法: {method}")
                    # 移除HTTP方法的限制，接受所有HTTP方法
                    # if method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
                    #     continue

                    endpoint = {
                        "service": service_name,
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": [],
                        "required_params": [],
                        "operation_id": details.get("operationId", ""),
                        "parameter_details": []  # 添加参数详细信息
                    }

                    # 提取查询参数和路径参数
                    for param in details.get("parameters", []):
                        param_name = param.get("name", "")
                        if param_name:
                            endpoint["parameters"].append(param_name)
                            if param.get("required", False):
                                endpoint["required_params"].append(param_name)
                            # 添加参数详细信息
                            endpoint["parameter_details"].append({
                                "name": param_name,
                                "in": param.get("in", ""),
                                "required": param.get("required", False),
                                "schema": param.get("schema", {}),
                                "description": param.get("description", "")
                            })

                    # 提取请求体参数 (requestBody)
                    if "requestBody" in details:
                        content = details["requestBody"].get("content", {})
                        for content_type, content_details in content.items():
                            if "schema" in content_details:
                                schema = content_details["schema"]
                                # 如果是引用模式，解析引用的模型
                                if "$ref" in schema:
                                    # 解析引用路径 #/components/schemas/UserUpdate
                                    ref_path = schema["$ref"]
                                    if ref_path.startswith("#/components/schemas/"):
                                        schema_name = ref_path.split("/")[-1]
                                        if schema_name in schemas:
                                            schema_def = schemas[schema_name]
                                            # 提取模型属性作为参数
                                            if "properties" in schema_def:
                                                for prop_name, prop_schema in schema_def["properties"].items():
                                                    endpoint["parameters"].append(prop_name)
                                                    # requestBody中的参数标记为body位置
                                                    endpoint["parameter_details"].append({
                                                        "name": prop_name,
                                                        "in": "body",
                                                        "required": prop_name in schema_def.get("required", []),
                                                        "schema": prop_schema,
                                                        "description": prop_schema.get("description", "")
                                                    })
                                elif "properties" in schema:
                                    # 直接定义的属性
                                    for prop_name, prop_schema in schema["properties"].items():
                                        endpoint["parameters"].append(prop_name)
                                        # requestBody中的参数标记为body位置
                                        endpoint["parameter_details"].append({
                                            "name": prop_name,
                                            "in": "body",
                                            "required": prop_name in schema.get("required", []),
                                            "schema": prop_schema,
                                            "description": prop_schema.get("description", "")
                                        })
                                elif "additionalProperties" in schema:
                                    # 处理additionalProperties的情况
                                    # 对于接受任意属性的对象，我们标记它以便后续处理
                                    endpoint["parameter_details"].append({
                                        "name": "_additionalPropertiesBody",
                                        "in": "body",
                                        "required": details["requestBody"].get("required", False),
                                        "schema": schema,
                                        "description": "Request body accepting arbitrary properties"
                                    })

                    # 添加服务器信息（如果有）
                    if "servers" in details and details["servers"]:
                        endpoint["server"] = details["servers"][0].get("url", "")
                    elif "servers" in data and data["servers"]:
                        endpoint["server"] = data["servers"][0].get("url", "")

                    endpoints.append(endpoint)
            
            logging.info(f"解析完成，共找到{len(endpoints)}个接口端点")
            return endpoints

        except asyncio.TimeoutError:
            print(f"解析Swagger失败: 请求 {swagger_url} 超时")
            return []
        except aiohttp.ClientError as e:
            print(f"解析Swagger失败: 请求 {swagger_url} 出错: {e}")
            return []
        except ValueError as e:
            print(f"解析Swagger失败: JSON解析错误: {e}")
            return []
        except Exception as e:
            print(f"解析Swagger失败: 未知错误: {e}")
            # 打印详细的错误信息以便调试
            import traceback
            traceback.print_exc()
            return []