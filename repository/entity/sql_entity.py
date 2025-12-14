from typing import Optional
from pydantic import BaseModel, Field


''''
"""用户表模型"""
'''
class t_user(BaseModel):

    id: int = Field(
        ...,
        description="主键ID",
        alias="id"  # 对应数据库字段名
    )

    name: Optional[str] = Field(
        None,
        description="用户名称",
        max_length=20,
        alias="name"  # 对应数据库字段名
    )

    address: Optional[str] = Field(
        None,
        description="用户地址",
        max_length=60,
        alias="address"  # 对应数据库字段名
    )

    sex: Optional[int] = Field(
        None,
        description="用户性别（0-女，1-男）",
        ge=0,
        le=1,
        alias="sex"  # 对应数据库字段名
    )



''''
"""用户组织表模型"""
'''
class t_user_org(BaseModel):

    id: int = Field(
        ...,
        description="主键ID",
        alias="id"  # 对应数据库字段名
    )

    name: Optional[str] = Field(
        None,
        description="组织名称",
        max_length=20,
        alias="name"  # 对应数据库字段名
    )
    user_id: int = Field(
        ...,
        description="用户ID",
        alias="user_id"  # 对应数据库字段名
    )

'''
组织表
说明：t_user_org.user_id 关联 t_user.id，t_user_org 可视为用户-组织中间表（若需多对多）；也可将 t_user.org_id 直接指向 t_org.id。此处保留 t_user_org 作为中间表更灵活。
'''
class t_org(BaseModel):
    id: int = Field(..., description="组织ID", alias="id")
    name: Optional[str] = Field(None, description="组织名称", max_length=50, alias="name")
    parent_id: Optional[int] = Field(None, description="父组织ID", alias="parent_id")


'''
角色表
'''
class t_role(BaseModel):
    id: int = Field(..., description="角色ID", alias="id")
    name: Optional[str] = Field(None, description="角色名称", max_length=30, alias="name")
    code: Optional[str] = Field(None, description="角色编码", max_length=30, alias="code")



'''
t_user_role —— 用户-角色关联表（多对多）
'''
class t_user_role(BaseModel):
    id: int = Field(..., description="主键ID", alias="id")
    user_id: int = Field(..., description="用户ID", alias="user_id")
    role_id: int = Field(..., description="角色ID", alias="role_id")


'''
t_permission —— 权限表
'''
class t_permission(BaseModel):
    id: int = Field(..., description="权限ID", alias="id")
    name: Optional[str] = Field(None, description="权限名称", max_length=50, alias="name")
    code: Optional[str] = Field(None, description="权限编码（如 user:delete）", max_length=50, alias="code")



'''
t_role_permission —— 角色-权限关联表（多对多）
'''
class t_role_permission(BaseModel):
    id: int = Field(..., description="主键ID", alias="id")
    role_id: int = Field(..., description="角色ID", alias="role_id")
    permission_id: int = Field(..., description="权限ID", alias="permission_id")


'''
t_menu —— 菜单表（前端路由/菜单项）
'''
class t_menu(BaseModel):
    id: int = Field(..., description="菜单ID", alias="id")
    name: Optional[str] = Field(None, description="菜单名称", max_length=30, alias="name")
    path: Optional[str] = Field(None, description="路由路径", max_length=100, alias="path")
    parent_id: Optional[int] = Field(None, description="父菜单ID", alias="parent_id")
    permission_code: Optional[str] = Field(None, description="关联的权限编码", max_length=50, alias="permission_code")



'''
t_role_menu —— 角色-菜单关联表（控制菜单可见性）
'''
class t_role_menu(BaseModel):
    id: int = Field(..., description="主键ID", alias="id")
    role_id: int = Field(..., description="角色ID", alias="role_id")
    menu_id: int = Field(..., description="菜单ID", alias="menu_id")





'''
t_dept —— 部门表（可与组织关联）
'''
class t_dept(BaseModel):
    id: int = Field(..., description="部门ID", alias="id")
    name: Optional[str] = Field(None, description="部门名称", max_length=50, alias="name")
    org_id: Optional[int] = Field(None, description="所属组织ID", alias="org_id")
'''
t_user_dept —— 用户-部门关联表
'''
class t_user_dept(BaseModel):
    id: int = Field(..., description="主键ID", alias="id")
    user_id: int = Field(..., description="用户ID", alias="user_id")
    dept_id: int = Field(..., description="部门ID", alias="dept_id")





'''
t_login_log —— 用户登录日志表（用于测试时间字段、聚合等）
'''
class t_login_log(BaseModel):
    id: int = Field(..., description="日志ID", alias="id")
    user_id: int = Field(..., description="用户ID", alias="user_id")
    login_time: Optional[str] = Field(None, description="登录时间（ISO8601格式）", alias="login_time")
    ip: Optional[str] = Field(None, description="登录IP", max_length=45, alias="ip")



'''
t_call_log —— AI Agent 调用日志表（记录自然语言指令执行的全链路步骤）
'''
class t_call_log(BaseModel):
    # 主键，自增唯一ID
    id: Optional[int] = Field(
        None,
        description="主键，自增唯一ID",
        alias="id"
    )

    # 全局请求ID（UUID），关联同一用户指令的所有步骤
    request_id: str = Field(
        ...,
        description="全局请求ID（UUID），关联同一用户指令的所有步骤",
        alias="request_id"
    )

    # 执行阶段，如 planning / execution / retry / correction
    stage: str = Field(
        ...,
        description="执行阶段，如 planning / execution / retry / correction",
        alias="stage"
    )

    # 步骤序号，表示该请求中的第几步（从1开始）
    step_order: int = Field(
        ...,
        description="步骤序号，表示该请求中的第几步（从1开始）",
        alias="step_order"
    )

    # 操作描述，如 调用LLM生成计划、执行POST /users
    operation: str = Field(
        ...,
        description="操作描述，如 调用LLM生成计划、执行POST /users",
        alias="operation"
    )

    # 输入数据（JSON格式），如 LLM 输入 prompt 或 API 请求体
    input_data: Optional[str] = Field(
        None,
        description="输入数据（JSON格式），如 LLM 输入 prompt 或 API 请求体",
        alias="input_data"
    )

    # 输出数据（JSON格式），如 LLM 返回的 plan 或 API 响应体
    output_data: Optional[str] = Field(
        None,
        description="输出数据（JSON格式），如 LLM 返回的 plan 或 API 响应体",
        alias="output_data"
    )

    # 状态：success / failed / retrying / corrected
    status: str = Field(
        ...,
        description="状态：success / failed / retrying / corrected",
        alias="status"
    )

    # 错误详情（仅当 status=failed 时有值）
    error_message: Optional[str] = Field(
        None,
        description="错误详情（仅当 status=failed 时有值）",
        alias="error_message"
    )

    # 执行耗时（毫秒）
    execution_time: Optional[int] = Field(
        None,
        description="执行耗时（毫秒）",
        alias="execution_time"
    )

    # 记录创建时间
    timestamp: Optional[str] = Field(
        None,
        description="记录创建时间",
        alias="timestamp"
    )

    # 被调用的API路径（如 /users）
    endpoint_path: Optional[str] = Field(
        None,
        description="被调用的API路径（如 /users）",
        alias="endpoint_path"
    )

    # HTTP方法（如 POST, GET）
    endpoint_method: Optional[str] = Field(
        None,
        description="HTTP方法（如 POST, GET）",
        alias="endpoint_method"
    )