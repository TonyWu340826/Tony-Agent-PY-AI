# utils/entity_loader.py
import importlib.util
import inspect
from pydantic import BaseModel
import typing


def load_sql_entities(file_path: str):
    """动态加载 sql_entity.py 文件，读取所有 Pydantic 实体类的字段信息"""
    spec = importlib.util.spec_from_file_location("sql_entity", file_path)
    sql_entity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sql_entity)

    entities = {}
    for name, obj in inspect.getmembers(sql_entity, inspect.isclass):
        if issubclass(obj, BaseModel) and obj is not BaseModel:
            fields = []
            for field_name, field_info in obj.model_fields.items():
                annotation = field_info.annotation
                type_str = _get_type_name(annotation)

                f = {
                    "name": field_name,
                    "type": type_str,
                    "desc": field_info.description or "",
                    "default": field_info.default,
                }
                fields.append(f)
            entities[name] = fields
    return entities


def _get_type_name(annotation):
    """从注解中提取类型名，支持 Optional、Union 等，但优先返回实际类型"""
    if hasattr(annotation, '__origin__'):
        origin = annotation.__origin__
        args = annotation.__args__

        # 处理 Optional[T] -> T
        if origin is type(None):  # Optional[T]
            return str(args[0].__name__) if args else "unknown"

        # 处理 Union[T, None] -> T
        elif origin is typing.Union:
            # 如果是 Union[T, None]，则返回 T
            if len(args) == 2 and type(None) in args:
                for arg in args:
                    if arg is not type(None):
                        return getattr(arg, '__name__', str(arg))
            else:
                return str(origin.__name__)

        # 处理 List[T]
        elif origin is typing.List:
            return f"list[{args[0].__name__}]" if args else "list"

        # 处理 Dict[K, V]
        elif origin is typing.Dict:
            return f"dict[{args[0].__name__}, {args[1].__name__}]" if len(args) == 2 else "dict"

        else:
            return str(origin.__name__)
    else:
        return getattr(annotation, '__name__', str(annotation))