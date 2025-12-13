# app_sql.py —— 对话式 SQL 智能生成助手（支持表卡片、自然语言输入、AI 解析）
import streamlit as st
import pandas as pd
import requests
from model.dashscope_model import DashScopeModel
from utils.entity_loader import load_sql_entities
from core.logger import logger

# ======================
# 页面配置
# ======================
st.set_page_config(page_title="🧠 SQL 智能助手", layout="wide")
st.title("🧠 SQL 智能生成与执行助手")

BACKEND_URL = "http://localhost:8889/api/user/user/sql/exec"

# ======================
# 加载 ORM 实体定义
# ======================
try:
    entities = load_sql_entities("repository/entity/sql_entity.py")
except Exception as e:
    st.error(f"加载实体定义失败：{e}")
    st.stop()

if not entities:
    st.error("未加载到任何表结构，请检查实体文件。")
    st.stop()

# ======================
# 表选择（卡片形式）
# ======================
st.sidebar.header("📂 选择表")

selected_tables = []
for table_name in entities.keys():
    if st.sidebar.checkbox(table_name, key=f"chk_{table_name}"):
        selected_tables.append(table_name)

if not selected_tables:
    st.info("请至少选择一个表以继续。")
    st.stop()

# ======================
# 显示所选表结构（卡片式布局）
# ======================
st.subheader("📋 所选表结构")
with st.expander("📊 表结构详情（点击展开）"):
    if not selected_tables:
        st.info("暂未选择任何表。")
    else:
        # 每行最多显示 3 张卡片（可根据需要调整）
        cols_per_row = 10
        for i in range(0, len(selected_tables), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, tbl in enumerate(selected_tables[i:i + cols_per_row]):
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"#### 📄 `{tbl}`")
                        table_data = entities[tbl]
                        fields_info = []
                        for item in table_data:
                            if isinstance(item, dict):
                                fields_info.append({
                                    'name': item.get('name', 'unknown'),
                                    'type': item.get('type', 'unknown'),
                                    'desc': item.get('desc', ''),
                                })
                            else:
                                fields_info.append({'name': str(item), 'type': 'unknown', 'desc': ''})

                        if fields_info:
                            # 使用紧凑的 markdown 列表展示字段
                            for field in fields_info:
                                name = field['name']
                                ftype = field['type']
                                desc = field['desc'] or "—"
                                # 使用小号字体 + 灰色描述，提升可读性
                                st.markdown(
                                    f"<div style='font-size:0.95em; margin-bottom:8px;'>"
                                    f"<b>{name}</b> <span style='color:#888; font-size:0.9em;'>({ftype})</span><br>"
                                    f"<span style='color:#666; font-size:0.85em;'>{desc}</span>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                        else:
                            st.markdown("<i style='color:#999;'>无字段信息</i>", unsafe_allow_html=True)

# ======================
# 自然语言输入（对话式）
# ======================
st.subheader("💬 请输入你的 SQL 需求（例如：查询所有用户的姓名和年龄）")

user_prompt = st.text_area(
    "📝 描述你的查询需求",
    placeholder="例如：查一下 t_user 表中所有名字叫张三的人，返回姓名和年龄",
    height=100
)

# ======================
# 生成 SQL 按钮
# ======================
if st.button("🚀 生成 SQL"):
    if not user_prompt.strip():
        st.warning("请输入你的查询需求。")
    else:
        # 构建清晰的提示词
        table_structures = []
        for tbl in selected_tables:
            fields = entities[tbl]
            field_list = [f"{f['name']} ({f.get('desc', '')})" for f in fields]
            table_structures.append(f"'{tbl}': [{', '.join(field_list)}]")

        prompt = f"""
        - Role(角色): 数据库开发工程师  
        - Background（背景）: 用户需要根据指定的数据库表结构和业务需求，生成用于查询、插入、更新或删除数据的 SQL 语句。当前上下文提供了可用表、表结构及自然语言描述的需求。  
        - Profile(轮廓): 你是一位经验丰富的数据库开发工程师，精通 SQL 语言，熟悉 MySQL 5.7+ 的语法特性与最佳实践，能够基于有限信息推断合理的表关联关系和业务逻辑。  
        - Skills(技能): 熟练编写高效、安全、可维护的 SQL 语句，包括多表 JOIN、子查询、条件过滤、排序分页等；能根据模糊需求合理推导实现逻辑（如“最近”→按时间倒序+LIMIT）；注重字段限定、别名使用与性能优化。  
        - Goals(目标): 根据用户提供的表信息和自然语言需求，生成一条语法正确、逻辑严谨、执行高效且符合 MySQL 5.7+ 标准的 SQL 语句。  
        - Constrains（约束条件）:  
          1. 仅输出最终 SQL 语句，不得包含解释、注释、Markdown 或额外文本。  
          2. 语句末尾不得添加分号（;）。  
          3. 禁止使用 SELECT *，仅返回需求明确提及或逻辑必需的字段。  
          4. 多表操作时，基于惯例（主键为 id，外键为 {table_name}_id）推断 JOIN 条件；优先使用 INNER JOIN，仅当语义允许空值时使用 LEFT JOIN。  
          5. 所有表必须使用简洁别名（如 users → u），重复字段必须用别名限定（如 u.name）。  
          6. 对模糊表述（如“最近”“最多”“最新记录”）按常规业务逻辑实现（如 ORDER BY created_at DESC LIMIT 1）。  
          7. 确保语句可执行，避免歧义、无效引用或破坏数据完整性的操作。  
        - OutputFormat（输出格式）: 纯文本 SQL 语句，格式清晰、缩进合理、便于直接执行。  
        - Workflow(工作流程):  
          1. 解析用户需求，识别操作类型（SELECT/INSERT/UPDATE/DELETE）、目标表、关键字段及过滤条件。  
          2. 结合表结构与命名惯例，构建语句骨架，合理推断 JOIN 关系与 WHERE 条件。  
          3. 优化字段选择、别名使用与排序逻辑，确保语句简洁高效。  
        - Examples(实例):  
          - 查询用户姓名和邮箱：  
            SELECT name, email FROM users  
          - 插入新订单：  
            INSERT INTO orders (order_id, user_id, order_date, total_amount) VALUES (1, 1001, '2025-11-05', 99.99)  
          - 更新用户邮箱：  
            UPDATE users SET email = 'new_email@example.com' WHERE user_id = 1001  
          - 删除已取消订单：  
            DELETE FROM orders WHERE status = 'cancelled'  

        -【可用表】
        {", ".join(selected_tables)}

        -【表结构】
        {{{', '.join(table_structures)}}}

        -【用户需求】
        "{user_prompt}"

        请严格遵循上述角色设定与约束条件，直接输出符合要求的 SQL 语句。
        """

        logger.info(f"AI 提示词：{prompt}")
        try:
            model = DashScopeModel()
            sql_result = model.call(prompt)
            st.session_state["sql_result"] = sql_result
        except Exception as e:
            st.error(f"调用模型失败：{e}")

# ======================
# 显示 SQL 并执行
# ======================
if "sql_result" in st.session_state:
    st.subheader("📝 SQL 结果")
    sql_text = st.text_area(
        "可修改 SQL 后执行",
        st.session_state["sql_result"],
        height=150
    )

    if st.button("▶ 执行 SQL"):
        if not sql_text.strip():
            st.warning("SQL 不能为空")
        else:
            try:
                resp = requests.post(BACKEND_URL, json={"sql": sql_text})
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(data.get("msg", "执行成功"))
                    if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                        result_df = pd.DataFrame([{k: str(v) for k, v in row.items()} for row in data["data"]])
                        st.dataframe(result_df, use_container_width=True)
                    else:
                        st.info("查询成功，但无返回数据。")
                else:
                    st.error(f"执行失败：{resp.text}")
            except Exception as e:
                st.error(f"请求失败：{e}")
                logger.error(f"SQL 执行异常: {e}")