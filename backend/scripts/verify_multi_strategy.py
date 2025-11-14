"""
验证多策略交易系统配置

检查所有关键文件和配置是否正确
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def check_file_exists(filepath: str, description: str):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"[OK] {description}: {filepath}")
        return True
    else:
        print(f"[FAIL] {description} 不存在: {filepath}")
        return False


def check_model_file():
    """检查RL模型文件"""
    model_path = "models/production/final_model.zip"
    return check_file_exists(model_path, "RL模型文件")


def check_strategy_files():
    """检查策略相关文件"""
    files = [
        ("trading/strategy_factory.py", "策略工厂"),
        ("trading/multi_strategy_manager.py", "多策略管理器"),
        ("api/routers/auto_trading.py", "自动交易路由"),
        ("api/services/auto_trading_service.py", "自动交易服务"),
    ]

    all_exist = True
    for filepath, desc in files:
        if not check_file_exists(filepath, desc):
            all_exist = False

    return all_exist


def check_imports():
    """检查关键模块能否正常导入"""
    print("\n检查模块导入...")

    try:
        from trading.strategy_factory import StrategyMode, StrategyFactory, CombinedStrategy
        print("[OK] strategy_factory 模块导入成功")

        # 检查策略模式定义
        modes = StrategyMode.get_all_modes()
        print(f"[OK] 定义了 {len(modes)} 个策略模式: {', '.join(modes)}")

    except ImportError as e:
        print(f"[FAIL] strategy_factory 模块导入失败: {e}")
        return False

    try:
        from trading.multi_strategy_manager import MultiStrategyManager, StrategyPerformance
        print("[OK] multi_strategy_manager 模块导入成功")
    except ImportError as e:
        print(f"[FAIL] multi_strategy_manager 模块导入失败: {e}")
        return False

    try:
        from api.services.auto_trading_service import auto_trading_service
        print("[OK] auto_trading_service 模块导入成功")
    except ImportError as e:
        print(f"[FAIL] auto_trading_service 模块导入失败: {e}")
        return False

    return True


def verify_strategy_modes():
    """验证策略模式配置"""
    print("\n验证策略模式配置...")

    try:
        from trading.strategy_factory import StrategyMode

        expected_modes = {
            'rl_only': '单RL模型',
            'llm_agent_only': '单LLM Agent',
            'llm_memory': 'LLM + Memory Bank',
            'rl_llm': 'RL + LLM',
            'rl_llm_memory': 'RL + LLM + Memory'
        }

        all_correct = True
        for mode_id, expected_name in expected_modes.items():
            mode_info = StrategyMode.get_mode_info(mode_id)
            if mode_info:
                actual_name = mode_info.get('name', '')
                if actual_name == expected_name:
                    print(f"[OK] {mode_id}: {actual_name}")
                else:
                    print(f"[FAIL] {mode_id}: 期望 '{expected_name}', 实际 '{actual_name}'")
                    all_correct = False
            else:
                print(f"[FAIL] {mode_id}: 模式信息不存在")
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"[FAIL] 验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("多策略交易系统验证")
    print("=" * 60)

    print("\n1. 检查文件存在性...")
    files_ok = check_strategy_files()

    print("\n2. 检查模型文件...")
    model_ok = check_model_file()

    print("\n3. 检查模块导入...")
    import_ok = check_imports()

    print("\n4. 验证策略模式...")
    modes_ok = verify_strategy_modes()

    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    print(f"文件检查: {'[OK] 通过' if files_ok else '[FAIL] 失败'}")
    print(f"模型文件: {'[OK] 存在' if model_ok else '[WARN] 不存在（训练后会生成）'}")
    print(f"模块导入: {'[OK] 通过' if import_ok else '[FAIL] 失败'}")
    print(f"策略配置: {'[OK] 通过' if modes_ok else '[FAIL] 失败'}")

    if files_ok and import_ok and modes_ok:
        print("\n[OK] 多策略交易系统配置正确！")
        print("\n下一步:")
        print("1. 确保RL模型已训练: models/production/final_model.zip")
        print("2. 启动后端服务: uvicorn main:app --reload")
        print("3. 启动前端服务: npm run dev")
        print("4. 在前端选择策略并启动自动交易")
        return 0
    else:
        print("\n[FAIL] 配置存在问题，请检查上述错误")
        return 1


if __name__ == "__main__":
    sys.exit(main())
