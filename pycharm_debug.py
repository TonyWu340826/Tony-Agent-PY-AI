#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyCharm 调试启动脚本
专门用于解决 PyCharm 与 Python 3.13 兼容性问题
"""

import os
import sys

def setup_pycharm_debug_env():
    """
    设置 PyCharm 调试环境
    """
    # 设置环境变量以避免调试器问题
    os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # 设置开发环境
    os.environ['ENVIRONMENT'] = 'dev'
    os.environ['DEBUG'] = 'True'
    
    print("🔧 PyCharm 调试环境设置:")
    print(f"  环境: {os.environ.get('ENVIRONMENT')}")
    print(f"  Debug模式: {os.environ.get('DEBUG')}")
    print(f"  PYDEVD_DISABLE_FILE_VALIDATION: {os.environ.get('PYDEVD_DISABLE_FILE_VALIDATION')}")
    print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")
    print(f"  PYTHONUNBUFFERED: {os.environ.get('PYTHONUNBUFFERED')}")

def start_application():
    """
    启动应用程序
    """
    try:
        print("🚀 正在启动 FastAPI 应用...")
        from main import app
        import uvicorn
        
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
                
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 PyCharm 调试启动脚本")
    print("=" * 50)
    
    # 设置调试环境
    setup_pycharm_debug_env()
    
    print("\n" + "=" * 50)
    
    # 启动应用
    start_application()