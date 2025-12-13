from pydantic import BaseModel


# 定义你希望接收的 JSON 结构
class UserCreate(BaseModel):
    user_name: str
    email: str
    age: int
    is_active: bool = True


class ImageUnderstandingUploadRequest(BaseModel):
    prompt: str = "请描述这张图片的内容"
    model: str = "qwen-vl-plus"


class ImageUnderstandingBase64Request(BaseModel):
    image_content: str
    prompt: str
    model: str = "qwen-vl-plus"