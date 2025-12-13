from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import os
import logging
from dotenv import load_dotenv
from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL, Stream, WorkflowEvent, WorkflowEventType

# ----------------------------
# 日志配置
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coze_workflow")

# ----------------------------
# 加载 .env 配置
# ----------------------------
load_dotenv()

COZE_API_TOKEN = os.getenv("coze_api_token")
COZE_AutoCase_WORKFLOW_ID = os.getenv("coze_autoCase_workflow_id")
COZE_CaseCheck_WORKFLOW_ID = os.getenv("coze_caseCheck_workflow_id")

logger.info(
    f"🔑 加载环境变量 - Token存在: {bool(COZE_API_TOKEN)}, "
    f"AutoCase Workflow ID: {COZE_AutoCase_WORKFLOW_ID}, "
    f"CaseCheck Workflow ID: {COZE_CaseCheck_WORKFLOW_ID}"
)

if not COZE_API_TOKEN:
    raise RuntimeError("❌ 缺少 coze_api_token")
if not COZE_AutoCase_WORKFLOW_ID:
    raise RuntimeError("❌ 缺少 coze_autoCase_workflow_id")
if not COZE_CaseCheck_WORKFLOW_ID:
    raise RuntimeError("❌ 缺少 coze_caseCheck_workflow_id")

# ----------------------------
# 初始化 Coze 客户端
# ----------------------------
coze_client = Coze(
    auth=TokenAuth(token=COZE_API_TOKEN),
    base_url=COZE_CN_BASE_URL
)

# ----------------------------
# 请求模型（使用 discriminated union 更佳，但简化处理）
# ----------------------------
class WorkflowRequest(BaseModel):
    type: str = Field(..., pattern="^(autoCase|caseCheck)$", description="工作流类型")
    mail: str
    # autoCase 专用
    document_id: Optional[str] = ""
    input1: Optional[str] = ""
    # caseCheck 专用
    test_case_url_token: Optional[str] = None

# ----------------------------
# 后台任务：异步执行工作流
# ----------------------------
def run_workflow_in_background(
    workflow_type: str,
    mail: str,
    document_id: str = "",
    input1: str = "",
    test_case_url_token: Optional[str] = None,
):
    """
    在后台运行 Coze 工作流
    """
    try:
        if workflow_type == "autoCase":
            workflow_id = COZE_AutoCase_WORKFLOW_ID
            parameters = {
                "document_id": document_id,
                "input1": input1,
                "mail": mail
            }
        elif workflow_type == "caseCheck":
            workflow_id = COZE_CaseCheck_WORKFLOW_ID
            if not test_case_url_token:
                logger.error(f"❌ caseCheck 类型缺少 test_case_url_token (邮箱: {mail})")
                return
            parameters = {
                "test_case_url_token": test_case_url_token,
                "email": mail  # 注意：Coze 工作流变量名是 email 还是 mail？请确认！
            }
        else:
            logger.error(f"❌ 未知工作流类型: {workflow_type}")
            return

        logger.info(f"🚀 启动 {workflow_type} 工作流，目标邮箱: {mail}")

        stream = coze_client.workflows.runs.stream(
            workflow_id=workflow_id,
            parameters=parameters
        )

        # 消费事件流
        for event in stream:
            if event.event == WorkflowEventType.ERROR:
                err_msg = getattr(event.error, 'msg', '未知错误')
                logger.error(f"❌ {workflow_type} 工作流出错 (邮箱: {mail}): {err_msg}")
                break
            elif event.event == WorkflowEventType.MESSAGE:
                content = event.message.content if event.message and event.message.content else ""
                if content:
                    logger.debug(f"📧 {workflow_type} 输出片段 ({mail}): {content[:100]}...")

        logger.info(f"✅ {workflow_type} 工作流完成（邮箱: {mail}）")

    except Exception as e:
        logger.exception(f"💥 后台工作流异常 ({workflow_type}, 邮箱: {mail}): {e}")

# ----------------------------
# FastAPI 应用
# ----------------------------
app = FastAPI(
    title="Coze Workflow Controller",
    description="通过 FastAPI 触发 Coze 工作流（autoCase / caseCheck），结果将通过邮件发送"
)

router = APIRouter()

@router.post("/run-workflow", response_model=dict)  # 简化响应模型
async def run_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks
):
    """
    触发 Coze 工作流（立即返回，异步执行）
    """
    # 参数校验
    if request.type == "autoCase":
        if not request.input1:
            raise HTTPException(status_code=400, detail="autoCase 类型必须提供 input1")
    elif request.type == "caseCheck":
        if not request.test_case_url_token:
            raise HTTPException(status_code=400, detail="caseCheck 类型必须提供 test_case_url_token")

    # 添加后台任务
    background_tasks.add_task(
        run_workflow_in_background,
        workflow_type=request.type,
        mail=request.mail,
        document_id=request.document_id,
        input1=request.input1,
        test_case_url_token=request.test_case_url_token,
    )

    return {
        "message": "✅ 调用成功！请五分钟后检查你的邮箱查看结果。",
        "mail": request.mail,
        "type": request.type
    }

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "coze_api_token_configured": bool(COZE_API_TOKEN),
        "autoCase_workflow_id": COZE_AutoCase_WORKFLOW_ID,
        "caseCheck_workflow_id": COZE_CaseCheck_WORKFLOW_ID,
    }
