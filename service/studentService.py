
from core.logger import logger


class FixedContentQueryChecker:
    def __init__(self, fixed_content: str): # 初始化时接收配置
        self.fixed_content = fixed_content

    def __call__(self, q: str = ""): # ✅ 关键：实现 __call__ 方法
        logger.info("进入student...... %s", q)
        if q:
            logger.info("返回student...... %s", self.fixed_content in q)
            return self.fixed_content in q
        return False

# 创建依赖项实例 这里就是初始化
checker = FixedContentQueryChecker("bar")

'''
工作流程详解
以 Depends(FixedContentQueryChecker("bar")) 为例：

创建阶段：FixedContentQueryChecker("bar") 被执行，创建一个类实例。"bar" 作为 fixed_content 被保存在实例属性中。这个实例就是依赖项对象。
调用阶段：当有请求到达 /items/ 时，FastAPI 会“调用”这个依赖项对象。
执行 __call__：框架内部相当于执行 instance(q=query_param_from_request)。
参数注入：FastAPI 会像处理路径操作函数一样，解析 __call__ 方法的参数（如 q: str = ""），从请求中获取值并传入。
返回结果：__call__ 方法的返回值（True/False）被注入到路径操作函数的 fixed_content_in_q 参数中。
'''



