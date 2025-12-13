import aiohttp
import asyncio
from typing import List, Dict, Any
import logging


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
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
            
            for path, methods in paths_data.items():
                for method, details in methods.items():
                    if method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
                        continue

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
                            # 保存参数详细信息
                            endpoint["parameter_details"].append({
                                "name": param_name,
                                "in": param.get("in", ""),  # path, query, header, cookie, body
                                "required": param.get("required", False),
                                "schema": param.get("schema", {}),
                                "description": param.get("description", "")
                            })
                    
                    # 处理requestBody参数
                    if "requestBody" in details:
                        endpoint["requestBody"] = details["requestBody"]
                        # 解析requestBody中的参数
                        content = details["requestBody"].get("content", {})
                        for content_type, content_details in content.items():
                            if content_type == "application/json" and "schema" in content_details:
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
            return []