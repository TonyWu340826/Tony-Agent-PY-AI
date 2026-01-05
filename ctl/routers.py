from fastapi import APIRouter
from ctl.demo_ctl import router as demo_router
from ctl.student_ctl import router as student_router
from ctl.user_ctl import router as user_router
from ctl.OAuth2_ctl import router as OAuth2_ctl
from ctl.data_app_sub import router as data_app_sub
from ctl.chat_ctl import router as chat_ctl
from ctl.coze_ctl import router as coze_ctl
from ctl.call_log_ctl import router as call_log_ctl
from ctl.aliyun_ai_ctl import router as aliyun_ai_ctl
from ctl.embedding_ctl import router as embedding_router

api_router = APIRouter()

# 统一挂载
api_router.include_router(demo_router, prefix="/demo")
api_router.include_router(student_router, prefix="/student")
api_router.include_router(user_router, prefix="/user")
api_router.include_router(OAuth2_ctl, prefix="/auth")
api_router.include_router(data_app_sub, prefix="/data")
api_router.include_router(chat_ctl, prefix="/chat")
api_router.include_router(coze_ctl, prefix="/coze")
api_router.include_router(call_log_ctl)
api_router.include_router(aliyun_ai_ctl, prefix="/ai")
api_router.include_router(embedding_router, prefix="/embedding")  # 添加embedding路由