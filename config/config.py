# config/config.py
import os
import yaml
from dotenv import load_dotenv
from pydantic.v1 import BaseSettings

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.yml")

class Config:
    def __init__(self):
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def get(self, key, default=None):
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

# 创建全局实例
config = Config()



#读取配置
# 👇 调试：确认当前工作目录和 .env 是否存在
print("🔍 当前工作目录:", os.getcwd())
print("📄 .env 文件是否存在:", os.path.exists(".env"))

# 👇 第一步：先加载公共配置（如果存在）
load_dotenv(".env", verbose=True)  # 公共默认值

# 👇 第二步. 设置环境为 dev（你可以注释掉这行，用命令行传）
environment = os.getenv("ENVIRONMENT", "dev").lower()
env_file = f".env.{environment}"


# 👇 第三步：根据环境选择 .env 文件
env_file = f".env.{environment}"
print(f"🌍 当前环境: {environment}")
print(f"📁 正在加载配置文件: {env_file}")

if os.path.exists(env_file):
    load_dotenv(env_file, override=True)  # 覆盖公共配置
    print(f"✅ 已加载: {env_file}")
else:
    print(f"❌ 配置文件不存在: {env_file}")
    print(f"⚠️  使用默认环境变量或公共配置")




class Settings(BaseSettings):
    app_name: str = "Awesome API"
    admin_email: str
    items_per_user: int = 50
    database_url: str
    debug: bool = False
    SC_NAME: str

    # model_config = {"env_file": ".env"}  # 可以保留，但 load_dotenv() 更可靠
    # 保留也可以，但手动 load_dotenv() 更保险
settings = Settings()



# 👇 调试：确认是否读到值
print("✅ Settings 加载成功！")
print(f"  App Name: {settings.app_name}")
print(f"  Admin Email: {settings.admin_email}")
print(f"  Database URL: {settings.database_url}")
print(f"  Debug: {settings.debug}")












