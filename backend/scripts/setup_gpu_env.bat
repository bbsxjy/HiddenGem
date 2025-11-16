@echo off
REM GPU环境设置脚本 - Python 3.12 + CUDA

echo ========================================
echo 设置HiddenGem GPU训练环境
echo ========================================

REM 激活conda环境
call C:\ProgramData\miniconda3\condabin\conda.bat activate hiddengem_gpu

echo.
echo [1/4] 安装PyTorch GPU版本 (CUDA 12.1)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo [2/4] 安装stable-baselines3...
pip install stable-baselines3[extra]

echo.
echo [3/4] 安装其他依赖...
pip install gymnasium pandas numpy tushare akshare yfinance

echo.
echo [4/4] 验证GPU配置...
python -c "import torch; print(f'PyTorch版本: {torch.__version__}'); print(f'CUDA可用: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

echo.
echo ========================================
echo GPU环境设置完成！
echo ========================================
echo.
echo 使用方法:
echo   1. 激活环境: conda activate hiddengem_gpu
echo   2. 运行训练: python scripts/train_rl_production.py
echo.
pause
