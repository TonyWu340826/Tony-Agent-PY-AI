#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生产环境启动脚本
"""

import os
import sys

def setup_production_env():
    """
    设置生产环境变量
    """
    # 设置生产环境
    os.environ['ENVIRONMENT'] = 'prod'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # 可以通过环境变量覆盖默认配置
    port = int(os.environ.get('PORT', 8889))
    workers = int(os.environ.get('WORKERS', 4))
    
    print("🔧 生产环境启动配置:")
    print(f"  环境: {os.environ.get('ENVIRONMENT')}")
    print(f"  端口: {port}")
    print(f"  工作进程数: {workers}")
    print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")

def start_production_server():
    """
    启动生产环境服务器
    """
    try:
        print("🚀 正在启动生产环境服务器...")
        
        # 导入 uvicorn
        import uvicorn
        
        # 获取配置
        port = int(os.environ.get('PORT', 8889))
        workers = int(os.environ.get('WORKERS', 4))
        
        # 使用 uvicorn 命令行方式启动（更适合生产环境）
        sys.argv = [
            'uvicorn',
            'main:app',
            '--host=0.0.0.0',
            f'--port={port}',
            f'--workers={workers}',
            '--log-level=info',
            '--access-log'
        ]
        
        from uvicorn.main import main
        main()
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 FastAPI 生产环境启动脚本")
    print("=" * 50)
    
    # 设置生产环境
    setup_production_env()
    
    print("\n" + "=" * 50)
    
    # 启动服务器
    start_production_server()