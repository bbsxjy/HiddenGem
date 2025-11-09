"""
Enhanced Tushare Pro API integration for HiddenGem trading system.
Implements comprehensive data access methods for A-share market data.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
from loguru import logger

from config.settings import settings


class TushareProAPI:
    """
    Enhanced Tushare Pro API wrapper with all required methods for HiddenGem system.

    Provides access to:
    - Stock basic info and market data
    - Financial indicators
    - A-share specific risk data (pledge, restricted shares, ST status)
    - Market monitoring data (northbound capital, margin trading)
    - Index data
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Tushare Pro API.

        Args:
            token: Tushare API token (uses settings if not provided)
        """
        import tushare as ts

        self.token = token or settings.tushare_token
        if not self.token:
            raise ValueError("Tushare token not configured")

        ts.set_token(self.token)
        self.pro = ts.pro_api()

        # Rate limiting tracking
        self.last_call_time = 0
        self.call_interval = 60 / settings.tushare_rate_limit  # seconds between calls

        logger.info("Tushare Pro API initialized successfully")

    def _rate_limit(self):
        """Apply rate limiting between API calls."""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.call_interval:
            sleep_time = self.call_interval - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()

    @staticmethod
    def _convert_symbol(symbol: str, to_tushare: bool = True) -> str:
        """
        Convert symbol format between standard and Tushare format.

        Args:
            symbol: Stock symbol
            to_tushare: If True, convert to Tushare format (e.g., 000001.SZ)

        Returns:
            Converted symbol
        """
        if to_tushare:
            if '.' in symbol:
                return symbol
            # Determine exchange
            if symbol.startswith('6'):
                return f"{symbol}.SH"  # Shanghai
            elif symbol.startswith(('0', '3')):
                return f"{symbol}.SZ"  # Shenzhen
            else:
                return f"{symbol}.SH"  # Default to Shanghai
        else:
            return symbol.split('.')[0] if '.' in symbol else symbol

    # ==================== Stock Basic Info ====================

    def get_stock_basic(self, ts_code: Optional[str] = None, list_status: str = 'L') -> pd.DataFrame:
        """
        Get basic stock information.

        API: stock_basic
        Doc: https://tushare.pro/document/2?doc_id=25

        Args:
            ts_code: Stock code (optional, get all if None)
            list_status: 'L': listed, 'D': delisted, 'P': paused

        Returns:
            DataFrame with stock basic info
        """
        self._rate_limit()

        try:
            df = self.pro.stock_basic(
                ts_code=ts_code,
                list_status=list_status,
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            logger.debug(f"Retrieved stock_basic: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_stock_basic: {e}")
            raise

    def get_stock_company(self, ts_code: str) -> Dict[str, Any]:
        """
        Get detailed company information.

        API: stock_company
        Doc: https://tushare.pro/document/2?doc_id=112

        Args:
            ts_code: Stock code (e.g., '000001.SZ')

        Returns:
            Dictionary with company details
        """
        self._rate_limit()

        try:
            df = self.pro.stock_company(ts_code=ts_code)
            if df.empty:
                return {}

            row = df.iloc[0]
            return {
                'ts_code': row['ts_code'],
                'chairman': row.get('chairman'),
                'manager': row.get('manager'),
                'secretary': row.get('secretary'),
                'reg_capital': row.get('reg_capital'),
                'setup_date': row.get('setup_date'),
                'province': row.get('province'),
                'city': row.get('city'),
                'introduction': row.get('introduction'),
                'website': row.get('website'),
                'email': row.get('email'),
                'employees': row.get('employees'),
                'main_business': row.get('main_business'),
                'business_scope': row.get('business_scope'),
            }
        except Exception as e:
            logger.error(f"Error in get_stock_company for {ts_code}: {e}")
            return {}

    # ==================== Market Data ====================

    def get_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get daily market data (OHLCV).

        API: daily
        Doc: https://tushare.pro/document/2?doc_id=27

        Args:
            ts_code: Stock code (e.g., '000001.SZ')
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with daily OHLCV data
        """
        self._rate_limit()

        try:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved daily data for {ts_code}: {len(df)} bars")
            return df
        except Exception as e:
            logger.error(f"Error in get_daily for {ts_code}: {e}")
            raise

    def get_daily_basic(self, ts_code: Optional[str] = None,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get daily basic indicators (PE, PB, turnover, etc.).

        API: daily_basic
        Doc: https://tushare.pro/document/2?doc_id=32

        Args:
            ts_code: Stock code (optional)
            trade_date: Trade date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with daily basic indicators
        """
        self._rate_limit()

        try:
            df = self.pro.daily_basic(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            )
            logger.debug(f"Retrieved daily_basic: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_daily_basic: {e}")
            raise

    # ==================== Financial Data ====================

    def get_fina_indicator(self, ts_code: str, period: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get financial indicators (ROE, debt ratio, etc.).

        API: fina_indicator
        Doc: https://tushare.pro/document/2?doc_id=79

        Args:
            ts_code: Stock code
            period: Report period (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with financial indicators
        """
        self._rate_limit()

        try:
            df = self.pro.fina_indicator(
                ts_code=ts_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,ann_date,end_date,eps,dt_eps,total_revenue_ps,revenue_ps,capital_rese_ps,surplus_rese_ps,undist_profit_ps,extra_item,profit_dedt,gross_margin,current_ratio,quick_ratio,cash_ratio,invturn_days,arturn_days,inv_turn,ar_turn,ca_turn,fa_turn,assets_turn,op_income,valuechange_income,interst_income,daa,ebit,ebitda,fcff,fcfe,current_exint,noncurrent_exint,interestdebt,netdebt,tangible_asset,working_capital,networking_capital,invest_capital,retained_earnings,diluted2_eps,bps,ocfps,retainedps,cfps,ebit_ps,fcff_ps,fcfe_ps,netprofit_margin,grossprofit_margin,cogs_of_sales,expense_of_sales,profit_to_gr,saleexp_to_gr,adminexp_of_gr,finaexp_of_gr,impai_ttm,gc_of_gr,op_of_gr,ebit_of_gr,roe,roe_waa,roe_dt,roa,npta,roic,roe_yearly,roa2_yearly,roe_avg,opincome_of_ebt,investincome_of_ebt,n_op_profit_of_ebt,tax_to_ebt,dtprofit_to_profit,salescash_to_or,ocf_to_or,ocf_to_opincome,capitalized_to_da,debt_to_assets,assets_to_eqt,dp_assets_to_eqt,ca_to_assets,nca_to_assets,tbassets_to_totalassets,int_to_talcap,eqt_to_talcapital,currentdebt_to_debt,longdeb_to_debt,ocf_to_shortdebt,debt_to_eqt,eqt_to_debt,eqt_to_interestdebt,tangibleasset_to_debt,tangasset_to_intdebt,tangibleasset_to_netdebt,ocf_to_debt,ocf_to_interestdebt,ocf_to_netdebt,ebit_to_interest,longdebt_to_workingcapital,ebitda_to_debt,turn_days,roa_yearly,roa_dp,fixed_assets,profit_prefin_exp,non_op_profit,op_to_ebt,nop_to_ebt,ocf_to_profit,cash_to_liqdebt,cash_to_liqdebt_withinterest,op_to_liqdebt,op_to_debt,roic_yearly,total_fa_trun,profit_to_op,q_opincome,q_investincome,q_dtprofit,q_eps,q_netprofit_margin,q_gsprofit_margin,q_exp_to_sales,q_profit_to_gr,q_saleexp_to_gr,q_adminexp_to_gr,q_finaexp_to_gr,q_impair_to_gr_ttm,q_gc_to_gr,q_op_to_gr,q_roe,q_dt_roe,q_npta,q_opincome_to_ebt,q_investincome_to_ebt,q_dtprofit_to_profit,q_salescash_to_or,q_ocf_to_sales,q_ocf_to_or,basic_eps_yoy,dt_eps_yoy,cfps_yoy,op_yoy,ebt_yoy,netprofit_yoy,dt_netprofit_yoy,ocf_yoy,roe_yoy,bps_yoy,assets_yoy,eqt_yoy,tr_yoy,or_yoy,q_gr_yoy,q_gr_qoq,q_sales_yoy,q_sales_qoq,q_op_yoy,q_op_qoq,q_profit_yoy,q_profit_qoq,q_netprofit_yoy,q_netprofit_qoq,equity_yoy,rd_exp,update_flag'
            )
            logger.debug(f"Retrieved fina_indicator for {ts_code}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_fina_indicator for {ts_code}: {e}")
            raise

    # ==================== A-Share Specific Risk Data ====================

    def get_pledge_stat(self, ts_code: str, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get stock pledge statistics (股权质押统计).

        API: pledge_stat
        Doc: https://tushare.pro/document/2?doc_id=110

        Args:
            ts_code: Stock code
            end_date: End date (YYYYMMDD), defaults to latest

        Returns:
            DataFrame with pledge statistics
        """
        self._rate_limit()

        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            df = self.pro.pledge_stat(
                ts_code=ts_code,
                end_date=end_date
            )
            logger.debug(f"Retrieved pledge_stat for {ts_code}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_pledge_stat for {ts_code}: {e}")
            return pd.DataFrame()

    def get_share_float(self, ts_code: str, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get restricted share unlock schedule (限售股解禁).

        API: share_float
        Doc: https://tushare.pro/document/2?doc_id=160

        Args:
            ts_code: Stock code
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with unlock schedule
        """
        self._rate_limit()

        try:
            df = self.pro.share_float(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved share_float for {ts_code}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_share_float for {ts_code}: {e}")
            return pd.DataFrame()

    def get_stk_limit(self, ts_code: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get ST stock list (特别处理股票).

        API: stk_limit
        Doc: https://tushare.pro/document/2?doc_id=183

        Args:
            ts_code: Stock code (optional)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with ST stock information
        """
        self._rate_limit()

        try:
            df = self.pro.stk_limit(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved stk_limit: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_stk_limit: {e}")
            return pd.DataFrame()

    # ==================== Market Monitoring Data ====================

    def get_moneyflow_hsgt(self, trade_date: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get northbound capital flow via Stock Connect (沪深港通资金流向).

        API: moneyflow_hsgt
        Doc: https://tushare.pro/document/2?doc_id=47

        Args:
            trade_date: Trade date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with capital flow data
        """
        self._rate_limit()

        try:
            df = self.pro.moneyflow_hsgt(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved moneyflow_hsgt: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_moneyflow_hsgt: {e}")
            return pd.DataFrame()

    def get_hsgt_top10(self, ts_code: Optional[str] = None,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      market_type: str = '1') -> pd.DataFrame:
        """
        Get top 10 stocks by northbound trading (沪深港通十大成交股).

        API: hsgt_top10
        Doc: https://tushare.pro/document/2?doc_id=48

        Args:
            ts_code: Stock code (optional)
            trade_date: Trade date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            market_type: '1': Shanghai, '3': Shenzhen

        Returns:
            DataFrame with top 10 stocks
        """
        self._rate_limit()

        try:
            df = self.pro.hsgt_top10(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                market_type=market_type
            )
            logger.debug(f"Retrieved hsgt_top10: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_hsgt_top10: {e}")
            return pd.DataFrame()

    def get_margin(self, trade_date: Optional[str] = None,
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get margin trading summary (融资融券交易汇总).

        API: margin
        Doc: https://tushare.pro/document/2?doc_id=58

        Args:
            trade_date: Trade date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with margin trading data
        """
        self._rate_limit()

        try:
            df = self.pro.margin(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved margin data: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_margin: {e}")
            return pd.DataFrame()

    def get_margin_detail(self, ts_code: Optional[str] = None,
                         trade_date: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get margin trading details by stock (个股融资融券明细).

        API: margin_detail
        Doc: https://tushare.pro/document/2?doc_id=59

        Args:
            ts_code: Stock code (optional)
            trade_date: Trade date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with detailed margin trading data
        """
        self._rate_limit()

        try:
            df = self.pro.margin_detail(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved margin_detail: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_margin_detail: {e}")
            return pd.DataFrame()

    # ==================== Index Data ====================

    def get_index_basic(self, market: str = 'SSE') -> pd.DataFrame:
        """
        Get index basic information.

        API: index_basic
        Doc: https://tushare.pro/document/2?doc_id=94

        Args:
            market: Market code ('SSE', 'SZSE', 'CICC', 'SW', 'OTH')

        Returns:
            DataFrame with index basic info
        """
        self._rate_limit()

        try:
            df = self.pro.index_basic(market=market)
            logger.debug(f"Retrieved index_basic for {market}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_index_basic: {e}")
            return pd.DataFrame()

    def get_index_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get index daily data.

        API: index_daily
        Doc: https://tushare.pro/document/2?doc_id=95

        Args:
            ts_code: Index code (e.g., '000001.SH' for SSE Composite)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            DataFrame with index daily data
        """
        self._rate_limit()

        try:
            df = self.pro.index_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved index_daily for {ts_code}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_index_daily for {ts_code}: {e}")
            raise

    # ==================== Other Useful Data ====================

    def get_suspend_d(self, ts_code: Optional[str] = None,
                     suspend_date: Optional[str] = None,
                     resume_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get intraday stock suspension information (盘中停复牌信息).

        NOTE: This API returns INTRADAY suspension records, not long-term suspensions.
        Use get_suspend() for long-term suspension information.

        API: suspend_d
        Doc: https://tushare.pro/document/2?doc_id=31

        Args:
            ts_code: Stock code (optional)
            suspend_date: Suspension date (YYYYMMDD)
            resume_date: Resume date (YYYYMMDD)

        Returns:
            DataFrame with intraday suspension info
            Columns: ts_code, trade_date, suspend_timing, suspend_type
        """
        self._rate_limit()

        try:
            df = self.pro.suspend_d(
                ts_code=ts_code,
                suspend_date=suspend_date,
                resume_date=resume_date
            )
            logger.debug(f"Retrieved suspend_d: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_suspend_d: {e}")
            return pd.DataFrame()

    def get_suspend(self, ts_code: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   suspend_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get long-term stock suspension information (长期停复牌信息).

        This API returns long-term suspension records with suspend_date and resume_date.
        Use this (not suspend_d) to check if a stock is currently suspended.

        API: suspend
        Points Required: 2000+
        Doc: https://tushare.pro/document/2?doc_id=31

        Args:
            ts_code: Stock code (optional)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            suspend_type: Suspension type (optional)

        Returns:
            DataFrame with long-term suspension info
            Columns: ts_code, suspend_date, resume_date, ann_date, suspend_reason, reason_type
        """
        self._rate_limit()

        try:
            df = self.pro.suspend(
                ts_code=ts_code,
                suspend_type=suspend_type,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"Retrieved suspend (long-term): {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_suspend: {e}")
            return pd.DataFrame()

    def get_moneyflow(self, ts_code: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     trade_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get individual stock money flow data (个股资金流向).

        API: moneyflow
        Points Required: 2000
        Update Frequency: Daily 19:00
        Doc: https://tushare.pro/document/2?doc_id=170

        Args:
            ts_code: Stock code
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            trade_date: Trade date (YYYYMMDD)

        Returns:
            DataFrame with money flow data
            Columns: ts_code, trade_date, buy_sm_vol, buy_sm_amount,
                    sell_sm_vol, sell_sm_amount, buy_md_vol, buy_md_amount,
                    sell_md_vol, sell_md_amount, buy_lg_vol, buy_lg_amount,
                    sell_lg_vol, sell_lg_amount, buy_elg_vol, buy_elg_amount,
                    sell_elg_vol, sell_elg_amount, net_mf_vol, net_mf_amount
        """
        self._rate_limit()

        try:
            ts_code = self._convert_symbol(ts_code, to_tushare=True)

            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                trade_date=trade_date
            )
            logger.debug(f"Retrieved moneyflow for {ts_code}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_moneyflow for {ts_code}: {e}")
            return pd.DataFrame()

    def get_hk_hold(self, ts_code: Optional[str] = None,
                   trade_date: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   exchange: Optional[str] = None) -> pd.DataFrame:
        """
        Get Shanghai-Shenzhen-HK Stock Connect holdings (沪深股通持股明细).

        API: hk_hold
        Points Required: 2000
        Update Frequency: Next trading day 08:00
        Doc: https://tushare.pro/document/2?doc_id=188

        Args:
            ts_code: Stock code
            trade_date: Trade date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            exchange: Exchange (SH/SZ)

        Returns:
            DataFrame with HK holdings data
            Columns: code, trade_date, ts_code, name, vol, ratio, exchange
        """
        self._rate_limit()

        try:
            if ts_code:
                ts_code = self._convert_symbol(ts_code, to_tushare=True)

            df = self.pro.hk_hold(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                exchange=exchange
            )
            logger.debug(f"Retrieved hk_hold: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_hk_hold: {e}")
            return pd.DataFrame()

    def get_stk_holdertrade(self, ts_code: Optional[str] = None,
                           ann_date: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           trade_type: Optional[str] = None,
                           holder_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get shareholder trading records (股东增减持).

        API: stk_holdertrade
        Points Required: 2000
        Update Frequency: Daily 19:00
        Doc: https://tushare.pro/document/2?doc_id=175

        Args:
            ts_code: Stock code
            ann_date: Announcement date (YYYYMMDD)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            trade_type: Trade type (增持/减持)
            holder_type: Holder type

        Returns:
            DataFrame with shareholder trading data
            Columns: ts_code, ann_date, holder_name, holder_type, in_de,
                    change_vol, change_ratio, after_share, after_ratio,
                    avg_price, total_share, begin_date, close_date
        """
        self._rate_limit()

        try:
            if ts_code:
                ts_code = self._convert_symbol(ts_code, to_tushare=True)

            df = self.pro.stk_holdertrade(
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                trade_type=trade_type,
                holder_type=holder_type
            )
            logger.debug(f"Retrieved stk_holdertrade: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_stk_holdertrade: {e}")
            return pd.DataFrame()

    def get_top_list(self, trade_date: Optional[str] = None,
                    ts_code: Optional[str] = None) -> pd.DataFrame:
        """
        Get daily top list (dragon-tiger list) records (龙虎榜每日明细).

        API: top_list
        Points Required: 2000
        Update Frequency: Daily 20:00
        Doc: https://tushare.pro/document/2?doc_id=106

        Args:
            trade_date: Trade date (YYYYMMDD)
            ts_code: Stock code

        Returns:
            DataFrame with top list data
            Columns: trade_date, ts_code, name, close, pct_chg, turnover_rate,
                    amount, l_sell, l_buy, l_amount, net_amount, net_rate,
                    amount_rate, float_values, reason
        """
        self._rate_limit()

        try:
            if ts_code:
                ts_code = self._convert_symbol(ts_code, to_tushare=True)

            df = self.pro.top_list(
                trade_date=trade_date,
                ts_code=ts_code
            )
            logger.debug(f"Retrieved top_list: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_top_list: {e}")
            return pd.DataFrame()

    def get_top_inst(self, trade_date: Optional[str] = None,
                    ts_code: Optional[str] = None) -> pd.DataFrame:
        """
        Get top list institutional trading details (龙虎榜机构交易明细).

        API: top_inst
        Points Required: 2000
        Update Frequency: Daily 20:00
        Doc: https://tushare.pro/document/2?doc_id=107

        Args:
            trade_date: Trade date (YYYYMMDD)
            ts_code: Stock code

        Returns:
            DataFrame with institutional trading data
            Columns: trade_date, ts_code, exalter, buy, buy_rate,
                    sell, sell_rate, net_buy
        """
        self._rate_limit()

        try:
            if ts_code:
                ts_code = self._convert_symbol(ts_code, to_tushare=True)

            df = self.pro.top_inst(
                trade_date=trade_date,
                ts_code=ts_code
            )
            logger.debug(f"Retrieved top_inst: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_top_inst: {e}")
            return pd.DataFrame()

    def get_namechange(self, ts_code: str) -> pd.DataFrame:
        """
        Get stock name change history (股票曾用名).

        API: namechange
        Doc: https://tushare.pro/document/2?doc_id=100

        Args:
            ts_code: Stock code

        Returns:
            DataFrame with name change history
        """
        self._rate_limit()

        try:
            df = self.pro.namechange(ts_code=ts_code)
            logger.debug(f"Retrieved namechange for {ts_code}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error in get_namechange for {ts_code}: {e}")
            return pd.DataFrame()

    # ==================== Helper Methods ====================

    def get_latest_financial_indicators(self, ts_code: str) -> Dict[str, Any]:
        """
        Get latest financial indicators for a stock (convenience method).

        Args:
            ts_code: Stock code

        Returns:
            Dictionary with latest financial indicators
        """
        try:
            ts_code = self._convert_symbol(ts_code, to_tushare=True)

            # Get latest report period
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            df = self.get_fina_indicator(ts_code, start_date=start_date, end_date=end_date)

            if df.empty:
                return {}

            # Get most recent record
            df = df.sort_values('end_date', ascending=False)
            latest = df.iloc[0]

            return {
                'ts_code': ts_code,
                'end_date': latest['end_date'],
                'ann_date': latest['ann_date'],
                'roe': latest.get('roe'),
                'roe_waa': latest.get('roe_waa'),
                'roe_dt': latest.get('roe_dt'),
                'roa': latest.get('roa'),
                'debt_to_assets': latest.get('debt_to_assets'),
                'current_ratio': latest.get('current_ratio'),
                'quick_ratio': latest.get('quick_ratio'),
                'gross_margin': latest.get('gross_margin'),
                'netprofit_margin': latest.get('netprofit_margin'),
                'eps': latest.get('eps'),
                'bps': latest.get('bps'),
                'ocfps': latest.get('ocfps'),
            }
        except Exception as e:
            logger.error(f"Error getting latest financial indicators for {ts_code}: {e}")
            return {}

    def get_latest_pledge_ratio(self, ts_code: str) -> float:
        """
        Get latest pledge ratio for a stock (convenience method).

        Args:
            ts_code: Stock code

        Returns:
            Pledge ratio (0-100), or 0 if no data
        """
        try:
            ts_code = self._convert_symbol(ts_code, to_tushare=True)
            df = self.get_pledge_stat(ts_code)

            if df.empty:
                return 0.0

            # Get most recent record
            df = df.sort_values('end_date', ascending=False)
            latest = df.iloc[0]

            # pledge_count is total pledged shares ratio
            return float(latest.get('pledge_count', 0.0))
        except Exception as e:
            logger.error(f"Error getting pledge ratio for {ts_code}: {e}")
            return 0.0

    def get_next_unlock_info(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """
        Get next restricted share unlock info (convenience method).

        Args:
            ts_code: Stock code

        Returns:
            Dictionary with next unlock info, or None if no upcoming unlocks
        """
        try:
            ts_code = self._convert_symbol(ts_code, to_tushare=True)

            # Get unlock schedule for next 12 months
            start_date = datetime.now().strftime('%Y%m%d')
            end_date = (datetime.now() + timedelta(days=365)).strftime('%Y%m%d')

            df = self.get_share_float(ts_code, start_date=start_date, end_date=end_date)

            if df.empty:
                return None

            # Get nearest future unlock
            df = df.sort_values('float_date')
            next_unlock = df.iloc[0]

            return {
                'ts_code': ts_code,
                'float_date': next_unlock['float_date'],
                'float_share': next_unlock.get('float_share'),
                'float_ratio': next_unlock.get('float_ratio'),
                'holder_name': next_unlock.get('holder_name'),
                'share_type': next_unlock.get('share_type'),
            }
        except Exception as e:
            logger.error(f"Error getting next unlock info for {ts_code}: {e}")
            return None

    def is_st_stock(self, ts_code: str) -> bool:
        """
        Check if a stock is currently ST (Special Treatment).

        Args:
            ts_code: Stock code

        Returns:
            True if stock is ST, False otherwise
        """
        try:
            ts_code = self._convert_symbol(ts_code, to_tushare=True)

            # Get stock basic info
            df = self.get_stock_basic(ts_code=ts_code)

            if not df.empty:
                stock_info = df.iloc[0]
                name = stock_info.get('name', '')

                # Check if name contains ST, *ST, S*ST, etc.
                if 'ST' in name:
                    return True

                # Check list_status
                list_status = stock_info.get('list_status', '')
                if list_status in ['P', 'D']:  # P=暂停上市, D=退市
                    return True

            return False
        except Exception as e:
            logger.error(f"Error checking ST status for {ts_code}: {e}")
            return False


# Global instance
tushare_api = None

def get_tushare_api() -> TushareProAPI:
    """Get or create global Tushare Pro API instance."""
    global tushare_api
    if tushare_api is None:
        tushare_api = TushareProAPI()
    return tushare_api
