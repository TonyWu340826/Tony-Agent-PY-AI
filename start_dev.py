#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开发环境启动脚本
解决 debug 启动失败的问题
"""

import os
import sys
import signal
import logging

def signal_handler(sig, frame):
    print('\n👋 应用已停止')
    sys.exit(0)

def setup_logging():
    """设置日志配置"""
    # 设置根日志记录器
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置第三方库的日志级别，避免过多噪音
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    print("📝 日志配置已完成")

def main():
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 设置环境变量
    os.environ["ENVIRONMENT"] = "dev"
    os.environ["DEBUG"] = "True"
    
    # 设置编码
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # 为Python 3.13兼容性，禁用eager_start特性
    os.environ["PYTHONASYNCIOTASKS"] = "0"
    
    # 设置日志
    setup_logging()
    
    print("🔧 开发环境启动配置:")
    print(f"  环境: {os.environ.get('ENVIRONMENT', '未设置')}")
    print(f"  Debug模式: {os.environ.get('DEBUG', '未设置')}")
    print(f"  编码: {os.environ.get('PYTHONIOENCODING', '未设置')}")
    print(f"  PYTHONASYNCIOTASKS: {os.environ.get('PYTHONASYNCIOTASKS', '未设置')}")
    print(f"  Python路径: {sys.executable}")
    
    # 启动应用
    try:
        print("🚀 正在启动应用...")
        # 使用 uvicorn 直接启动，修复与 Python 3.13 的兼容性问题
        import uvicorn
        
        # 修复 uvicorn 与 Python 3.13 的兼容性问题
        try:
            # 尝试使用新的参数
            uvicorn.run("main:app", host="0.0.0.0", port=8889, reload=True, log_level="debug")
        except TypeError as e:
            if "loop_factory" in str(e):
                # 如果是因为 loop_factory 参数导致的错误，使用旧的方式
                import asyncio
                
                if sys.version_info >= (3, 13):
                    # Python 3.13+ 的处理方式
                    async def serve_app():
                        config = uvicorn.Config("main:app", host="0.0.0.0", port=8889, reload=True, log_level="debug")
                        server = uvicorn.Server(config)
                        await server.serve()
                    
                    asyncio.run(serve_app())
                else:
                    # 其他版本使用原始方式
                    uvicorn.run("main:app", host="0.0.0.0", port=8889, reload=True, log_level="debug")
            else:
                # 其他类型的 TypeError，重新抛出
                raise
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()