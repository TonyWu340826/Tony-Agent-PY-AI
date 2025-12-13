# PowerShell 启动脚本
# 解决 debug 启动失败的问题

Write-Host "🔧 开发环境启动配置:" -ForegroundColor Green
Write-Host "  环境: dev" -ForegroundColor Cyan
Write-Host "  Debug模式: True" -ForegroundColor Cyan
Write-Host "  编码: utf-8" -ForegroundColor Cyan

# 设置环境变量
$env:ENVIRONMENT = "dev"
$env:DEBUG = "True"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "🚀 正在启动应用..." -ForegroundColor Green

# 启动应用
try {
    python start_dev.py
} catch {
    Write-Host "❌ 启动失败: $_" -ForegroundColor Red
    exit 1
}