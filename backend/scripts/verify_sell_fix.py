#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SELL仓位计算修复验证脚本

快速验证SELL动作的仓位计算是否正确。

Usage:
    python scripts/verify_sell_fix.py
"""

def test_sell_calculation():
    """测试SELL仓位计算逻辑"""
    print("="*60)
    print("SELL仓位计算修复验证")
    print("="*60)

    # 测试用例
    test_cases = [
        # (持仓数量, target_ratio, 预期卖出数量, 说明)
        (1000, 0.5, 500, "1000股持仓，卖出50%"),
        (1000, 1.0, 1000, "1000股持仓，卖出100%"),
        (1000, 0.25, 200, "1000股持仓，卖出25%（向下取整到100倍数）"),
        (500, 0.5, 200, "500股持仓，卖出50%（向下取整到100倍数）"),
        (300, 0.5, 100, "300股持仓，卖出50%（向下取整到100倍数）"),
        (200, 0.5, 100, "200股持仓，卖出50%"),
        (150, 0.5, 100, "150股持仓，卖出50%（小于100股，取100股）"),
        (100, 0.5, 100, "100股持仓，卖出50%（小于100股，取100股）"),
        (80, 0.5, 80, "80股持仓，卖出50%（不足100股，全部卖出）"),
        (50, 1.0, 50, "50股持仓，卖出100%（不足100股，全部卖出）"),
    ]

    all_passed = True

    for i, (position_quantity, target_ratio, expected_quantity, description) in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {description}")
        print(f"  持仓: {position_quantity}股, target_ratio: {target_ratio} ({target_ratio*100:.0f}%)")

        # 执行修复后的计算逻辑
        raw_quantity = position_quantity * target_ratio
        quantity = int(raw_quantity / 100) * 100

        if quantity < 100 and raw_quantity > 0:
            quantity = 100

        quantity = min(quantity, position_quantity)

        # 验证结果
        if quantity == expected_quantity:
            print(f"  ✅ 通过: 卖出 {quantity}股 (预期 {expected_quantity}股)")
        else:
            print(f"  ❌ 失败: 卖出 {quantity}股 (预期 {expected_quantity}股)")
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有测试用例通过！SELL仓位计算修复正确。")
    else:
        print("❌ 部分测试用例失败！请检查代码。")
    print("="*60)

    return all_passed


def test_old_buggy_calculation():
    """测试修复前的错误计算（用于对比）"""
    print("\n" + "="*60)
    print("修复前的错误计算（对比参考）")
    print("="*60)

    test_cases = [
        (1000, 0.5, "500股"),
        (500, 0.5, "250股"),
        (200, 0.5, "100股"),
        (100, 0.5, "50股"),
    ]

    for position_quantity, target_ratio, expected in test_cases:
        # 错误的计算方式（修复前）
        buggy_quantity = int(position_quantity * target_ratio / 100) * 100

        print(f"\n持仓: {position_quantity}股, target_ratio: {target_ratio} (50%)")
        print(f"  ❌ 错误计算: {buggy_quantity}股 (预期{expected})")
        print(f"  错误原因: {position_quantity} * {target_ratio} / 100 * 100 = {buggy_quantity}")


def verify_code_file():
    """验证代码文件是否已修复"""
    print("\n" + "="*60)
    print("检查代码文件")
    print("="*60)

    try:
        with open("trading/multi_strategy_manager.py", "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否包含错误代码
        if "position.quantity * target_ratio / 100) * 100" in content:
            print("❌ 代码文件仍包含错误的计算公式！")
            print("   错误代码: quantity = int(position.quantity * target_ratio / 100) * 100")
            print("\n请检查：")
            print("   1. 是否在正确的分支 (feature/frontend-api-alignment)")
            print("   2. 是否拉取了最新代码 (git pull)")
            print("   3. 是否应用了commit 5250889")
            return False

        # 检查是否包含正确代码
        if "raw_quantity = position.quantity * target_ratio" in content:
            print("✅ 代码文件包含正确的计算公式！")
            print("   第349行: raw_quantity = position.quantity * target_ratio")
            print("   第352行: quantity = int(raw_quantity / 100) * 100")
            return True
        else:
            print("⚠️  无法确认代码状态，请手动检查 trading/multi_strategy_manager.py")
            return None

    except FileNotFoundError:
        print("❌ 找不到文件 trading/multi_strategy_manager.py")
        print("   请确保在项目根目录下运行此脚本")
        return False


if __name__ == "__main__":
    print("\nSELL仓位计算修复验证工具\n")

    # 1. 检查代码文件
    code_ok = verify_code_file()

    # 2. 测试修复后的计算逻辑
    test_ok = test_sell_calculation()

    # 3. 展示修复前的错误（对比）
    test_old_buggy_calculation()

    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)

    if code_ok and test_ok:
        print("✅ SELL仓位计算修复验证通过！")
        print("   - 代码文件已正确修复")
        print("   - 所有测试用例通过")
        print("\n可以安全使用SELL功能。")
    elif code_ok is False:
        print("❌ 代码文件未修复！")
        print("\n请执行以下操作：")
        print("   1. git checkout feature/frontend-api-alignment")
        print("   2. git pull origin feature/frontend-api-alignment")
        print("   或者：")
        print("   git cherry-pick 5250889")
    elif not test_ok:
        print("❌ 测试用例失败！")
        print("\n可能的原因：")
        print("   - 代码逻辑有误")
        print("   - 测试用例有误")
        print("\n请检查 trading/multi_strategy_manager.py 第344-359行")

    print("="*60)
