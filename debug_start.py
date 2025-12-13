#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug 启动脚本
用于解决 debug 启动失败的问题
"""

import os
import sys
import subprocess

def main():
    # 设置环境变量
    os.environ["ENVIRONMENT"] = "dev"
    os.environ["DEBUG"] = "True"
    
    # 设置编码
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    print("🔧 Debug 启动配置:")
    print(f"  环境: {os.environ.get('ENVIRONMENT', '未设置')}")
    print(f"  Debug模式: {os.environ.get('DEBUG', '未设置')}")
    print(f"  编码: {os.environ.get('PYTHONIOENCODING', '未设置')}")
    
    # 启动应用
    try:
        print("🚀 正在启动应用...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "127.0.0.1", 
            "--port", "8889",
            "--reload"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
        sys.exit(0)

if __name__ == "__main__":
    main()