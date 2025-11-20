"""
数据库管理器

负责创建和管理本地SQLite数据库
设计符合Tushare数据结构
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TushareDatabase:
    """Tushare本地数据库管理器"""

    def __init__(self, db_path: str = "data/tushare_local.db"):
        """初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self.connect()
        self.create_tables()

    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 返回字典格式
        logger.info(f"✅ 已连接到数据库: {self.db_path}")

    def create_tables(self):
        """创建所有必要的数据表"""
        cursor = self.conn.cursor()

        # 1. 股票基本信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                ts_code TEXT PRIMARY KEY,
                symbol TEXT,
                name TEXT,
                area TEXT,
                industry TEXT,
                market TEXT,
                list_date TEXT,
                updated_at TEXT
            )
        """)

        # 2. 日线行情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                pre_close REAL,
                change REAL,
                pct_chg REAL,
                vol REAL,
                amount REAL,
                UNIQUE(ts_code, trade_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quotes_code ON daily_quotes(ts_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quotes_date ON daily_quotes(trade_date)")

        # 3. 财务指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                end_date TEXT NOT NULL,
                ann_date TEXT,
                eps REAL,
                dt_eps REAL,
                total_revenue_ps REAL,
                revenue_ps REAL,
                capital_rese_ps REAL,
                surplus_rese_ps REAL,
                undist_profit_ps REAL,
                extra_item REAL,
                profit_dedt REAL,
                gross_margin REAL,
                current_ratio REAL,
                quick_ratio REAL,
                cash_ratio REAL,
                invturn_days REAL,
                arturn_days REAL,
                inv_turn REAL,
                ar_turn REAL,
                ca_turn REAL,
                fa_turn REAL,
                assets_turn REAL,
                op_income REAL,
                valuechange_income REAL,
                interst_income REAL,
                daa REAL,
                ebit REAL,
                ebitda REAL,
                fcff REAL,
                fcfe REAL,
                current_exint REAL,
                noncurrent_exint REAL,
                interestdebt REAL,
                netdebt REAL,
                tangible_asset REAL,
                working_capital REAL,
                networking_capital REAL,
                invest_capital REAL,
                retained_earnings REAL,
                diluted2_eps REAL,
                bps REAL,
                ocfps REAL,
                retainedps REAL,
                cfps REAL,
                ebit_ps REAL,
                fcff_ps REAL,
                fcfe_ps REAL,
                netprofit_margin REAL,
                grossprofit_margin REAL,
                cogs_of_sales REAL,
                expense_of_sales REAL,
                profit_to_gr REAL,
                saleexp_to_gr REAL,
                adminexp_of_gr REAL,
                finaexp_of_gr REAL,
                impai_ttm REAL,
                gc_of_gr REAL,
                op_of_gr REAL,
                ebit_of_gr REAL,
                roe REAL,
                roe_waa REAL,
                roe_dt REAL,
                roa REAL,
                npta REAL,
                roic REAL,
                roe_yearly REAL,
                roa2_yearly REAL,
                roe_avg REAL,
                opincome_of_ebt REAL,
                investincome_of_ebt REAL,
                n_op_profit_of_ebt REAL,
                tax_to_ebt REAL,
                dtprofit_to_profit REAL,
                salescash_to_or REAL,
                ocf_to_or REAL,
                ocf_to_opincome REAL,
                capitalized_to_da REAL,
                debt_to_assets REAL,
                assets_to_eqt REAL,
                dp_assets_to_eqt REAL,
                ca_to_assets REAL,
                nca_to_assets REAL,
                tbassets_to_totalassets REAL,
                int_to_talcap REAL,
                eqt_to_talcapital REAL,
                currentdebt_to_debt REAL,
                longdeb_to_debt REAL,
                ocf_to_shortdebt REAL,
                debt_to_eqt REAL,
                eqt_to_debt REAL,
                eqt_to_interestdebt REAL,
                tangibleasset_to_debt REAL,
                tangasset_to_intdebt REAL,
                tangibleasset_to_netdebt REAL,
                ocf_to_debt REAL,
                ocf_to_interestdebt REAL,
                ocf_to_netdebt REAL,
                ebit_to_interest REAL,
                longdebt_to_workingcapital REAL,
                ebitda_to_debt REAL,
                turn_days REAL,
                roa_yearly REAL,
                roa_dp REAL,
                fixed_assets REAL,
                profit_prefin_exp REAL,
                non_op_profit REAL,
                op_to_ebt REAL,
                nop_to_ebt REAL,
                ocf_to_profit REAL,
                cash_to_liqdebt REAL,
                cash_to_liqdebt_withinterest REAL,
                op_to_liqdebt REAL,
                op_to_debt REAL,
                roic_yearly REAL,
                total_fa_trun REAL,
                profit_to_op REAL,
                q_opincome REAL,
                q_investincome REAL,
                q_dtprofit REAL,
                q_eps REAL,
                q_netprofit_margin REAL,
                q_gsprofit_margin REAL,
                q_exp_to_sales REAL,
                q_profit_to_gr REAL,
                q_saleexp_to_gr REAL,
                q_adminexp_to_gr REAL,
                q_finaexp_to_gr REAL,
                q_impair_to_gr_ttm REAL,
                q_gc_to_gr REAL,
                q_op_to_gr REAL,
                q_roe REAL,
                q_dt_roe REAL,
                q_npta REAL,
                q_opincome_to_ebt REAL,
                q_investincome_to_ebt REAL,
                q_dtprofit_to_profit REAL,
                q_salescash_to_or REAL,
                q_ocf_to_sales REAL,
                q_ocf_to_or REAL,
                basic_eps_yoy REAL,
                dt_eps_yoy REAL,
                cfps_yoy REAL,
                op_yoy REAL,
                ebt_yoy REAL,
                netprofit_yoy REAL,
                dt_netprofit_yoy REAL,
                ocf_yoy REAL,
                roe_yoy REAL,
                bps_yoy REAL,
                assets_yoy REAL,
                eqt_yoy REAL,
                tr_yoy REAL,
                or_yoy REAL,
                q_gr_yoy REAL,
                q_gr_qoq REAL,
                q_sales_yoy REAL,
                q_sales_qoq REAL,
                q_op_yoy REAL,
                q_op_qoq REAL,
                q_profit_yoy REAL,
                q_profit_qoq REAL,
                q_netprofit_yoy REAL,
                q_netprofit_qoq REAL,
                equity_yoy REAL,
                rd_exp REAL,
                update_flag TEXT,
                UNIQUE(ts_code, end_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_code ON financial_indicators(ts_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_date ON financial_indicators(end_date)")

        # 4. 实时行情表（用于缓存最新行情）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS realtime_quotes (
                ts_code TEXT PRIMARY KEY,
                price REAL,
                change REAL,
                pct_change REAL,
                vol REAL,
                amount REAL,
                bid REAL,
                ask REAL,
                high REAL,
                low REAL,
                open REAL,
                pre_close REAL,
                updated_at TEXT
            )
        """)

        # 5. 同步状态表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                table_name TEXT PRIMARY KEY,
                last_sync_date TEXT,
                last_sync_time TEXT,
                total_records INTEGER,
                status TEXT,
                error_message TEXT
            )
        """)

        # 6. 交易日历表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_calendar (
                exchange TEXT NOT NULL,
                cal_date TEXT NOT NULL,
                is_open INTEGER,
                pretrade_date TEXT,
                UNIQUE(exchange, cal_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_calendar_date ON trade_calendar(cal_date)")

        self.conn.commit()
        logger.info("✅ 数据表创建完成")

    def insert_or_update(self, table: str, data: Dict[str, Any]):
        """插入或更新单条记录

        Args:
            table: 表名
            data: 数据字典
        """
        cursor = self.conn.cursor()

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())

        sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        self.conn.commit()

    def bulk_insert(self, table: str, data_list: List[Dict[str, Any]]):
        """批量插入数据

        Args:
            table: 表名
            data_list: 数据字典列表
        """
        if not data_list:
            return

        cursor = self.conn.cursor()

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['?' for _ in data_list[0]])

        sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"

        values_list = [tuple(d.values()) for d in data_list]
        cursor.executemany(sql, values_list)
        self.conn.commit()

        logger.info(f"✅ 批量插入 {len(data_list)} 条记录到 {table}")

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """执行查询

        Args:
            sql: SQL语句
            params: 参数

        Returns:
            查询结果列表
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_last_sync_date(self, table: str) -> Optional[str]:
        """获取表的最后同步日期

        Args:
            table: 表名

        Returns:
            最后同步日期（YYYYMMDD格式），如果从未同步返回None
        """
        result = self.query(
            "SELECT last_sync_date FROM sync_status WHERE table_name = ?",
            (table,)
        )

        return result[0]['last_sync_date'] if result else None

    def update_sync_status(self, table: str, sync_date: str, total_records: int, status: str = 'success', error: str = None):
        """更新同步状态

        Args:
            table: 表名
            sync_date: 同步日期
            total_records: 记录数
            status: 状态（success/failed）
            error: 错误信息
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.insert_or_update('sync_status', {
            'table_name': table,
            'last_sync_date': sync_date,
            'last_sync_time': now,
            'total_records': total_records,
            'status': status,
            'error_message': error
        })

    def get_stock_list(self) -> List[str]:
        """获取所有股票代码列表

        Returns:
            股票代码列表
        """
        result = self.query("SELECT ts_code FROM stock_basic")
        return [r['ts_code'] for r in result]

    def get_date_range(self, table: str, ts_code: str) -> tuple:
        """获取某股票的数据日期范围

        Args:
            table: 表名
            ts_code: 股票代码

        Returns:
            (最早日期, 最晚日期)
        """
        result = self.query(
            f"SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date FROM {table} WHERE ts_code = ?",
            (ts_code,)
        )

        if result and result[0]['min_date']:
            return result[0]['min_date'], result[0]['max_date']
        return None, None

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("✅ 数据库连接已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
