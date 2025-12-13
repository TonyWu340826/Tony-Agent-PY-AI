# demo_ctl.py
from fastapi import APIRouter
from core.logger import logger
import asyncio

from dto.user_model import UserCreate

"""
@author: yunshan
This is a demo of how to use modular routes in FastAPI.
"""
router = APIRouter()


@router.get("/query")
async def root():
    logger.info("欢迎访问python项目!")
    await asyncio.sleep(1)
    return {"message": "Welcome to FastAPI with modular routes!"}

@router.get("/hello/{name}", tags=["测试接口"])
async def say_hello(name: str):
    logger.info(f"welcome to FastAPI with modular routes!>>>>>{name}")
    return {"message": f"Hello {name}"}

@router.get("/items/{item_id}", tags=["2个入参"])
async def read_item(item_id: int, q: str = None):
    logger.info("welcome to FastAPI with modular routes!")
    return {"item_id": item_id, "q": q}

@router.post("/adduser/{user_id}", tags=["2个入参"])
def add_user(user_id: int, user_name: str):
    logger.info("welcome to FastAPI with modular routes!" + str(user_id))
    return {"user_id": user_id, "user_name": user_name}

@router.post("/adduser", tags=["入参是对象"])
def add_user(user: UserCreate):
    # user 是自动解析后的对象，可以直接用 user.user_name 等
    print(f"Name: {user.user_name}")
    print(f"Email: {user.email}")
    print(f"Age: {user.age}")
    print(f"Active: {user.is_active}")

    return {
        "message": "User created",
        "user": user.dict()  # 转成字典返回
    }









