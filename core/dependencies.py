# 这就是一个依赖项函数
# 它可以接收查询参数、请求体、Header 等，就像路径操作函数一样
from typing import Union
from fastapi import Depends, HTTPException, status

async def common_parameters(
    q: Union[str, None] = None,
    skip: int = 0,
    limit: int = 100
):
    # 这里可以包含任何业务逻辑
    return {"q": q, "skip": skip, "limit": limit} # 返回结果

# 第 1 层：最基础的依赖 - 获取数据库连接
'''
在 FastAPI 的依赖项中，yield 就像一个“暂停键”。它先交出你需要的资源（如数据库连接），
让你的路径函数去使用；等路径函数用完（或出错）后，它再“恢复”执行，确保把资源安全地清理掉（如关闭连接）。
'''
def get_db():
    print("Opening database connection...")
    db = "DB_CONNECTION"  # 模拟数据库连接
    try:
        yield db
    finally:
        print("Closing database connection...")

# 第 2 层：依赖于 get_db - 获取当前登录用户
def get_current_user(
    db = Depends(get_db),          # ✅ 依赖项函数也可以有 Depends 参数
    token: str = "mock_token"     # 模拟从请求中获取 token
):
    print(f"Authenticating user with token: {token} using DB: {db}")
    # 模拟查询数据库获取用户
    user = {"id": 1, "username": "alice", "role": "admin", "db": db}
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

# 第 3 层：依赖于 get_current_user - 检查是否为管理员
def require_admin(
    current_user = Depends(get_current_user)  # ✅ 依赖于另一个依赖项
):
    print(f"Checking if user {current_user['username']} is admin...")
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user  # 返回用户信息，供上层使用