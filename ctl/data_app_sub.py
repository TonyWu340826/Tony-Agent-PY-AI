from fastapi import APIRouter, requests
from invoice import Invoice

from config.config import settings

'''
方式	类型	路由处理	中间件	适用场景
app.mount()	子应用（SubApplication）	完全独立，主应用不管	子应用有自己的中间件	独立服务、FastAPI 嵌套 FastAPI
router.include_router()	路由包含（Include Router）	统一管理，主应用控制一切	共享主应用中间件	模块化拆分（推荐
'''
router = APIRouter()

# main.py
from fastapi import FastAPI

'''
读取配置
'''
@router.get("/config_info")
def get_info():
    return {
        "app_name": settings.app_name,
        "admin_email": settings.admin_email,
        "items_per_user": settings.items_per_user,
        "debug": settings.debug,
        "SC_NAME": settings.SC_NAME
    }

@router.get("/health")
def health():
    return {"status": "ok", "database": settings.database_url}





from pydantic import BaseModel, HttpUrl
from typing import Optional

# =============================
# 1. 定义数据模型
# =============================

class Invoice(BaseModel):
    id: str
    customer: str
    amount: float

class PaymentEvent(BaseModel):
    event: str = "payment_received"
    invoice_id: str

class PaymentAck(BaseModel):
    ok: bool = True


# =============================
# 2. 创建回调路由（仅用于文档）
# =============================

@router.post(
    "{$callback_url}/invoices/{$request.body.id}",  # 🔥 动态路径
    summary="支付成功通知",
    description="当发票支付成功后，我们会向你提供的 callback_url 发送此通知。",
    response_model=PaymentAck,
    status_code=200,
)
def payment_notification(event: PaymentEvent):
    """
    这个函数不会被实际调用。
    它的存在只是为了生成 OpenAPI 文档。
    """
    pass  # 文档专用，无需实现


# =============================
# 3. 主接口：创建发票 + 回调
# =============================


@router.post("/create-invoice", callbacks=router.routes)
def create_invoice(
    invoice: Invoice,
    callback_url: Optional[HttpUrl] = None
):
    """
    创建一张发票。
    如果提供了 callback_url，支付成功后会发送 Webhook 回调。
    """
    # ✅ 修复：只打印信息，不混入赋值
    print(f"✅ 发票 {invoice.id} 已创建，客户：{invoice.customer}")

    # ✅ 创建要发送给对方的回调数据
    data = PaymentEvent(event="payment_received", invoice_id=invoice.id)

    if callback_url:
        try:
            # ✅ 构造回调 URL：{callback_url}/invoices/{invoice.id}
            callback_endpoint = f"{callback_url}/invoices/{invoice.id}"
            print(f"📤 正在向 {callback_endpoint} 发送回调...")

            # ✅ 发送 POST 请求
            resp = requests.post(callback_endpoint, json=data.dict())
            print(f"📨 回调响应: {resp.status_code} {resp.text}")

        except Exception as e:
            print(f"❌ 回调失败: {e}")

    return {"msg": "发票已创建", "id": invoice.id}





















