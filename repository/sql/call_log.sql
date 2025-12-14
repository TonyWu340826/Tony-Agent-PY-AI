-- sql/call_log.sql

-- name: create_call_log_table
CREATE TABLE IF NOT EXISTS t_call_log (
  id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键，自增唯一ID',
  request_id VARCHAR(36) NOT NULL COMMENT '全局请求ID（UUID），关联同一用户指令的所有步骤',
  stage VARCHAR(50) NOT NULL COMMENT '执行阶段，如 planning / execution / retry / correction',
  step_order INT NOT NULL COMMENT '步骤序号，表示该请求中的第几步（从1开始）',
  operation TEXT NOT NULL COMMENT '操作描述，如 调用LLM生成计划、执行POST /users',
  input_data LONGTEXT COMMENT '输入数据（JSON格式），如 LLM 输入 prompt 或 API 请求体',
  output_data LONGTEXT COMMENT '输出数据（JSON格式），如 LLM 返回的 plan 或 API 响应体',
  status VARCHAR(20) NOT NULL COMMENT '状态：success / failed / retrying / corrected',
  error_message TEXT COMMENT '错误详情（仅当 status=failed 时有值）',
  execution_time INT DEFAULT NULL COMMENT '执行耗时（毫秒）',
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  endpoint_path VARCHAR(255) DEFAULT NULL COMMENT '被调用的API路径（如 /users）',
  endpoint_method VARCHAR(10) DEFAULT NULL COMMENT 'HTTP方法（如 POST, GET）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI Agent 调用日志表：记录自然语言指令执行的全链路步骤';

-- name: insert_call_log
INSERT INTO t_call_log (
    request_id, stage, step_order, operation, input_data, output_data, 
    status, error_message, execution_time, timestamp, endpoint_path, endpoint_method
) VALUES (
    :request_id, :stage, :step_order, :operation, :input_data, :output_data, 
    :status, :error_message, :execution_time, :timestamp, :endpoint_path, :endpoint_method
);

-- name: get_call_logs_by_request_id
SELECT * FROM t_call_log 
WHERE request_id = :request_id 
ORDER BY step_order;

-- name: get_all_call_logs
SELECT * FROM t_call_log 
ORDER BY timestamp DESC, step_order 
LIMIT :limit OFFSET :offset;

-- name: delete_call_logs_by_request_id
DELETE FROM t_call_log 
WHERE request_id = :request_id;