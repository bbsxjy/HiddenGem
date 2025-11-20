#!/usr/bin/env python3
"""
Tushare API使用监控脚本

用途：统计API调用次数，帮助决策是否需要购买数据同步软件

运行：
python scripts/monitor_api_usage.py

查看统计：
python scripts/monitor_api_usage.py --report
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
import sys

# 日志文件路径
LOG_FILE = Path(__file__).parent.parent / "logs" / "api_usage.json"
LOG_FILE.parent.mkdir(exist_ok=True)


class APIUsageMonitor:
    """API使用监控器"""

    def __init__(self):
        self.log_file = LOG_FILE
        self.load_logs()

    def load_logs(self):
        """加载历史日志"""
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                self.logs = json.load(f)
        else:
            self.logs = {
                "daily_stats": {},
                "api_calls": []
            }

    def save_logs(self):
        """保存日志"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)

    def log_api_call(self, api_name: str, symbol: str = "", success: bool = True):
        """记录一次API调用

        Args:
            api_name: API名称（如 "get_stock_data", "get_news"）
            symbol: 股票代码
            success: 是否成功
        """
        today = date.today().isoformat()
        timestamp = datetime.now().isoformat()

        # 记录详细调用
        self.logs["api_calls"].append({
            "timestamp": timestamp,
            "api_name": api_name,
            "symbol": symbol,
            "success": success
        })

        # 更新每日统计
        if today not in self.logs["daily_stats"]:
            self.logs["daily_stats"][today] = {
                "total_calls": 0,
                "api_breakdown": {},
                "symbols": set()
            }

        self.logs["daily_stats"][today]["total_calls"] += 1

        # API分类统计
        if api_name not in self.logs["daily_stats"][today]["api_breakdown"]:
            self.logs["daily_stats"][today]["api_breakdown"][api_name] = 0
        self.logs["daily_stats"][today]["api_breakdown"][api_name] += 1

        # 股票统计（转换set为list以便JSON序列化）
        symbols = self.logs["daily_stats"][today]["symbols"]
        if isinstance(symbols, set):
            symbols = list(symbols)
            self.logs["daily_stats"][today]["symbols"] = symbols

        if symbol and symbol not in symbols:
            symbols.append(symbol)
            self.logs["daily_stats"][today]["symbols"] = symbols

        self.save_logs()

    def get_report(self, days: int = 7):
        """生成统计报告

        Args:
            days: 统计最近几天，默认7天
        """
        print("\n" + "="*60)
        print(f"📊 Tushare API使用统计报告（最近{days}天）")
        print("="*60 + "\n")

        # 按日期排序
        sorted_dates = sorted(self.logs["daily_stats"].keys(), reverse=True)[:days]

        total_calls = 0
        total_symbols = set()
        api_breakdown_total = defaultdict(int)

        for day in sorted_dates:
            stats = self.logs["daily_stats"][day]
            calls = stats["total_calls"]
            symbols = stats.get("symbols", [])

            total_calls += calls
            total_symbols.update(symbols)

            print(f"📅 {day}")
            print(f"   总调用次数: {calls}")
            print(f"   涉及股票数: {len(symbols)}")

            # API分类统计
            breakdown = stats.get("api_breakdown", {})
            if breakdown:
                print(f"   API调用分布:")
                for api, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                    print(f"      - {api}: {count}次")
                    api_breakdown_total[api] += count
            print()

        # 总体统计
        print("="*60)
        print("📈 总体统计")
        print("="*60)
        print(f"统计天数: {len(sorted_dates)}天")
        print(f"总调用次数: {total_calls}次")
        print(f"日均调用: {total_calls / len(sorted_dates):.1f}次" if sorted_dates else "0次")
        print(f"涉及股票总数: {len(total_symbols)}只")
        print()

        # API分类汇总
        print("🔍 API调用分布（总计）:")
        for api, count in sorted(api_breakdown_total.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {api}: {count}次 ({count/total_calls*100:.1f}%)")
        print()

        # 建议
        print("="*60)
        print("💡 建议")
        print("="*60)

        avg_daily = total_calls / len(sorted_dates) if sorted_dates else 0

        if avg_daily < 500:
            print("✅ API调用量较低，当前Tushare套餐够用")
            print("   建议：暂不需要购买数据同步软件")
        elif avg_daily < 1000:
            print("⚠️ API调用量中等，可能偶尔遇到限流")
            print("   建议：考虑购买数据同步软件（¥199）")
        else:
            print("❌ API调用量较高，容易遇到限流")
            print("   建议：强烈推荐购买数据同步软件（¥199）")
            print("   原因：本地数据库可以无限调用，避免限流")

        print()
        print("Tushare限流说明：")
        print("   - 基础会员：120次/分钟")
        print(f"   - 你的峰值：约{avg_daily/240:.1f}次/分钟（假设4小时交易时段）")
        print()


def patch_tushare_calls():
    """
    补丁函数：在Tushare调用时自动记录

    使用方法：
    在你的主程序开始时调用：
    from scripts.monitor_api_usage import patch_tushare_calls
    patch_tushare_calls()
    """
    monitor = APIUsageMonitor()

    # TODO: 这里需要monkey patch你的数据接口
    # 示例：
    # import tradingagents.dataflows.interface as data_interface
    # original_get_stock_data = data_interface.get_stock_data_dataframe
    #
    # def monitored_get_stock_data(*args, **kwargs):
    #     symbol = args[0] if args else kwargs.get('symbol', '')
    #     monitor.log_api_call('get_stock_data', symbol)
    #     return original_get_stock_data(*args, **kwargs)
    #
    # data_interface.get_stock_data_dataframe = monitored_get_stock_data

    print("✅ API监控已启用")
    return monitor


if __name__ == "__main__":
    monitor = APIUsageMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # 生成报告
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        monitor.get_report(days)
    else:
        # 测试记录
        print("📝 测试记录API调用...")
        monitor.log_api_call("get_stock_data", "000001.SZ")
        monitor.log_api_call("get_stock_info", "000001.SZ")
        monitor.log_api_call("get_news", "000001.SZ")
        print("✅ 测试完成")
        print("\n运行以下命令查看报告：")
        print("python scripts/monitor_api_usage.py --report")
