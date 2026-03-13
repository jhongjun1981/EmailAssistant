@echo off
chcp 65001 >nul
title AI 邮件助手
cd /d "%~dp0"
python main.py
pause
