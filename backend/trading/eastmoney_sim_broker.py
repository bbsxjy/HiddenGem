"""
Eastmoney Simulated Broker - 东方财富模拟盘券商接口实现
"""
import requests, hashlib, time, logging
from typing import Dict, List, Optional
from datetime import datetime
from .base_broker import BaseBroker, BrokerLoginError, BrokerOrderError, BrokerConnectionError
from .order import Order, OrderStatus, OrderSide

logger = logging.getLogger(__name__)

class EastmoneySimulatedBroker(BaseBroker):
    BASE_URL = "https://emdesk.eastmoney.com"
    API_ENDPOINTS = {
        'login': '/api/login',
        'logout': '/api/logout',
        'submit_order': '/api/order/submit',
        'cancel_order': '/api/order/cancel',
        'get_positions': '/api/position/list',
        'get_balance': '/api/account/balance',
        'get_orders': '/api/order/list',
    }
    
    def __init__(self, account_config: dict):
        super().__init__(account_config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/json'
        })
        self.token = None
        self.user_id = None
        self._cache = {'positions': None, 'balance': None, 'orders': None, 'last_update': None}
        logger.info("EastmoneySimulatedBroker initialized")
    
    def login(self) -> bool:
        try:
            logger.warning("[SIMULATED] Using simulated login (not connected to real API)")
            result = {'success': True, 'token': 'mock_token_' + str(int(time.time())), 'user_id': 'mock_user_001'}
            if result.get('success'):
                self.token = result.get('token')
                self.user_id = result.get('user_id')
                self.is_logged_in = True
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                logger.info(f"[SUCCESS] Login successful")
                return True
            raise BrokerLoginError("Login failed")
        except Exception as e:
            raise BrokerLoginError(f"Login error: {e}")
    
    def logout(self) -> bool:
        if not self.is_logged_in:
            return True
        self.is_logged_in = False
        self.token = None
        self.user_id = None
        self._clear_cache()
        return True
    
    def submit_order(self, order: Order) -> dict:
        if not self.is_logged_in:
            raise BrokerOrderError("Not logged in")
        valid, error_msg = self.validate_order(order)
        if not valid:
            raise BrokerOrderError(f"Order validation failed: {error_msg}")
        logger.warning("[SIMULATED] Using simulated order submission (not connected to real API)")
        result = {'success': True, 'broker_order_id': f'EM{int(time.time() * 1000)}', 'message': '订单已提交（模拟）', 'timestamp': datetime.now().isoformat()}
        if result.get('success'):
            self._clear_cache()
            return result
        raise BrokerOrderError("Order submission failed")
    
    def cancel_order(self, order_id: str) -> dict:
        if not self.is_logged_in:
            raise BrokerOrderError("Not logged in")
        logger.warning("[SIMULATED] Using simulated order cancellation (not connected to real API)")
        result = {'success': True, 'message': '撤单成功（模拟）'}
        self._clear_cache()
        return result
    
    def get_positions(self) -> List[dict]:
        if not self.is_logged_in:
            raise BrokerConnectionError("Not logged in")
        if self._is_cache_valid() and self._cache['positions'] is not None:
            return self._cache['positions']
        logger.warning("[SIMULATED] Using simulated position data (not connected to real API)")
        positions = []
        self._cache['positions'] = positions
        self._cache['last_update'] = time.time()
        return positions
    
    def get_balance(self) -> dict:
        if not self.is_logged_in:
            raise BrokerConnectionError("Not logged in")
        if self._is_cache_valid() and self._cache['balance'] is not None:
            return self._cache['balance']
        logger.warning("[SIMULATED] Using simulated balance data (not connected to real API)")
        initial_capital = self.account_config.get('initial_capital', 1000000)
        balance = {'total_assets': initial_capital, 'available_cash': initial_capital, 'frozen_cash': 0, 'market_value': 0, 'total_pnl': 0, 'total_pnl_pct': 0}
        self._cache['balance'] = balance
        self._cache['last_update'] = time.time()
        return balance
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[dict]:
        if not self.is_logged_in:
            raise BrokerConnectionError("Not logged in")
        logger.warning("[SIMULATED] Using simulated order data (not connected to real API)")
        orders = []
        if status:
            orders = [o for o in orders if o.get('status') == status.value]
        return orders
    
    def _hash_password(self, password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()
    
    def _is_cache_valid(self, max_age: int = 5) -> bool:
        if self._cache['last_update'] is None:
            return False
        age = time.time() - self._cache['last_update']
        return age < max_age
    
    def _clear_cache(self):
        self._cache = {'positions': None, 'balance': None, 'orders': None, 'last_update': None}
