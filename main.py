# main.py
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import config
from ctl.routers import api_router

app = FastAPI(
    title="ChimichangApp",                    # 标题
    description="学习代码",                  # 描述（支持 Markdown）
    summary="Deadpool 的最爱应用",             # 简介
    version="1.0.0",                          # 版本号
    terms_of_service="http://example.com/terms/",  # 服务条款链接
    contact={                                 # 联系方式
        "name": "开发云杉",
        "url": "http://mywebsite.com/contact/",
        "email": "li@example.com",
    },
    license_info={                            # 许可证
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# ========= 挂载路由，并统一添加 /api 前缀 =========
app.include_router(
    api_router,
    prefix="/api"
)

# 挂载上传目录作为静态文件服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ======== 打印当前注册的路由 ========
print("🔍 当前注册的路由：")
for route in app.routes:
    if hasattr(route, "path"):
        methods = getattr(route, "methods", "N/A")
        if methods != "N/A":
            methods = ", ".join(sorted(methods))
        print(f"  → {route.name} [{methods}] = {route.path}")


# ======== 打印配置 ========
env = config.get("app.profile", "dev")
log_level = config.get("app.log_level", "info")
db_url = config.get("database.url")

print(f"当前环境: {env}")
print(f"日志级别: {log_level}")


# ===================================================
# 🚀 主程序入口：这里是唯一可以"设置环境"的地方
# ===================================================
if __name__ == "__main__":
    import uvicorn
    
    # ✅ 明确在这里设置环境（你可以注释/修改这行来切换环境）
    os.environ["ENVIRONMENT"] = "dev"  # 👈 开发时切换这里，或用命令行传
    
    # 💡 提示：你也可以注释上一行，改用命令行传：
    #       ENVIRONMENT=prod python main.py
    
    # 修复 uvicorn 与 Python 3.13 的兼容性问题
    try:
        # 尝试使用新的参数
        uvicorn.run("main:app", host="127.0.0.1", port=8889, reload=False)
    except TypeError as e:
        if "loop_factory" in str(e):
            # 如果是因为 loop_factory 参数导致的错误，使用旧的方式
            import asyncio
            import sys
            
            if sys.version_info >= (3, 13):
                # Python 3.13+ 的处理方式
                async def serve_app():
                    config = uvicorn.Config("main:app", host="127.0.0.1", port=8889, reload=False)
                    server = uvicorn.Server(config)
                    await server.serve()
                
                asyncio.run(serve_app())
            else:
                # 其他版本使用原始方式
                uvicorn.run("main:app", host="127.0.0.1", port=8889, reload=False)
        else:
            # 其他类型的 TypeError，重新抛出
            raise