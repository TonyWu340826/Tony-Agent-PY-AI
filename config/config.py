# config/config.py
import os
import yaml
from dotenv import load_dotenv
from pydantic.v1 import BaseSettings
from urllib.parse import quote_plus

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


# 配置加载逻辑 - 支持多环境配置文件
print("🔍 当前工作目录:", os.getcwd())

# 1. 先加载公共配置文件（如果存在）
if os.path.exists(".env"):
    load_dotenv(".env", verbose=True)
    print("✅ 已加载公共配置文件: .env")

# 2. 根据环境变量确定配置文件
environment = os.getenv("ENVIRONMENT", "dev").lower()
env_file = f".env.{environment}"

print(f"🌍 当前环境: {environment}")
print(f"📁 正在加载配置文件: {env_file}")

# 3. 加载特定环境配置文件（会覆盖公共配置）
if os.path.exists(env_file):
    load_dotenv(env_file, override=True)
    print(f"✅ 已加载环境配置文件: {env_file}")
else:
    print(f"⚠️  环境配置文件不存在: {env_file}")
    print("💡 将使用公共配置或默认值")

# 4. 验证关键配置是否加载成功
print("\n📋 配置加载验证:")
print(f"  SC_NAME: {os.getenv('SC_NAME', '未设置')}")
print(f"  APP_NAME: {os.getenv('APP_NAME', '未设置')}")
print(f"  DEBUG: {os.getenv('DEBUG', '未设置')}")
print(f"  DATABASE_URL: {'已设置' if os.getenv('DATABASE_URL') else '未设置'}")


class Settings(BaseSettings):
    app_name: str = os.getenv("APP_NAME", "Awesome API")
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    items_per_user: int = 50
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    SC_NAME: str = os.getenv("SC_NAME", "DefaultService")
    
    @property
    def database_url(self) -> str:
        # 优先级：环境变量 > config.yml > 默认值
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
            
        # 从config.yml读取数据库配置
        db_config = config.get("database")
        if db_config:
            encoded_password = quote_plus(db_config['password'])
            return (
                f"{db_config['dialect']}+{db_config['driver']}://"
                f"{db_config['username']}:{encoded_password}@"
                f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
                f"?charset={db_config['charset']}"
            )
        return ""

# 创建Settings实例
settings = Settings()

print(f"\n✅ Settings 配置加载完成!")
print(f"  App Name: {settings.app_name}")
print(f"  Admin Email: {settings.admin_email}")
print(f"  Service Name: {settings.SC_NAME}")
print(f"  Debug Mode: {settings.debug}")
print(f"  Database URL: {'已配置' if settings.database_url else '未配置'}")