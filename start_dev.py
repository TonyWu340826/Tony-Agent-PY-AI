#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开发环境启动脚本
自动加载 .env.dev 配置文件
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
    
    # 设置开发环境变量（会被 .env.dev 中的配置覆盖）
    os.environ.setdefault("ENVIRONMENT", "dev")
    os.environ.setdefault("DEBUG", "True")
    
    # 设置编码
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    
    # 为Python 3.13兼容性，禁用eager_start特性
    os.environ.setdefault("PYTHONASYNCIOTASKS", "0")
    
    # 设置日志
    setup_logging()
    
    print("🔧 开发环境启动配置:")
    print(f"  环境: {os.environ.get('ENVIRONMENT', '未设置')}")
    print(f"  Debug模式: {os.environ.get('DEBUG', '未设置')}")
    print(f"  编码: {os.environ.get('PYTHONIOENCODING', '未设置')}")
    print(f"  PYTHONASYNCIOTASKS: {os.environ.get('PYTHONASYNCIOTASKS', '未设置')}")
    print(f"  Python路径: {sys.executable}")
    
    # 验证配置文件加载情况
    print("\n📋 配置文件状态:")
    print(f"  .env 存在: {os.path.exists('.env')}")
    print(f"  .env.dev 存在: {os.path.exists('.env.dev')}")
    
    # 启动应用
    try:
        print("\n🚀 正在启动应用...")
        # 使用 uvicorn 直接启动
        import uvicorn
        
        # 导入配置验证加载情况
        from config.config import settings
        print(f"✅ 配置加载验证 - Service Name: {settings.SC_NAME}")
        
        # 启动应用
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8889, 
            reload=os.getenv("RELOAD", "true").lower() == "true",
            log_level="debug"
        )
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()