@echo off
chcp 65001 >nul
title EmailAssistant 安装程序
cd /d "%~dp0"

echo ============================================
echo    EmailAssistant 一键安装
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 显示 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [√] Python %PYVER%

:: 安装依赖
echo.
echo [1/3] 安装 Python 依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo [√] 依赖安装完成

:: 配置文件
echo.
echo [2/3] 检查配置文件...
if not exist config.json (
    copy config.example.json config.json >nul
    echo [√] 已创建 config.json（从模板复制）
    echo [!] 请编辑 config.json 填入你的 LLM API Key
) else (
    echo [√] config.json 已存在，跳过
)

:: MCP 配置提示
echo.
echo [3/3] MCP Server 配置...
echo.
echo 如需在 Claude Code 中使用，请在项目根目录的 .mcp.json 中添加:
echo.
echo   "email-assistant": {
echo     "command": "python",
echo     "args": ["%CD:\=/%/run_mcp.py"],
echo     "cwd": "%CD:\=/%",
echo     "env": {
echo       "EA_API_URL": "http://localhost:8200"
echo     }
echo   }
echo.

:: 完成
echo ============================================
echo    安装完成！
echo ============================================
echo.
echo 启动方式:
echo   方式1: 双击 start_all.bat（API + GUI 一起启动）
echo   方式2: python run_api.py（仅启动 API 服务，端口 8200）
echo   方式3: python main.py（仅启动 GUI）
echo.
pause
