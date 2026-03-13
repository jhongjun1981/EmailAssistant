@echo off
chcp 65001 >nul
title EmailAssistant
cd /d "%~dp0"

echo ============================================
echo    EmailAssistant 启动中...
echo ============================================
echo.

:: 检查配置文件
if not exist config.json (
    echo [错误] 未找到 config.json，请先运行 install.bat
    pause
    exit /b 1
)

:: 启动 API 服务（后台）
echo [1/2] 启动 API 服务 (端口 8200)...
start "EmailAssistant-API" /min python run_api.py
timeout /t 2 /nobreak >nul

:: 启动 GUI
echo [2/2] 启动 GUI...
python main.py

:: GUI 关闭后，关闭 API 服务
echo.
echo 正在关闭 API 服务...
taskkill /fi "WINDOWTITLE eq EmailAssistant-API" /f >nul 2>&1
echo 已退出。
