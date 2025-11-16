"""
Report Generator

回测报告生成器 - 生成 HTML 和 JSON 格式的回测报告
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd


class ReportGenerator:
    """回测报告生成器"""

    def __init__(self, backtest_result: Dict[str, Any]):
        """初始化报告生成器

        Args:
            backtest_result: 回测结果字典
        """
        self.result = backtest_result

    def generate_json_report(self, filepath: Optional[str] = None) -> dict:
        """生成 JSON 格式报告

        Args:
            filepath: 保存路径（可选）

        Returns:
            报告字典
        """
        # 准备 JSON 数据（处理日期序列化）
        json_data = self._prepare_json_data()

        # 保存到文件
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

        return json_data

    def _prepare_json_data(self) -> dict:
        """准备可序列化的 JSON 数据"""
        data = self.result.copy()

        # 转换权益曲线中的日期
        if 'equity_curve' in data:
            for item in data['equity_curve']:
                if isinstance(item.get('timestamp'), datetime):
                    item['timestamp'] = item['timestamp'].isoformat()

        # 转换交易记录中的日期
        if 'trades' in data:
            for trade in data['trades']:
                if isinstance(trade.get('timestamp'), datetime):
                    trade['timestamp'] = trade['timestamp'].isoformat()

        return data

    def generate_html_report(self, filepath: Optional[str] = None) -> str:
        """生成 HTML 格式报告

        Args:
            filepath: 保存路径（可选）

        Returns:
            HTML 字符串
        """
        metrics = self.result.get('metrics', {})
        equity_curve = self.result.get('equity_curve', [])
        trades = self.result.get('trades', [])
        strategy_name = self.result.get('strategy_name', 'Unknown Strategy')

        # 生成 HTML
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测报告 - {strategy_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #eee;
            padding-bottom: 8px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card.positive {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        }}
        .metric-card.negative {{
            background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .trades-table th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        .trades-table td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .trades-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .buy {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .sell {{
            color: #f44336;
            font-weight: bold;
        }}
        .chart-placeholder {{
            background-color: #f0f0f0;
            padding: 60px 20px;
            text-align: center;
            border-radius: 8px;
            margin: 20px 0;
            border: 2px dashed #ccc;
        }}
        .timestamp {{
            text-align: right;
            color: #888;
            margin-top: 30px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1> 回测报告</h1>
        <p><strong>策略名称：</strong>{strategy_name}</p>
        <p><strong>生成时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2> 绩效摘要</h2>
        <div class="metrics-grid">
            {self._generate_metric_card('初始资金', f"¥{metrics.get('initial_capital', 0):,.2f}")}
            {self._generate_metric_card('最终价值', f"¥{metrics.get('final_value', 0):,.2f}")}
            {self._generate_metric_card('总收益率', f"{metrics.get('total_return', 0):.2f}%",
                'positive' if metrics.get('total_return', 0) > 0 else 'negative')}
            {self._generate_metric_card('年化收益率', f"{metrics.get('annualized_return', 0):.2f}%",
                'positive' if metrics.get('annualized_return', 0) > 0 else 'negative')}
            {self._generate_metric_card('夏普比率', f"{metrics.get('sharpe_ratio', 0):.3f}")}
            {self._generate_metric_card('索提诺比率', f"{metrics.get('sortino_ratio', 0):.3f}")}
            {self._generate_metric_card('最大回撤', f"{metrics.get('max_drawdown_pct', 0):.2f}%", 'negative')}
            {self._generate_metric_card('卡玛比率', f"{metrics.get('calmar_ratio', 0):.3f}")}
            {self._generate_metric_card('波动率', f"{metrics.get('volatility', 0):.2f}%")}
            {self._generate_metric_card('胜率', f"{metrics.get('win_rate', 0):.2f}%")}
            {self._generate_metric_card('盈亏比', f"{metrics.get('profit_factor', 0):.2f}")}
            {self._generate_metric_card('交易次数', f"{metrics.get('total_trades', 0)}")}
        </div>

        <h2> 权益曲线</h2>
        <div class="chart-placeholder">
            <p> 权益曲线图表</p>
            <p style="color: #666; font-size: 14px;">
                使用前端可视化库（如 Chart.js、ECharts）渲染数据<br>
                数据已包含在 JSON 报告的 equity_curve 字段中
            </p>
        </div>

        <h2> 回撤曲线</h2>
        <div class="chart-placeholder">
            <p> 回撤曲线图表</p>
            <p style="color: #666; font-size: 14px;">
                最大回撤: {metrics.get('max_drawdown_pct', 0):.2f}%
            </p>
        </div>

        <h2> 交易明细</h2>
        <table class="trades-table">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>股票代码</th>
                    <th>操作</th>
                    <th>数量</th>
                    <th>价格</th>
                    <th>手续费</th>
                    <th>盈亏</th>
                </tr>
            </thead>
            <tbody>
                {self._generate_trades_rows(trades)}
            </tbody>
        </table>

        <div class="timestamp">
            报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

        # 保存到文件
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)

        return html

    def _generate_metric_card(self, label: str, value: str, card_type: str = '') -> str:
        """生成指标卡片 HTML"""
        card_class = f"metric-card {card_type}" if card_type else "metric-card"
        return f"""
            <div class="{card_class}">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
        """

    def _generate_trades_rows(self, trades: List[dict]) -> str:
        """生成交易记录表格行"""
        if not trades:
            return '<tr><td colspan="7" style="text-align:center;">暂无交易记录</td></tr>'

        rows = []
        for trade in trades:
            timestamp = trade.get('timestamp', '')
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

            symbol = trade.get('symbol', 'N/A')
            side = trade.get('side', 'N/A')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            commission = trade.get('commission', 0)
            pnl = trade.get('realized_pnl', 0)

            side_class = 'buy' if side == 'buy' else 'sell'
            pnl_display = f"{pnl:,.2f}" if side == 'sell' else '-'

            rows.append(f"""
                <tr>
                    <td>{timestamp}</td>
                    <td>{symbol}</td>
                    <td class="{side_class}">{side.upper()}</td>
                    <td>{quantity}</td>
                    <td>¥{price:,.2f}</td>
                    <td>¥{commission:,.2f}</td>
                    <td>{pnl_display}</td>
                </tr>
            """)

        return '\n'.join(rows)

    def generate_summary_text(self) -> str:
        """生成文本摘要

        Returns:
            文本摘要
        """
        metrics = self.result.get('metrics', {})
        strategy_name = self.result.get('strategy_name', 'Unknown Strategy')

        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                      回测报告摘要                              ║
╚══════════════════════════════════════════════════════════════╝

策略名称: {strategy_name}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 收益指标
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
初始资金:        ¥{metrics.get('initial_capital', 0):,.2f}
最终价值:        ¥{metrics.get('final_value', 0):,.2f}
总收益率:        {metrics.get('total_return', 0):.2f}%
年化收益率:      {metrics.get('annualized_return', 0):.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 风险指标
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
波动率:          {metrics.get('volatility', 0):.2f}%
夏普比率:        {metrics.get('sharpe_ratio', 0):.3f}
索提诺比率:      {metrics.get('sortino_ratio', 0):.3f}
最大回撤:        {metrics.get('max_drawdown_pct', 0):.2f}%
卡玛比率:        {metrics.get('calmar_ratio', 0):.3f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 交易指标
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总交易次数:      {metrics.get('total_trades', 0)}
盈利交易:        {metrics.get('winning_trades', 0)}
亏损交易:        {metrics.get('losing_trades', 0)}
胜率:            {metrics.get('win_rate', 0):.2f}%
盈亏比:          {metrics.get('profit_factor', 0):.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return summary
