@echo off
chcp 65001 >nul
title EmailAssistant - 公网 MCP Server
cd /d "%~dp0"

echo ============================================================
echo    EmailAssistant 公网 MCP Server 启动器
echo ============================================================
echo.

:: 检查配置文件
if not exist config.json (
    echo [错误] 未找到 config.json，请先运行 install.bat
    pause
    exit /b 1
)

:: 启动 API 服务（后台）
echo [1/3] 启动 API 服务 (端口 8200)...
start "EA-API" /min python run_api.py
timeout /t 3 /nobreak >nul

:: 启动 MCP SSE 服务 + ngrok 隧道
echo [2/3] 启动 MCP SSE 服务 + ngrok 公网隧道...
echo.
python start_public.py

:: 退出时清理
echo.
echo 正在关闭所有服务...
taskkill /fi "WINDOWTITLE eq EA-API" /f >nul 2>&1
echo 已退出。
pause
