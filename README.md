# FastAPI 项目

## 项目简介
这是一个基于 FastAPI 的 Web 项目，包含用户管理、学生管理等功能模块。

## 环境要求
- Python 3.8+
- MySQL 8.0+ (或兼容数据库)

## 安装依赖
```bash
pip install -r requirements.txt
```

## 启动项目

### 开发环境启动
```bash
# 方法1: 使用启动脚本 (推荐)
python start_dev.py

# 方法2: 使用 PowerShell 脚本 (Windows)
.\start-dev.ps1

# 方法3: 直接启动
python main.py
```

### PyCharm 调试启动
如果在 PyCharm 中进行调试时遇到 `isAlive()` 错误或 uvicorn 兼容性问题，请使用以下方法：

1. 运行修复脚本（只需运行一次）：
   ```bash
   python fix_pydev_debug.py
   ```

2. 使用专门的调试启动脚本：
   ```bash
   python pycharm_debug.py
   ```

3. 或者使用开发环境启动脚本：
   ```bash
   python start_dev.py
   ```

4. 或者在 PyCharm 中配置运行参数：
   - Script path: `D:\coding\AI-CODING\fastApiProject-01\pycharm_debug.py`
   - Environment variables:
     - `PYDEVD_DISABLE_FILE_VALIDATION=1`
     - `PYTHONIOENCODING=utf-8`
     - `PYTHONUNBUFFERED=1`

### 生产环境启动
```bash
# 方法1: 使用 uvicorn 命令（推荐）
uvicorn main:app --host 0.0.0.0 --port 8889 --workers 4

# 方法2: 使用专门的生产环境启动脚本
python start_prod.py

# 方法3: 设置环境变量后运行主文件
ENVIRONMENT=prod PORT=8889 WORKERS=4 python main.py

# Windows PowerShell 环境下使用:
$env:ENVIRONMENT="prod"
$env:PORT="8889"
$env:WORKERS="4"
python main.py
```

## 项目结构
```
.
├── config/           # 配置文件
├── ctl/              # 控制器
├── dto/              # 数据传输对象
├── model/            # 数据模型
├── repository/       # 数据访问层
├── service/          # 业务逻辑层
├── static/           # 静态文件
├── templates/        # 模板文件
├── main.py           # 主入口文件
└── app.py            # 应用核心文件
```

## API 文档
启动项目后访问:
- Swagger UI: http://localhost:8889/docs
- ReDoc: http://localhost:8889/redoc

## 常见问题解决

### Debug 启动失败
如果遇到 debug 启动失败的问题，请使用以下方法之一:

1. 使用专门的启动脚本:
   ```bash
   python start_dev.py
   ```

2. 检查端口占用:
   ```bash
   netstat -ano | findstr :8889
   ```

3. 检查环境变量配置是否正确

### 数据库连接问题
确保数据库配置正确，并且数据库服务正在运行。