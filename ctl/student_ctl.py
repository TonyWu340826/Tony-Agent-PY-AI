import datetime
from http.client import HTTPException
from fastapi import APIRouter, Form, Query, Depends
from typing import Annotated
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from starlette.responses import JSONResponse, HTMLResponse
from core.dependencies import common_parameters
from service.studentService import FixedContentQueryChecker



router = APIRouter()



"""
@auth:
@time:
@desc: 学生管理接口
"""


'''
查询用户信息-没有入参
'''
@router.get("/student_query")
async def query_student():
    return {"msg": "查询成功"}


@router.get("/student_find/{id}")
async def query_student_by_id(id: int):
    return {"msg": f"查询成功, id={id}"}


'''
路径方式
'''
@router.get("/student_find_name/{name}")
async def query_student_by_name(name: str):
    return {"msg": f"查询成功, name={name}"}


'''
接收一个json数据
'''
@router.post("/student_add")
async def add_student(obj: dict):
    print("接收到的 JSON 数据：", obj)
    return {"msg": "添加成功", "received": obj}


'''
表单方式
'''
@router.post("/student_create_form")
async def create_student_form(name: str = Form(...),
                              age: int = Form(...),
                              email: str = Form(...)
                              ):
    # 打印接收到的数据
    print("✅ 接收到的表单数据：")
    print(f"  姓名: {name}")
    print(f"  年龄: {age}")
    print(f"  邮箱: {email}")

    return {
        "msg": "学生创建成功",
        "data": {
            "name": name,
            "age": age,
            "email": email
        }
    }


'''
入参为文件路径 
http://localhost:8082/files/users/123/avatar.png
返回{
  "file_path": "users/123/avatar.png"
}
'''
@router.get("/files/{file_path:path}")
async def read_file(file_path: str):
    print(f"接收到的文件路径: {file_path}")
    return {"file_path": file_path}

'''
查询参数
就是 URL 中 ? 后面的“键值对”
某个参数不是必须的，可以用 = None 或 = "默认值"  name: str = none, category: str = "通用"
如果你想让某个查询参数 必须提供，可以用 = ...：   name: str = ..., category: str = "通用"
请求方式地址：
http://example.com/items?name=手机&category=电子&price=999
'''
@router.get("/items")
async def read_items(name: str, category: str):
    return {"name": name, "category": category}


@router.get("/items_optional/{user_id}/find")
async def test_query(
        user_id: int,
        name: str,
        address:str = None,
        age:int = 18):
    return {"user_id": user_id, "name": name, "address": address, "age": age}



'''
字符串长度限制
'''
@router.get("/student_read_items01/")
async def read_items(
    q: Annotated[
        str | None,
        Query(
            min_length=3,
            max_length=50,
            pattern=r"^[a-zA-Z0-9\u4e00-\u9fa5]+$",  # 只允许中英文数字
            title="搜索关键词",
            description="用于模糊匹配商品名称，至少3个字符",
            example="手机"
        )
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, title="每页数量", example=20)
    ] = 20
):
    return {
        "q": q,
        "limit": limit
    }
@router.get("/student_read_items02/")
async def read_items(
    q: list[str] = Query(["foo", "bar"])  # 默认是 ["foo", "bar"]
):
    return {"q": q}



'''
使用 Pydantic 模型来定义查询参数
'''
'''
先定义一个接口的dto，并限制对象属性的类型和范围
'''
class ItemsQuery():
    q: str | None = Query(None, min_length=3, max_length=50)
    skip: int = Query(0, ge=0)
    limit: int = Query(10, ge=1, le=100)
    sort: str = Query("id", pattern="^(id|name|price)$")
    featured: bool = False


'''
依赖项  Depends  和   dependencies的使用 start
'''

@router.get("/depends/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    # commons 参数的值就是 common_parameters() 函数的返回值
    return commons

@router.get("/depends/users/")
async def read_users(commons: dict = Depends(common_parameters)):
    return commons



@router.get("/depends/s3/")
async def read_items(
    # ✅ 直接在 Depends() 中创建类实例
    # 这样更简洁，也表明这是一个依赖项
    fixed_content_in_q: bool = Depends(FixedContentQueryChecker("bar"))
):
    return {"fixed_content_in_q": fixed_content_in_q}

'''
到目前为止，我们主要在路径操作函数的参数列表中使用 Depends()。这适用于那些：

需要获取依赖项返回值用于业务逻辑的场景。
依赖项本身需要从请求中获取参数（如查询参数、请求体）的场景。
但有些依赖项，我们只关心它的执行效果（比如验证、记录日志），而不关心它的返回值。对于这类依赖项，如果还把它放在参数列表里，会显得冗余和混乱。
dependencies=[Depends(verify_token)]：这是关键。dependencies 是一个列表，可以包含多个 Depends()。
verify_token 函数的返回值被忽略。我们只关心它是否成功执行（即没有抛出异常）。

dependencies 理论上只能用于没有返回值的依赖项。，Depends 都可以，只是用dependencies 单独处理更优雅
'''

# 示例：一个不需要返回值的认证依赖
async def verify_token(token: str):
    if token != "secret-token":
        raise HTTPException(status_code=403, detail="Invalid token")


@router.get("/items/", dependencies=[Depends(verify_token)])
async def read_items():
    return {"message": "Here are your items!"}

'''
依赖项  Depends  和   dependencies的使用 end
'''




'''
token 验证 安全
'''

# 给接口加上“刷卡”要求
@router.get("/login/user/")
async def read_items(token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="token"))]):
    return {"token": token}  # 返回你刷的卡号

'''
token 验证 安全  end
'''


'''
CORS（跨域资源共享）
'''






'''
 后台任务（Background Tasks）
'''
from fastapi import BackgroundTasks, FastAPI
def write_log(username: str):
    with open("log.txt", "a") as f:
        f.write(f"用户 {username} 在 {datetime.now()} 注册了\n")

app = FastAPI()

@router.post("/register/")
def register(username: str, background_tasks: BackgroundTasks):
    # 1. 正常处理（比如创建用户）
    print(f"用户 {username} 注册成功！")

    # 2. 添加后台任务
    background_tasks.add_task(write_log, username=username)

    # 3. 立即返回响应（不等写日志完成）
    return {"msg": "注册成功，后台正在记录日志..."}




@router.put("/update_item1/{id}",summary="更新项目", description="更新项目",operation_id="update_item1")
def update_item1(obj: dict):
    json_compatible_item_data = jsonable_encoder(obj)
    return JSONResponse(content=json_compatible_item_data)



'''
你想返回…	使用响应类
JSON 数据（默认）	JSONResponse（无需显式指定）
HTML 页面	HTMLResponse
纯文本	PlainTextResponse
重定向到其他 URL	RedirectResponse
大文件或流数据	StreamingResponse
下载文件	FileResponse

'''


@router.get("/html", response_class=HTMLResponse)
async def get_html():
    html_content = """
    <html>
        <head><title>你好，FastAPI！</title></head>
        <body>
            <h1>这是一个 HTML 页面</h1>
            <p>支持中文！</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

'''
RedirectResponse - 重定向
'''
from fastapi.responses import RedirectResponse

@router.get("/old-page")
async def redirect_to_new():
    return RedirectResponse("/new-page")

@router.get("/new-page")
async def new_page():
    return {"message": "你已被重定向到这里！"}

'''
StreamingResponse - 流式传输
适用于大文件或实时数据流（如日志、视频、CSV 文件等），可以边生成数据边发送，节省内存
'''
import asyncio
from fastapi.responses import StreamingResponse
async def slow_numbers(minimum, maximum):
    yield "开始生成数字...\n"
    await asyncio.sleep(0.5)
    for number in range(minimum, maximum + 1):
        yield str(number) + "\n"
        await asyncio.sleep(0.5)

@router.get("/stream-numbers")
async def stream_numbers():
    # 生成器函数作为内容
    return StreamingResponse(slow_numbers(1, 10), media_type="text/plain")


'''
FileResponse - 返回文件
用于返回一个文件（如图片、PDF、ZIP 等），支持自动处理大文件和断点续传。
'''
from fastapi.responses import FileResponse

@app.get("/download")
async def download_file():
    file_path = "example.pdf"
    return FileResponse(
        path=file_path,
        media_type='application/pdf',
        filename="报告.pdf"
    )



















