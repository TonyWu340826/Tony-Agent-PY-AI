# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
#
# """
# 主入口：AI驱动的通用接口调用工作流
# 流程：
# 1. 用户输入自然语言查询
# 2. AI分析用户意图，提取关键信息
# 3. 解析Swagger文档，获取可用接口列表
# 4. AI根据用户意图匹配最合适接口
# 5. 执行接口调用
# 6. 返回结果给用户
# """
#
# import logging
# import traceback
# from typing import Dict, Any, List
# from active.endpoint_matcher import analyze_user_intent, match_endpoints_with_ai, execute_api_call, analyze_api_error_and_retry
# from active.SwaggerParser import SwaggerParser
# from config.config import config
#
# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
#
# logger = logging.getLogger(__name__)
#
#
# async def chat_with_ai(user_query: str, swagger_urls: List[str] = None) -> Dict[str, Any]:
#     """
#     AI驱动的通用接口调用工作流
#
#     Args:
#         user_query: 用户的自然语言查询
#         swagger_urls: Swagger文档URL列表
#
#     Returns:
#         包含用户意图、匹配结果和执行结果的字典
#     """
#     try:
#         logger.info(f"🚀 开始处理用户查询: {user_query}")
#
#         # 如果没有提供Swagger URLs，从配置中获取
#         if not swagger_urls:
#             swagger_urls = []
#             # 从配置中获取预定义的Swagger URLs
#             swagger_configs = config.get("swagger_urls", {})
#             for service_config in swagger_configs.values():
#                 if isinstance(service_config, dict) and service_config.get("enabled", True):
#                     url = service_config.get("url")
#                     if url:
#                         swagger_urls.append(url)
#
#             # 如果配置中没有URL，使用默认值
#             if not swagger_urls:
#                 swagger_urls = ["http://localhost:8889/openapi.json"]
#
#         logger.info(f"📚 Swagger URLs: {swagger_urls}")
#
#         # 第一步：分析用户意图
#         logger.info("🔍 [第一步] 分析用户意图")
#         user_intent = await analyze_user_intent(user_query)
#         logger.info(f"🎯 用户意图分析完成: {user_intent}")
#
#         # 第二步：解析Swagger文档
#         logger.info("📖 [第二步] 解析Swagger文档")
#         all_endpoints = []
#         for swagger_url in swagger_urls:
#             try:
#                 endpoints = await SwaggerParser.parse_swagger(swagger_url)
#                 all_endpoints.extend(endpoints)
#                 logger.info(f"  ✅ 从 {swagger_url} 解析到 {len(endpoints)} 个接口")
#             except Exception as e:
#                 logger.error(f"  ❌ 解析 {swagger_url} 失败: {e}")
#                 continue
#
#         logger.info(f"📊 总共解析到 {len(all_endpoints)} 个接口")
#
#         if not all_endpoints:
#             return {
#                 "success": False,
#                 "error": "未能解析任何Swagger文档",
#                 "user_intent": user_intent
#             }
#
#         # 第三步：AI匹配接口
#         logger.info("🧠 [第三步] AI匹配接口")
#         match_result = await match_endpoints_with_ai(user_intent, all_endpoints)
#         logger.info(f"🔗 接口匹配完成: {match_result}")
#
#         # 第四步：执行API调用
#         logger.info("⚡ [第四步] 执行API调用")
#         execution_results = []
#
#         # 获取调用序列
#         call_sequence = match_result.get("call_sequence", [])
#         selected_endpoints = match_result.get("selected_endpoints", [])
#
#         # 如果没有明确的调用序列，按selected_endpoints顺序执行
#         if not call_sequence:
#             call_sequence = list(range(1, len(selected_endpoints) + 1))
#
#         previous_result = None
#         for i, endpoint_index in enumerate(call_sequence):
#             try:
#                 # 确保索引有效（1-based）
#                 # AI返回的call_sequence中的数字直接对应接口列表的索引
#                 if 1 <= endpoint_index <= len(all_endpoints):
#                     endpoint = all_endpoints[endpoint_index - 1]
#                     # 在selected_endpoints中查找对应的参数
#                     selected_endpoint_info = None
#                     for se in selected_endpoints:
#                         if se.get("endpoint_index") == endpoint_index:
#                             selected_endpoint_info = se
#                             break
#
#                     # 如果找不到对应的参数信息，使用默认值
#                     if selected_endpoint_info is None:
#                         selected_endpoint_info = {"endpoint_index": endpoint_index, "call_parameters": {}}
#
#                     call_params = selected_endpoint_info.get("call_parameters", {})
#
#                     logger.info(f"  🔧 [第四步第{i+1}个接口] 开始调用: {endpoint.get('path')}")
#
#                     # 执行API调用
#                     result = await execute_api_call(endpoint, call_params, previous_result)
#
#                     # 检查是否需要错误分析和重试
#                     if result.get("status_code", 0) >= 400 or not result.get("success", False):
#                         logger.info(f"  ⚠️ [第四步第{i+1}个接口] 调用失败，开始错误分析")
#                         # 进行错误分析和重试
#                         result = await analyze_api_error_and_retry(endpoint, call_params, result, all_endpoints)
#
#                     execution_results.append(result)
#                     previous_result = result
#
#                     logger.info(f"  ✅ [第四步第{i+1}个接口] 调用结果: {result}")
#                 else:
#                     error_msg = f"无效的调用序列索引: {endpoint_index}"
#                     logger.error(f"  ❌ {error_msg}")
#                     execution_results.append({"success": False, "error": error_msg})
#             except Exception as e:
#                 error_msg = f"执行第{i+1}个接口调用时发生错误: {str(e)}"
#                 logger.error(f"  ❌ {error_msg}")
#                 logger.error(f"  📋 错误详情: {traceback.format_exc()}")
#                 execution_results.append({"success": False, "error": error_msg})
#
#         # 构建最终结果
#         final_result = {
#             "success": True,
#             "user_intent": user_intent,
#             "match_result": match_result,
#             "execution_results": execution_results
#         }
#
#         # 检查是否有任何调用失败
#         for result in execution_results:
#             if not result.get("success", False):
#                 final_result["success"] = False
#                 break
#
#         logger.info("🏁 工作流执行完成")
#         return final_result
#
#     except Exception as e:
#         error_msg = f"工作流执行过程中发生错误: {str(e)}"
#         logger.error(f"💥 {error_msg}")
#         logger.error(f"📋 错误详情: {traceback.format_exc()}")
#         return {
#             "success": False,
#             "error": error_msg,
#             "user_intent": {},
#             "match_result": {},
#             "execution_results": []
#         }
#
#
# # 测试入口
# if __name__ == "__main__":
#     import asyncio
#     import sys
#
#     # 设置日志级别
#     logging.getLogger().setLevel(logging.INFO)
#
#     if len(sys.argv) > 1:
#         query = " ".join(sys.argv[1:])
#     else:
#         query = "查询用户信息"
#
#     print(f"🤖 测试查询: {query}")
#
#     async def test():
#         result = await chat_with_ai(query)
#         print(f"📊 最终结果: {result}")
#
#     asyncio.run(test())