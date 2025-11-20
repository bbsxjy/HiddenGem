"""
Tushare数据本地同步系统

替代商业数据同步软件，节省¥199
完全开源，可定制化

功能：
1. 数据同步：将Tushare数据同步到本地SQLite数据库
2. 增量更新：只同步新数据，避免重复下载
3. 自动调度：每日自动更新数据
4. 统一接口：提供与Tushare API兼容的查询接口

使用方法：
    from data_sync import TushareDataSync

    sync = TushareDataSync()
    sync.sync_all()  # 首次全量同步
    sync.sync_daily()  # 每日增量同步
"""

from .sync_engine import TushareDataSync
from .database import TushareDatabase
from .scheduler import start_scheduler, stop_scheduler

__all__ = ['TushareDataSync', 'TushareDatabase', 'start_scheduler', 'stop_scheduler']
