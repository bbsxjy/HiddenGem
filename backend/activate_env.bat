@echo off
echo Activating hiddengem_gpu environment...
call C:\ProgramData\miniconda3\condabin\conda.bat activate hiddengem_gpu
echo Environment activated!
echo Python version:
python --version
echo PyTorch version:
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
