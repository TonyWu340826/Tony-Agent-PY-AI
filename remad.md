# 部署前端准备流程
# author: 云杉 ， time: 2023-05-18

## #1: 写好 requirements.txt
# 工程所有的依赖版本清单
pip freeze > requirements.txt

## #2: 工程打包
Compress-Archive -Path * -DestinationPath fastApi_1.0.0_master.zip

## #3: 解压
unzip fastApi_1.0.0_master.zip -d myproject
cd fastApi_1.0.0_master

## #4: python环境
# Ubuntu/Debian 系统
apt update
apt install python3 python3-pip -y

# CentOS/RHEL 系统
yum update
yum install python3 python3-pip -y

## #5: 验证依赖
pip3 install -r requirements.txt

## #6: 启动
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 > app.log 2>&1 &

| 参数 | 说明 |
|------|------|
| main:app | 加载 main.py，使用变量 app |
| --host 0.0.0.0 | 允许外部访问（不只是本地） |
| --port 8000 | 监听 8000 端口 |
| --workers 1 | 启动 1 个 worker（如果你 CPU 核心多，可以改 --workers 4） |
| nohup ... & | 让程序在后台运行，关闭终端也不影响 |
| > app.log 2>&1 | 把日志保存到 app.log 文件 |

## #启动脚本
#!/bin/bash

# FastAPI 一键启动脚本
# 用法: bash start.sh

echo "🚀 开始启动 FastAPI 项目..."

# 进入项目目录
cd /root/fastApiProject-01

# 检查是否需要安装依赖
if [ ! -f "requirements.txt" ]; then
    echo "❌ 找不到 requirements.txt，检查项目路径！"
    exit 1
fi

# 安装依赖（首次运行时）
if ! pip show fastapi > /dev/null 2>&1; then
    echo "📦 首次运行，正在安装依赖..."
    pip install -r requirements.txt
fi

# 启动 Uvicorn（后台运行）
echo "🔥 启动 Uvicorn..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 > app.log 2>&1 &

# 获取进程 ID
PID=$!

# 等待几秒看是否启动成功
sleep 3

# 检查进程是否还在
if ps -p $PID > /dev/null; then
    echo "✅ 启动成功！"
    echo "📄 日志文件: app.log"
    echo "🌐 访问地址: http://你的服务器IP:8000/docs"
    echo "mPid: $PID"
else
    echo "❌ 启动失败，请查看日志: tail -f app.log"
fi