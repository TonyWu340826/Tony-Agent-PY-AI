from typing import Optional
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from model import DashScopeModel, get_dashscope_model
from repository.crud import get_user_by_id, create_user, get_all_users, update_user, delete_user
from repository.entity.sql_entity import t_user
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict
from dto.user_model import ImageUnderstandingBase64Request, ImageUnderstandingUploadRequest
import os
import uuid
import base64


router = APIRouter(prefix="/user", tags=["user"])
router.mount("/static", StaticFiles(directory="static"), name="static")


# 请求模型
class UserCreate(BaseModel):
    id: int
    name: str
    address: str
    sex: int

class UserUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    sex: Optional[int] = None




from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config.database import execute_sql  # 用你的数据库执行函数
from core.logger import logger

class SQLRequest(BaseModel):
    sql: str


# 🔵 查询用户
@router.get("/find_user_byid/{user_id}", tags=["根据主键ID查询"])
def read_user(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

# 🟢 创建用户
@router.post("/create_user/", tags=["创建用户"])
def create_user1(user: t_user):
    try:
        create_user(user.id, user.name, user.address, user.sex)
        return {"msg": "用户创建成功", "data": user.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🟢 创建用户
@router.post("/create_users_init/", tags=["用户数据初始化"])
def create_user_init100():
    try:
        for i in range(4, 104):
            create_user(i, f"name_{i}", f"address_{i}", i % 2)
        return {"msg": "成功创建 100 个测试用户", "total": 100}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


# 🔵 查询用户
@router.get("/get_all_users/", tags=["查询所有用户"])
def get_all_users1(skip: int = 0, limit: int = 10):
    return get_all_users(skip=skip, limit=limit)

# 🟡 更新用户
@router.put("/update_user/{user_id}", tags=["根据用户ID修改数据"])
def update_user1(user_id: int, user_update: UserUpdate):
    try:
        update_user(user_id, user_update.name, user_update.address, user_update.sex)
        return {"msg": "更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔴 删除用户
@router.delete("/delete_user/{user_id}",  summary="删除用户", description="删除用户",operation_id="delete_user1")
def delete_user1(user_id: int):
    try:
        delete_user(user_id)
        return {"msg": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




class ChatRequest(BaseModel):
    prompt: str



# 根路径返回聊天页面
@router.get("/ui/chat/", response_class=HTMLResponse)
async def get_chat_page():
    with open("static/chat.html", "r", encoding="utf-8") as f:
        return f.read()

@router.post("/aliyun/chat", response_model=Dict[str, str])
async def chat(
    request: ChatRequest,
    model: DashScopeModel = Depends(get_dashscope_model)  # ← 注入模型
):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    response_text = model.call(request.prompt)
    return {"response": response_text}




from pydantic import BaseModel
from typing import Optional

class ChatRequest2(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    size: Optional[str] = "1024*1024"

@router.post("/aliyun/image_create", response_model=dict)
async def chat(
    request: ChatRequest2,
    model: DashScopeModel = Depends(get_dashscope_model)
):
    # 去掉首尾空格
    prompt = request.prompt.strip()
    if not prompt:
        return {"error": "prompt 不能为空"}

    # 判断：只要用户显式传了 negative_prompt 字段（包括传了空字符串），就认为要生图
    # 注意：Pydantic 中如果没传，值为 None；如果传了 ""，值就是 ""
    if request.negative_prompt is not None:
        # 图像生成
        resp = model.text_to_image(
            prompt=prompt,
            negative_prompt=request.negative_prompt or "",
            size=request.size or "1024*1024"
        )
        if not resp:
            return {"error": "图像生成失败"}

        try:
            logger.info(f"图像生成结果：{resp}")
            image_url = resp.output.choices[0].message.content[0]["image"]
            logger.info(f"图像生成成功：{image_url}")
            return {"image_url": image_url}
        except Exception:
            return {"error": "无法解析图像结果"}
    else:
        # 智能体对话
        response_text = model.call(prompt)
        return {"response": response_text}


# 图像理解接口 - Base64版本的核心逻辑
async def _image_understanding_base64_logic(request: ImageUnderstandingBase64Request, model: DashScopeModel):
    """图像理解Base64版本的核心逻辑"""
    if not request.image_content.strip():
        return {"error": "image_content 不能为空"}
        
    if not request.prompt.strip():
        return {"error": "prompt 不能为空"}

    try:
        response_text = model.image_to_text(
            image_content=request.image_content,
            prompt=request.prompt,
            model=request.model
        )
        logger.info(f"图像理解结果：{response_text}")
        if response_text:
            return {"response": response_text}
        else:
            return {"error": "图像理解失败"}
    except Exception as e:
        logger.exception("图像理解接口异常")
        return {"error": f"处理失败: {str(e)}"}


# 图像理解接口 - Base64版本
@router.post("/aliyun/image_understanding_base64", response_model=dict)
async def image_understanding_base64(
    request: ImageUnderstandingBase64Request,
    model: DashScopeModel = Depends(get_dashscope_model)
):
    """根据图片Base64编码和提示词生成文本描述"""
    return await _image_understanding_base64_logic(request, model)


# 图像理解接口 - 文件上传版本（本地测试用）
@router.post("/aliyun/image_understanding_upload", response_model=dict)
async def image_understanding_upload(
    file: UploadFile = File(...),
    prompt: str = "请描述这张图片的内容",
    model: DashScopeModel = Depends(get_dashscope_model)
):
    """上传图片文件并根据提示词生成文本描述（本地测试用，自动转换为Base64并调用Base64接口）"""
    # 检查文件类型
    if not file.content_type.startswith("image/"):
        return {"error": "只支持图片文件上传"}
    
    try:
        # 读取上传的文件内容
        content = await file.read()
        
        # 将文件转换为Base64编码
        base64_image = base64.b64encode(content).decode("utf-8")
        
        # 根据文件扩展名确定MIME类型
        _, ext = os.path.splitext(file.filename)
        mime_type = "image/jpeg"  # 默认JPEG
        if ext.lower() in ['.jpg', '.jpeg']:
            mime_type = "image/jpeg"
        elif ext.lower() == '.png':
            mime_type = "image/png"
        elif ext.lower() == '.webp':
            mime_type = "image/webp"
        elif ext.lower() == '.gif':
            mime_type = "image/gif"
        
        # 确保image_content格式正确，包含"data:image/..."前缀
        image_content = f"data:{mime_type};base64,{base64_image}"
        
        # 验证Base64字符串是否有效
        if not base64_image:
            return {"error": "文件转换为Base64失败"}
        logger.info(f"图像理解请求 - image_content={image_content}")
        # 创建请求对象
        request = ImageUnderstandingBase64Request(
            image_content=image_content,
            prompt=prompt,
            model="qwen-vl-plus"
        )
        
        # 调用Base64版本的核心逻辑
        return await _image_understanding_base64_logic(request, model)
        
    except Exception as e:
        logger.exception("图像理解接口异常")
        return {"error": f"处理失败: {str(e)}"}

















@router.post("/sql/exec", tags=["执行sql"])
def exec_sql(req: SQLRequest):
    sql_text = req.sql.strip()
    if not sql_text:
        raise HTTPException(status_code=400, detail="SQL 不能为空")

    try:
        # 判断SQL类型
        if sql_text.lower().startswith("select"):
            result = execute_sql(sql_text, fetch="all")
            return {"msg": "查询成功", "data": result}
        else:
            execute_sql(sql_text)
            return {"msg": "执行成功（非查询语句）"}
    except Exception as e:
        logger.exception("SQL 执行失败")
        raise HTTPException(status_code=500, detail=f"SQL 执行失败: {e}")