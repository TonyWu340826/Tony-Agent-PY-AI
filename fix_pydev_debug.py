#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复 PyCharm 调试器与 Python 3.13 兼容性问题的脚本
"""

import os
import sys

def fix_pydev_compatibility():
    """
    修复 PyCharm 调试器与 Python 3.13 的兼容性问题
    主要问题是 isAlive() 方法已被弃用，应该使用 is_alive()
    """
    pycharm_helpers_path = r"D:\Python-app\PyCharm 2024.1.4\plugins\python\helpers\pydev\_pydev_bundle"
    pydev_file = os.path.join(pycharm_helpers_path, "pydev_is_thread_alive.py")
    
    if os.path.exists(pydev_file):
        try:
            # 读取原文件内容
            with open(pydev_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 isAlive() 为 is_alive()
            fixed_content = content.replace('t.isAlive()', 't.is_alive()')
            
            # 如果内容有变化，则写回文件
            if fixed_content != content:
                # 创建备份
                backup_file = pydev_file + ".backup"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 写入修复后的内容
                with open(pydev_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print(f"✅ 已修复 PyCharm 调试器兼容性问题")
                print(f"  原文件已备份为: {backup_file}")
                print(f"  修复内容: isAlive() -> is_alive()")
                return True
            else:
                print("ℹ️  文件已经是最新版本，无需修复")
                return True
                
        except Exception as e:
            print(f"❌ 修复过程中出现错误: {e}")
            return False
    else:
        print(f"❌ 未找到 PyCharm 调试器文件: {pydev_file}")
        return False

def setup_debug_environment():
    """
    设置调试环境变量
    """
    # 设置环境变量以避免调试器问题
    os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    print("🔧 调试环境设置:")
    print(f"  PYDEVD_DISABLE_FILE_VALIDATION: {os.environ.get('PYDEVD_DISABLE_FILE_VALIDATION')}")
    print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")

if __name__ == "__main__":
    print("🔧 正在修复 PyCharm 调试器兼容性问题...")
    
    # 设置调试环境
    setup_debug_environment()
    
    # 修复兼容性问题
    success = fix_pydev_compatibility()
    
    if success:
        print("\n✅ PyCharm 调试器修复完成!")
        print("现在可以正常进行 debug 启动了。")
    else:
        print("\n❌ 修复失败，请手动修复或升级 PyCharm 版本。")