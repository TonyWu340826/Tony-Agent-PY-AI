'''
OAuth2 作用域
'''
import secrets
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, HTTPBasicCredentials, HTTPBasic
from rich import status
from repository.crud import get_user_by_id




# 定义可用的 Scopes 及其描述
router = APIRouter()

'''
OAuth2 权限范围（Scopes）
在现代 Web 应用中，仅仅“登录”是不够的。我们还需要控制用户“能做什么”。
OAuth2 Scopes（权限范围） 就是用来解决这个问题的——它允许你为不同的用户或应用授予不同级别的访问权限。

实现基于 用户名/密码 的登录。
使用 JWT Token（Bearer Token） 进行认证。
利用 Scopes（权限范围） 实现细粒度权限控制（例如：只读、读写、管理员等）。
在 OpenAPI（Swagger UI）中支持 Token 认证和 Scope 选择。
'''


# 依赖：获取 token 和 user_id
def get_token_and_user_id_params(token: str, user_id: int):
    return {"token": token, "user_id": user_id}

# 依赖：验证 token 并返回用户
def get_current_user(dependency: dict = Depends(get_token_and_user_id_params)):
    user = get_user_by_id(dependency["user_id"]) # 拿出 user_id
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["address"] != dependency["token"]:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# 路由
@router.get("/demo/auth")
def get_users(user: dict = Depends(get_current_user)):
    return {"message": "你有权限访问", "data": user}


# 这些描述会显示在 Swagger UI 中
'''
作用：声明这是一个标准的 OAuth2 密码模式认证方案。
tokenUrl="token"：表示客户端应向 /token 接口请求 token。
scopes：定义了系统支持的所有权限范围及其描述，这些会显示在 Swagger UI 中，用于交互式测试。
'''
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "me": "Read your own info",
        "items": "Read items",
        "items:write": "Create and edit items",
    },
)


@router.post("/token")
async def login():
    return {
        "access_token": "fake-super-secret-token",
        "token_type": "bearer",
        "scopes": ["me", "items:read"]  # 👈 这个 token 只有这两个权限
    }


# 模拟：解析 token，返回用户的 scopes
def decode_token(token: str):
    # 真实项目中：用 JWT 解码
    # 这里模拟：假设 token 是 "johndoe"，他的权限是 ["me", "items"]
    if token == "johndoe":
        return {"username": "johndoe", "scopes": ["me", "items"]}
    elif token == "alice":
        return {"username": "alice", "scopes": ["me"]}  # alice 只有 me 权限
    else:
        return None


def require_scope(required_scope: str):
    def dependency(token: str = Depends(oauth2_scheme)):
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        if required_scope not in payload["scopes"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return payload  # 返回用户信息
    return dependency


@router.get("/users/me")
async def read_users_me(user: dict = Depends(require_scope("me"))):
    return {"username": user["username"]}


security = HTTPBasic()


# ✅ 直接在路由里写，不封装 Depends
@router.get("/api/data")
def get_data(credentials: HTTPBasicCredentials = Depends(security)):
    # 验证（用 secrets 比较）
    is_correct_user = secrets.compare_digest(credentials.username, "admin")
    is_correct_pass = secrets.compare_digest(credentials.password, "secret")

    if not (is_correct_user and is_correct_pass):
        raise HTTPException(401, "Unauthorized")

    return {"data": "ok"}


def verify_token(token: str = Depends(oauth2_scheme)):
    # 假设 token 是用户 ID
    try:
        user_id = int(token)
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(401, "User not found")
        return user  # 返回用户对象
    except ValueError:
        raise HTTPException(401, "Invalid token")

@router.get("/token/profile")
def get_profile(user: dict = Depends(verify_token)):
    return {"profile": user}















'''
路由	       方法	     认证方式	权限要求	说明
/token   	POST	无	无	返回模拟 token 及其 scopes
/users/me	GET	OAuth2 Bearer	me scope	只有带 me 权限的 token 可访问
/demo/auth	GET	自定义依赖	用户存在且 token 匹配 address	演示复合参数依赖
/api/data	GET	HTTP Basic	用户名=admin, 密码=secret	基础认证示例
/token/profile	GET	OAuth2 Bearer	token 能转为有效 user_id	演示 token → user 映射


'''




















