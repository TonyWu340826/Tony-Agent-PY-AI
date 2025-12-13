import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from active.SwaggerParser import SwaggerParser
from active.endpoint_matcher import analyze_user_intent, match_endpoints_with_ai, execute_api_call
from model.com_model import AskRequest, StandardResponse, ResponseCode
from model.openAI import chat_completion

class ChatRequest(BaseModel):
    query: str
    swagger_url: Optional[str] = None
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
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ]
        reply = await chat_completion(messages)
        logging.info(f"[结束调用大模型]大模型回复：{reply}")
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






DEFAULT_SYSTEM_PROMPT = "You are a helpful, accurate, and concise AI assistant."

@router.post("/ask-base", response_model=StandardResponse)
async def ask_gpt_base(request: AskRequest):
    """
    与 GPT 对话（统一返回格式）：
    - user_message: 必填，用户输入
    - system_prompt: 可选，若未提供则使用默认提示词
    """
    try:
        # 可选：增加非空校验（Pydantic 默认允许空字符串，如需禁止可加约束）
        if not request.user_message or not request.user_message.strip():
            return StandardResponse(
                code=ResponseCode.BAD_REQUEST,  # 10000
                message="用户消息不能为空",
                data=None
            )
        system_prompt = request.system_prompt or DEFAULT_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.user_message.strip()}
        ]
        reply = await chat_completion(messages)
        return StandardResponse.success(data={"reply": reply})  # code=0
    except Exception as e:
        # 所有未预期异常视为系统错误
        return StandardResponse.fail(str(e))



'''
====================自定义工作流=======================================
'''
SWAGGER_CACHE: Dict[str, Any] = {
    "latest": []  # 初始化为空列表
}


@router.post("/active/chat")
async def chat_with_ai(request: ChatRequest):
    """
    完整流程：
    1. 分析用户意图
    2. 解析Swagger（如有）
    3. AI匹配接口
    4. 执行调用
    5. 返回结果
    """
    try:
        # 1. 分析用户意图
        user_intent = await analyze_user_intent(request.query)
        logging.info(f"[第一步结束]用户意图：{user_intent}")

        # 2. 获取接口列表
        endpoints = []
        if request.swagger_url:
            # 解析新的Swagger
            endpoints = await SwaggerParser.parse_swagger(request.swagger_url)
            logging.info(f"[第二步结束]解析Swagger成功，共找到{len(endpoints)}个接口")
            SWAGGER_CACHE["latest"] = endpoints
        elif "latest" in SWAGGER_CACHE:
            # 使用缓存的接口
            endpoints = SWAGGER_CACHE["latest"]
        else:
            raise HTTPException(status_code=400, detail="请先提供Swagger文档URL")

        # 3. AI匹配接口
        match_result = await match_endpoints_with_ai(user_intent, endpoints)
        logging.info(f"[第三步结束]AI匹配结果：{match_result}")
        if not match_result.get("selected_endpoints"):
            logging.info("[第三步异常]未找到匹配的接口")
            return {"error": "未找到匹配的接口", "user_intent": user_intent}

        # 4. 执行调用
        results = []
        previous_result = None
        num= 0
        for selected in match_result["selected_endpoints"]:
            idx = selected["endpoint_index"] - 1  # 转0-based索引
            if 0 <= idx < len(endpoints):
                endpoint = endpoints[idx]
                params = selected.get("call_parameters", {})
                logging.info(f"[第四步调试]调用接口: {endpoint.get('path')}, 参数: {params}")
                num += 1
                result = await execute_api_call(endpoint, params, previous_result)
                logging.info(f"[第四步第{num}个接口]调用结果: {result}")
                results.append(result)
                # 保存结果供下一个调用使用
                previous_result = result

        # 5. 返回结果
        return {
            "user_intent": user_intent,
            "match_result": match_result,
            "execution_results": results,
            "success": any(r.get("success") for r in results)
        }

    except Exception as e:
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






