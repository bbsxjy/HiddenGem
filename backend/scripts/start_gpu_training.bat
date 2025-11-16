@echo off
REM GPU训练启动脚本

echo ========================================
echo 启动HiddenGem GPU训练
echo ========================================

REM 激活conda环境
call C:\ProgramData\miniconda3\condabin\conda.bat activate hiddengem_gpu

REM 测试GPU
echo.
echo [步骤1] 测试GPU配置...
python scripts\test_gpu.py

REM 开始训练
echo.
echo [步骤2] 开始训练...
python scripts\train_rl_production.py

pause
