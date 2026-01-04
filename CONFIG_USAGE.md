# 多环境配置使用说明

## 配置文件结构

项目支持多种环境的配置文件：

```
.env              # 公共配置（所有环境共享）
.env.dev          # 开发环境配置
.env.test         # 测试环境配置  
.env.prod         # 生产环境配置
```

## 配置加载优先级

配置加载遵循以下优先级（后面的会覆盖前面的）：

1. `.env` (公共配置)
2. `.env.{environment}` (环境特定配置)
3. 环境变量
4. 代码中的默认值

## 启动方式

### 1. 开发环境启动（推荐）

```bash
# 自动加载 .env.dev 配置
python start_dev.py
```

### 2. 生产环境启动

```bash
# 自动加载 .env.prod 配置
python start_prod.py
```

### 3. 手动指定环境

```bash
# Windows PowerShell
$env:ENVIRONMENT="dev"
python main.py

# Linux/Mac
ENVIRONMENT=dev python main.py
```

## .env.dev 配置示例

```env
# 服务基本信息
SC_NAME=MyDevService
APP_NAME=My Development App
ADMIN_EMAIL=dev@myapp.com
DEBUG=True

# 环境配置
ENVIRONMENT=dev
LOG_LEVEL=debug
RELOAD=true

# 数据库配置
DATABASE_URL=mysql://root:password@localhost:3306/mydb

# API密钥配置
DASHSCOPE_API_KEY=your_dashscope_key
CHAT-GPT_API_KEY=your_chatgpt_key
DEEPSEEK_API_KEY=your_deepseek_key

# Coze配置
coze_api_token=your_coze_token
coze_autoCase_workflow_id=workflow_id_1
coze_caseCheck_workflow_id=workflow_id_2
```

## 验证配置加载

运行测试脚本验证配置是否正确加载：

```bash
python test_config_loading.py
```

## 在代码中使用配置

```python
from config.config import settings

# 访问配置项
print(f"Service Name: {settings.SC_NAME}")
print(f"Debug Mode: {settings.debug}")
print(f"Database URL: {settings.database_url}")
```

## 注意事项

1. **敏感信息保护**: 不要在版本控制系统中提交包含真实密钥的配置文件
2. **环境隔离**: 不同环境使用不同的配置文件
3. **配置覆盖**: 环境特定配置会覆盖公共配置
4. **启动脚本**: 推荐使用专门的启动脚本来确保正确的环境配置