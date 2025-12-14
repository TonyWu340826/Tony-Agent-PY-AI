import logging
from typing import Dict, Any, Optional
import time
import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from active.SwaggerParser import SwaggerParser
from active.endpoint_matcher import analyze_user_intent, match_endpoints_with_ai, execute_api_call, analyze_api_error_and_retry
from model.com_model import AskRequest, StandardResponse, ResponseCode
from model.openAI import chat_completion
from repository.call_log_crud import insert_call_log, delete_call_logs_by_request_id
from repository.entity.sql_entity import t_call_log

class ChatRequest(BaseModel):
    query: str
    swagger_url: Optional[str] = None
    api_url: str
router = APIRouter()


# 🔴 删除用户
@router.delete("/demo1/{user_id}",  summary="删除用户", description="删除用户",operation_id="delete_user1_chat")
def delete_user1_chat(user_id: int):
    return {"message": f"User {user_id} deleted"}





@router.post("/ask", summary="调用大模型")
async def ask_gpt(user_message: str):
    logging.info(f"[开始调用大模型]用户输入：{user_message}")
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        reply = await chat_completion(messages)
        logging.info(f"大模型回复：{reply}")
        return StandardResponse(
            code=ResponseCode.SUCCESS,
            message="操作成功",
            data={"reply": reply}
        )
    except Exception as e:
        logging.error(f"调用大模型失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


# 全局缓存Swagger文档
SWAGGER_CACHE = {}


@router.post("/active/chat")
async def chat_with_ai(request: ChatRequest):
    """主要的聊天接口，根据用户输入智能调用API"""
    # 生成唯一的请求ID，用于串联整个调用过程
    request_id = str(uuid.uuid4())
    
    # 初始化调用日志
    try:
        delete_call_logs_by_request_id(request_id)
    except:
        pass
    
    start_time = time.time()
    
    try:
        # ==========================================
        # 第一步：分析用户意图
        # ==========================================
        logging.info("=" * 50)
        logging.info(f"[第一步] 开始处理用户请求")
        logging.info(f"  用户查询: {request.query}")
        logging.info(f"  请求ID: {request_id}")
        logging.info("=" * 50)
        
        stage_start = time.time()
        user_intent = await analyze_user_intent(request.query)
        stage_time = int((time.time() - stage_start) * 1000)
        
        # 记录意图分析日志
        intent_log = t_call_log(
            request_id=request_id,
            stage="intent_analysis",
            step_order=1,
            operation="分析用户意图",
            input_data=request.query,
            output_data=json.dumps(user_intent, ensure_ascii=False),  # 确保是字符串
            status="success",
            execution_time=stage_time
        )
        insert_call_log(intent_log)
        
        logging.info(f"[第一步完成] 用户意图分析完成")
        logging.info(f"  意图: {user_intent.get('intent', '未知')}")
        logging.info(f"  实体: {user_intent.get('entities', {})}")
        logging.info(f"  操作: {user_intent.get('required_operations', [])}")
        logging.info(f"  执行时间: {stage_time}ms")
        logging.info("")

        # ==========================================
        # 第二步：解析Swagger文档
        # ==========================================
        logging.info("=" * 50)
        logging.info("[第二步] 开始解析Swagger文档")
        logging.info("=" * 50)
        
        stage_start = time.time()
        swagger_url = request.swagger_url or "http://localhost:9876/v3/api-docs"
        if swagger_url in SWAGGER_CACHE:
            endpoints = SWAGGER_CACHE[swagger_url]
            logging.info(f"  使用缓存的Swagger文档，共{len(endpoints)}个接口")
            cache_used = True
        else:
            endpoints = await SwaggerParser.parse_swagger(swagger_url)
            SWAGGER_CACHE[swagger_url] = endpoints
            logging.info(f"  解析完成，共找到{len(endpoints)}个接口")
            cache_used = False
            
        stage_time = int((time.time() - stage_start) * 1000)
        
        # 记录Swagger解析日志
        swagger_log = t_call_log(
            request_id=request_id,
            stage="swagger_parsing",
            step_order=2,
            operation="解析Swagger文档",
            input_data=json.dumps({"swagger_url": swagger_url, "cache_used": cache_used}, ensure_ascii=False),
            output_data=json.dumps({"endpoint_count": len(endpoints)}, ensure_ascii=False),
            status="success",
            execution_time=stage_time
        )
        insert_call_log(swagger_log)
        
        logging.info(f"[第二步完成] Swagger解析成功")
        logging.info(f"  文档URL: {swagger_url}")
        logging.info(f"  接口数量: {len(endpoints)}")
        logging.info(f"  执行时间: {stage_time}ms")
        logging.info("")

        # ==========================================
        # 第三步：AI匹配接口
        # ==========================================
        logging.info("=" * 50)
        logging.info("[第三步] 开始AI匹配接口")
        logging.info("=" * 50)
        
        stage_start = time.time()
        match_result = await match_endpoints_with_ai(user_intent, endpoints)
        stage_time = int((time.time() - stage_start) * 1000)
        
        # 记录接口匹配日志
        matching_log = t_call_log(
            request_id=request_id,
            stage="endpoint_matching",
            step_order=3,
            operation="AI匹配接口",
            input_data=json.dumps({"user_intent": user_intent, "endpoints_count": len(endpoints)}, ensure_ascii=False),
            output_data=json.dumps(match_result, ensure_ascii=False),
            status="success",
            execution_time=stage_time
        )
        insert_call_log(matching_log)
        
        logging.info(f"[第三步完成] AI匹配完成")
        logging.info(f"  匹配到的接口数量: {len(match_result.get('selected_endpoints', []))}")
        logging.info(f"  执行时间: {stage_time}ms")
        if match_result.get('selected_endpoints'):
            for i, endpoint in enumerate(match_result['selected_endpoints']):
                logging.info(f"    接口 {i+1}: 索引 {endpoint.get('endpoint_index')}, 参数 {endpoint.get('call_parameters')}")
        logging.info("")

        # ==========================================
        # 第四步：执行API调用
        # ==========================================
        logging.info("=" * 50)
        logging.info("[第四步] 开始执行API调用")
        logging.info("=" * 50)
        
        results = []
        previous_result = None
        num = 0
        
        # 初始化重试计数器
        retry_counts = {}
        
        for selected in match_result["selected_endpoints"]:
            idx = selected["endpoint_index"] - 1  # 转0-based索引
            if 0 <= idx < len(endpoints):
                endpoint = endpoints[idx]
                params = selected.get("call_parameters", {})
                num += 1
                
                logging.info(f"[第四个步驟 - 接口 {num}]")
                logging.info(f"  接口路径: {endpoint.get('method')} {endpoint.get('path')}")
                logging.info(f"  接口描述: {endpoint.get('summary')}")
                logging.info(f"  调用参数: {params}")
                
                # 为每个端点初始化重试计数
                endpoint_key = f"{endpoint.get('method')}_{endpoint.get('path')}"
                if endpoint_key not in retry_counts:
                    retry_counts[endpoint_key] = 0
                
                # 记录API执行开始日志 (4.n.1)
                api_start_log = t_call_log(
                    request_id=request_id,
                    stage="api_execution",
                    step_order=4 + num * 10 + 1,  # 4.1, 4.2, 4.3...
                    operation=f"开始执行API调用 [{endpoint.get('method')}] {endpoint.get('path')}",
                    input_data=json.dumps({"endpoint": endpoint, "params": params}, ensure_ascii=False),
                    output_data=None,
                    status="pending",
                    endpoint_path=endpoint.get('path'),
                    endpoint_method=endpoint.get('method')
                )
                insert_call_log(api_start_log)
                
                # 执行API调用 (4.n.2)
                stage_start = time.time()
                result = await execute_api_call(endpoint, params, previous_result,request.api_url)
                stage_time = int((time.time() - stage_start) * 1000)
                
                # 检查是否需要错误分析和重试
                # 完全依赖AI来判断是否需要重试，不进行硬编码判断
                should_analyze_error = (
                    result.get("status_code", 0) >= 400 or 
                    not result.get("success", False) or
                    (result.get("success", False) and 
                     isinstance(result.get("data"), dict) and 
                     "content" in result.get("data") and
                     isinstance(result.get("data", {}).get("content"), list) and
                     len(result.get("data", {}).get("content", [])) == 0)
                )
                
                # 记录API执行结果日志 (4.n.3)
                # 增加重试次数限制，最多重试3次
                max_retries = 3
                retry_count = 0
                
                while should_analyze_error and retry_count < max_retries:
                    logging.info(f"  ⚠️ [接口 {num}] 调用失败或返回空数据，开始错误分析 (重试次数: {retry_count+1}/{max_retries})")
                    
                    # 记录错误发生日志 (4.n.4)
                    error_log = t_call_log(
                        request_id=request_id,
                        stage="api_execution",
                        step_order=4 + num * 10 + 4,
                        operation=f"API调用失败 [{endpoint.get('method')}] {endpoint.get('path')}",
                        input_data=json.dumps({"endpoint": endpoint, "params": params}, ensure_ascii=False),
                        output_data=json.dumps(result, ensure_ascii=False),
                        status="failed",
                        error_message=f"Status code: {result.get('status_code', 'N/A')}",
                        execution_time=stage_time,
                        endpoint_path=endpoint.get('path'),
                        endpoint_method=endpoint.get('method')
                    )
                    insert_call_log(error_log)
                    
                    # 进行错误分析和重试 (4.n.5)
                    retry_start = time.time()
                    retry_result = await analyze_api_error_and_retry(endpoint, params, result, endpoints)
                    retry_time = int((time.time() - retry_start) * 1000)
                    
                    # 更新重试计数
                    retry_count += 1
                    
                    # 记录AI纠错分析日志 (4.n.6)
                    ai_correction_log = t_call_log(
                        request_id=request_id,
                        stage="ai_correction",
                        step_order=4 + num * 10 + 6,
                        operation=f"AI纠错分析 [{endpoint.get('method')}] {endpoint.get('path')}",
                        input_data=json.dumps({
                            "original_result": result,
                            "endpoint": endpoint,
                            "params": params
                        }, ensure_ascii=False),
                        output_data=json.dumps(retry_result, ensure_ascii=False),
                        status="success",
                        execution_time=retry_time,
                        endpoint_path=endpoint.get('path'),
                        endpoint_method=endpoint.get('method')
                    )
                    insert_call_log(ai_correction_log)
                    
                    # 记录错误处理日志 (4.n.7)
                    error_handling_log = t_call_log(
                        request_id=request_id,
                        stage="error_handling",
                        step_order=4 + num * 10 + 7,
                        operation=f"错误分析与重试 [{endpoint.get('method')}] {endpoint.get('path')}",
                        input_data=json.dumps({"original_result": result}, ensure_ascii=False),
                        output_data=json.dumps(retry_result, ensure_ascii=False),
                        status="success" if retry_result.get("success", False) else "failed",
                        execution_time=retry_time,
                        endpoint_path=endpoint.get('path'),
                        endpoint_method=endpoint.get('method')
                    )
                    insert_call_log(error_handling_log)
                    
                    # 使用纠错后的结果
                    result = retry_result
                    
                    # 重新检查是否还需要重试（完全依赖AI判断）
                    should_analyze_error = (
                        result.get("status_code", 0) >= 400 or 
                        not result.get("success", False) or
                        (result.get("success", False) and 
                         isinstance(result.get("data"), dict) and 
                         "content" in result.get("data") and
                         isinstance(result.get("data", {}).get("content"), list) and
                         len(result.get("data", {}).get("content", [])) == 0)
                    )
                
                logging.info(f"[接口 {num}调用完成]")
                logging.info(f"  调用结果: {'成功' if result.get('success') else '失败'}")
                logging.info(f"  状态码: {result.get('status_code', 'N/A')}")
                if result.get('data'):
                    if isinstance(result['data'], dict) and 'content' in result['data']:
                        logging.info(f"  数据条数: {len(result['data'].get('content', []))}")
                        logging.info(f"  总元素数: {result['data'].get('totalElements', 'N/A')}")
                    else:
                        logging.info(f"  数据: {type(result['data']).__name__}")
                logging.info(f"  执行时间: {stage_time}ms")
                logging.info("")
                
                results.append(result)
                # 保存结果供下一个调用使用
                previous_result = result
                
                # 更新API执行结果日志 (4.n.8)
                api_result_log = t_call_log(
                    request_id=request_id,
                    stage="api_execution",
                    step_order=4 + num * 10 + 8,
                    operation=f"完成API调用 [{endpoint.get('method')}] {endpoint.get('path')}",
                    input_data=json.dumps({"endpoint": endpoint, "params": params}, ensure_ascii=False),
                    output_data=json.dumps(result, ensure_ascii=False),
                    status="success" if result.get("success", False) else "failed",
                    execution_time=stage_time,
                    endpoint_path=endpoint.get('path'),
                    endpoint_method=endpoint.get('method')
                )
                insert_call_log(api_result_log)

        # ==========================================
        # 第五步：返回结果
        # ==========================================
        logging.info("=" * 50)
        logging.info("[第五步] 准备返回最终结果")
        logging.info("=" * 50)
        
        total_time = int((time.time() - start_time) * 1000)
        response_data = {
            "user_intent": user_intent,
            "match_result": match_result,
            "execution_results": results,
            "success": all(r.get("success") for r in results),  # 修改为所有调用都成功才算成功
            "request_id": request_id,
            "total_execution_time": total_time
        }
        
        # 记录最终响应日志 (5)
        final_log = t_call_log(
            request_id=request_id,
            stage="final_response",
            step_order=5,
            operation="返回最终响应",
            input_data=None,
            output_data=json.dumps(response_data, ensure_ascii=False),
            status="success",
            execution_time=total_time
        )
        insert_call_log(final_log)
        
        logging.info(f"[第五步完成] 最终响应准备完成")
        logging.info(f"  总体执行时间: {total_time}ms")
        logging.info(f"  接口调用成功率: {sum(1 for r in results if r.get('success'))}/{len(results)}")
        logging.info(f"  最终状态: {'成功' if response_data['success'] else '失败'}")
        logging.info("=" * 50)
        logging.info("处理流程完成")
        logging.info("=" * 50)
        
        return response_data

    except Exception as e:
        # ==========================================
        # 异常处理
        # ==========================================
        logging.error("=" * 50)
        logging.error("[异常] 处理过程中发生异常")
        logging.error(f"  错误信息: {str(e)}")
        logging.error(f"  请求ID: {request_id}")
        logging.error("=" * 50)
        
        # 记录异常日志 (6)
        error_log = t_call_log(
            request_id=request_id,
            stage="exception",
            step_order=6,
            operation="处理过程中发生异常",
            input_data=json.dumps(str(request.dict()), ensure_ascii=False),
            output_data=None,
            status="failed",
            error_message=str(e)
        )
        insert_call_log(error_log)
        
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/active/load-swagger")
async def load_swagger(swagger_url: str):
    """专门加载Swagger文档"""

    endpoints = await SwaggerParser.parse_swagger(swagger_url)
    SWAGGER_CACHE["latest"] = endpoints
    return {"count": len(endpoints), "endpoints": endpoints[:5]}  # 只返回前5个示例


'''
====================自定义工作流=======================================
'''