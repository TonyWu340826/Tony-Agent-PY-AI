# database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config.config import config
import os


def make_mysql_url():
    db = config.get("database")
    return (
        f"{db['dialect']}+{db['driver']}://"
        f"{db['username']}:{db['password']}@"
        f"{db['host']}:{db['port']}/{db['database']}"
        f"?charset={db['charset']}"
    )

    # 创建引擎


engine = create_engine(
    make_mysql_url(),
    echo=config.get("database.echo", True),
    pool_size=5,
    max_overflow=10
)


# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 工具函数：执行 SQL 并返回结果
def execute_sql(sql: str, params: dict = None, fetch: str = None):
    """
    执行 SQL
    :param sql: SQL 语句
    :param params: 参数
    :param fetch: None=无返回, "one", "all"
    """
    db = SessionLocal()
    try:
        result = db.execute(text(sql), params or {})
        data = None
        if fetch == "one":
            row = result.fetchone()
            data = row._asdict() if row else None
        elif fetch == "all":
            data = [row._asdict() for row in result.fetchall()]
        
        db.commit()
        return data
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()