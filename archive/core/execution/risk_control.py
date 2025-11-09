"""
Risk Control System.
Implements pre-trade and post-trade risk controls for A-share trading.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Order, OrderStatus, OrderSide, Position, TradingBoard
from core.data.models import OrderRequest
from core.utils.helpers import get_trading_board, calculate_position_value
from config.settings import settings


class RiskControl:
    """
    Risk Control System.

    Handles:
    - Pre-trade risk checks
    - Position size limits
    - Sector concentration
    - Correlation limits
    - Regulatory compliance
    - Cash availability
    """

    def __init__(self):
        """Initialize risk control system."""
        # Configuration
        self.max_position_pct = settings.max_position_pct  # 10%
        self.max_sector_pct = settings.max_sector_pct  # 30%
        self.max_correlation = settings.max_correlation  # 0.7
        self.default_stop_loss_pct = settings.default_stop_loss_pct  # 8%
        self.default_take_profit_pct = settings.default_take_profit_pct  # 15%

        # Regulatory limits (A-share)
        self.max_orders_per_second = 300  # Program trading threshold
        self.max_orders_per_day = 20000  # Daily reporting threshold

        # Order tracking for rate limiting
        self.order_timestamps: List[datetime] = []
        self.daily_order_count = 0
        self.last_reset_date = datetime.utcnow().date()

        logger.info("RiskControl initialized")

    async def check_order(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Dict:
        """
        Perform pre-trade risk checks on order.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Risk check result with 'passed' boolean and 'reason' if failed
        """
        # 1. Check rate limits (regulatory compliance)
        rate_check = await self._check_rate_limits()
        if not rate_check['passed']:
            return rate_check

        # 2. Check position size limits
        position_check = await self._check_position_size(request, db_session)
        if not position_check['passed']:
            return position_check

        # 3. Check sector concentration
        sector_check = await self._check_sector_concentration(request, db_session)
        if not sector_check['passed']:
            return sector_check

        # 4. Check cash availability (for buy orders)
        if request.side == OrderSide.BUY:
            cash_check = await self._check_cash_availability(request, db_session)
            if not cash_check['passed']:
                return cash_check

        # 5. Check position exists (for sell orders)
        if request.side == OrderSide.SELL:
            holding_check = await self._check_holding_availability(request, db_session)
            if not holding_check['passed']:
                return holding_check

        # 6. Check correlation limits (for new positions)
        correlation_check = await self._check_correlation_limits(request, db_session)
        if not correlation_check['passed']:
            return correlation_check

        # 7. Validate stop-loss and take-profit
        sl_tp_check = self._check_stop_loss_take_profit(request)
        if not sl_tp_check['passed']:
            return sl_tp_check

        # All checks passed
        logger.info(f"Risk checks passed for {request.symbol} {request.side} {request.quantity}")

        return {
            'passed': True,
            'reason': None
        }

    async def _check_rate_limits(self) -> Dict:
        """
        Check order rate limits for regulatory compliance.

        A-share regulations:
        - 300 orders/second triggers program trading reporting
        - 20,000 orders/day triggers daily reporting

        Returns:
            Check result
        """
        now = datetime.utcnow()

        # Reset daily counter if new day
        if now.date() != self.last_reset_date:
            self.daily_order_count = 0
            self.last_reset_date = now.date()

        # Check daily limit
        if self.daily_order_count >= self.max_orders_per_day:
            logger.warning(f"Daily order limit reached: {self.daily_order_count}")
            return {
                'passed': False,
                'reason': f"每日订单量已达上限 ({self.max_orders_per_day})"
            }

        # Check per-second limit (last 1 second)
        one_second_ago = now - timedelta(seconds=1)
        self.order_timestamps = [ts for ts in self.order_timestamps if ts > one_second_ago]

        if len(self.order_timestamps) >= self.max_orders_per_second:
            logger.warning(f"Order rate limit exceeded: {len(self.order_timestamps)}/sec")
            return {
                'passed': False,
                'reason': f"订单频率过高 ({len(self.order_timestamps)}/秒)"
            }

        # Update tracking
        self.order_timestamps.append(now)
        self.daily_order_count += 1

        return {'passed': True}

    async def _check_position_size(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Dict:
        """
        Check position size limits.

        Maximum single position: 10% of portfolio value.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Check result
        """
        # Get current portfolio value
        portfolio_value = await self._get_portfolio_value(db_session)

        if portfolio_value <= 0:
            logger.warning("Portfolio value is 0 or negative")
            return {
                'passed': False,
                'reason': "组合净值为零或负数"
            }

        # Calculate order value
        order_value = request.price * request.quantity if request.price else Decimal('0')

        # For market orders, estimate using recent price (simplified)
        if not request.price:
            # In production, would fetch latest price
            order_value = Decimal('10.00') * request.quantity

        # Get existing position value
        existing_position_value = await self._get_position_value(request.symbol, db_session)

        # Calculate new position value (buy adds, sell reduces)
        if request.side == OrderSide.BUY:
            new_position_value = existing_position_value + order_value
        else:
            new_position_value = existing_position_value - order_value

        # Check limit
        position_pct = float(new_position_value / portfolio_value)

        if position_pct > self.max_position_pct:
            logger.warning(
                f"Position size limit exceeded: {position_pct:.2%} > {self.max_position_pct:.2%}"
            )
            return {
                'passed': False,
                'reason': f"单一持仓超限 ({position_pct:.2%} > {self.max_position_pct:.2%})"
            }

        return {'passed': True}

    async def _check_sector_concentration(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Dict:
        """
        Check sector concentration limits.

        Maximum sector exposure: 30% of portfolio value.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Check result
        """
        # Get portfolio value
        portfolio_value = await self._get_portfolio_value(db_session)

        if portfolio_value <= 0:
            return {'passed': True}  # No portfolio yet

        # Get sector for symbol (simplified - would use actual sector data)
        sector = self._get_sector(request.symbol)

        # Get current sector exposure
        sector_value = await self._get_sector_value(sector, db_session)

        # Calculate order value
        order_value = request.price * request.quantity if request.price else Decimal('10.00') * request.quantity

        # Calculate new sector value
        if request.side == OrderSide.BUY:
            new_sector_value = sector_value + order_value
        else:
            new_sector_value = sector_value - order_value

        # Check limit
        sector_pct = float(new_sector_value / portfolio_value)

        if sector_pct > self.max_sector_pct:
            logger.warning(
                f"Sector concentration limit exceeded: {sector_pct:.2%} > {self.max_sector_pct:.2%}"
            )
            return {
                'passed': False,
                'reason': f"行业集中度超限 ({sector}:{sector_pct:.2%} > {self.max_sector_pct:.2%})"
            }

        return {'passed': True}

    async def _check_cash_availability(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Dict:
        """
        Check cash availability for buy orders.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Check result
        """
        # Calculate required cash (order value + commission + buffer)
        order_value = request.price * request.quantity if request.price else Decimal('10.00') * request.quantity

        # Estimate commission (0.03% minimum 5 RMB)
        commission = max(order_value * Decimal('0.0003'), Decimal('5.00'))

        required_cash = order_value + commission

        # Get available cash
        available_cash = await self._get_available_cash(db_session)

        if available_cash < required_cash:
            logger.warning(
                f"Insufficient cash: required={required_cash}, available={available_cash}"
            )
            return {
                'passed': False,
                'reason': f"现金不足 (需要 ¥{required_cash:.2f}, 可用 ¥{available_cash:.2f})"
            }

        return {'passed': True}

    async def _check_holding_availability(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Dict:
        """
        Check holding availability for sell orders.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Check result
        """
        # Get current position
        stmt = select(Position).where(Position.symbol == request.symbol)
        result = await db_session.execute(stmt)
        position = result.scalar_one_or_none()

        if not position:
            logger.warning(f"No position exists for {request.symbol}")
            return {
                'passed': False,
                'reason': f"未持有 {request.symbol}"
            }

        if position.quantity < request.quantity:
            logger.warning(
                f"Insufficient holding: have={position.quantity}, need={request.quantity}"
            )
            return {
                'passed': False,
                'reason': f"持仓不足 (持有 {position.quantity}, 卖出 {request.quantity})"
            }

        return {'passed': True}

    async def _check_correlation_limits(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Dict:
        """
        Check correlation limits with existing positions.

        Prevents over-concentration in correlated stocks.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Check result
        """
        # Only check for new buy orders
        if request.side == OrderSide.SELL:
            return {'passed': True}

        # Get existing positions
        stmt = select(Position)
        result = await db_session.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            return {'passed': True}  # No existing positions

        # Check correlation with each position (simplified)
        # In production, would use actual correlation matrix
        for position in positions:
            correlation = self._estimate_correlation(request.symbol, position.symbol)

            if correlation > self.max_correlation:
                logger.warning(
                    f"High correlation detected: {request.symbol} <-> {position.symbol} = {correlation:.2f}"
                )
                return {
                    'passed': False,
                    'reason': f"与持仓 {position.symbol} 相关性过高 ({correlation:.2f})"
                }

        return {'passed': True}

    def _check_stop_loss_take_profit(self, request: OrderRequest) -> Dict:
        """
        Validate stop-loss and take-profit levels.

        Args:
            request: Order request

        Returns:
            Check result
        """
        if not request.price:
            return {'passed': True}  # Market order, no validation needed

        # Check stop-loss
        if request.stop_loss_price:
            if request.side == OrderSide.BUY:
                # Stop-loss should be below entry price
                if request.stop_loss_price >= request.price:
                    return {
                        'passed': False,
                        'reason': "止损价必须低于入场价"
                    }

                # Check stop-loss percentage
                sl_pct = float((request.price - request.stop_loss_price) / request.price)
                if sl_pct > 0.20:  # Max 20% stop-loss
                    return {
                        'passed': False,
                        'reason': f"止损幅度过大 ({sl_pct:.2%})"
                    }

            else:  # SELL order
                # Stop-loss should be above entry price
                if request.stop_loss_price <= request.price:
                    return {
                        'passed': False,
                        'reason': "止损价必须高于卖出价"
                    }

        # Check take-profit
        if request.take_profit_price:
            if request.side == OrderSide.BUY:
                # Take-profit should be above entry price
                if request.take_profit_price <= request.price:
                    return {
                        'passed': False,
                        'reason': "止盈价必须高于入场价"
                    }

            else:  # SELL order
                # Take-profit should be below entry price
                if request.take_profit_price >= request.price:
                    return {
                        'passed': False,
                        'reason': "止盈价必须低于卖出价"
                    }

        return {'passed': True}

    async def _get_portfolio_value(self, db_session: AsyncSession) -> Decimal:
        """
        Get current portfolio value.

        Args:
            db_session: Database session

        Returns:
            Total portfolio value
        """
        # Get all positions
        stmt = select(Position)
        result = await db_session.execute(stmt)
        positions = result.scalars().all()

        total_value = Decimal('0')

        for position in positions:
            # In production, would use current market price
            position_value = position.avg_cost * position.quantity
            total_value += position_value

        # Add cash (from settings for now)
        total_value += Decimal(str(settings.initial_cash))

        return total_value

    async def _get_position_value(
        self,
        symbol: str,
        db_session: AsyncSession
    ) -> Decimal:
        """
        Get value of specific position.

        Args:
            symbol: Stock symbol
            db_session: Database session

        Returns:
            Position value
        """
        stmt = select(Position).where(Position.symbol == symbol)
        result = await db_session.execute(stmt)
        position = result.scalar_one_or_none()

        if not position:
            return Decimal('0')

        # In production, use current market price
        return position.avg_cost * position.quantity

    async def _get_sector_value(
        self,
        sector: str,
        db_session: AsyncSession
    ) -> Decimal:
        """
        Get total value of positions in a sector.

        Args:
            sector: Sector name
            db_session: Database session

        Returns:
            Sector total value
        """
        # Get all positions
        stmt = select(Position)
        result = await db_session.execute(stmt)
        positions = result.scalars().all()

        sector_value = Decimal('0')

        for position in positions:
            position_sector = self._get_sector(position.symbol)
            if position_sector == sector:
                sector_value += position.avg_cost * position.quantity

        return sector_value

    async def _get_available_cash(self, db_session: AsyncSession) -> Decimal:
        """
        Get available cash for trading.

        Args:
            db_session: Database session

        Returns:
            Available cash
        """
        # Simplified - in production would track cash separately
        # Here we use initial cash minus position values

        portfolio_value = await self._get_portfolio_value(db_session)

        # Get total position value
        stmt = select(Position)
        result = await db_session.execute(stmt)
        positions = result.scalars().all()

        position_value = sum(
            pos.avg_cost * pos.quantity for pos in positions
        )

        available = portfolio_value - position_value

        return max(Decimal('0'), available)

    def _get_sector(self, symbol: str) -> str:
        """
        Get sector for symbol (simplified).

        In production, would query from database or external API.

        Args:
            symbol: Stock symbol

        Returns:
            Sector name
        """
        # Simplified sector mapping based on symbol prefix
        if symbol.startswith('60'):
            return "主板"
        elif symbol.startswith('688'):
            return "科创板"
        elif symbol.startswith('300'):
            return "创业板"
        else:
            return "其他"

    def _estimate_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Estimate correlation between two symbols (simplified).

        In production, would calculate from historical price data.

        Args:
            symbol1: First symbol
            symbol2: Second symbol

        Returns:
            Correlation coefficient
        """
        # Same sector = higher correlation
        sector1 = self._get_sector(symbol1)
        sector2 = self._get_sector(symbol2)

        if sector1 == sector2:
            return 0.6  # Moderate correlation within sector
        else:
            return 0.3  # Low correlation across sectors

    async def check_position_risk(
        self,
        position: Position,
        current_price: Decimal,
        db_session: AsyncSession
    ) -> Dict:
        """
        Check risk levels for existing position.

        Post-trade risk monitoring.

        Args:
            position: Position to check
            current_price: Current market price
            db_session: Database session

        Returns:
            Risk assessment
        """
        risks = []

        # Calculate P&L
        pnl_pct = float((current_price - position.avg_cost) / position.avg_cost)

        # Check stop-loss breach
        if pnl_pct < -self.default_stop_loss_pct:
            risks.append({
                'type': 'stop_loss_breach',
                'severity': 'high',
                'message': f"持仓 {position.symbol} 亏损达 {pnl_pct:.2%}, 建议止损"
            })

        # Check extreme profit (consider taking profit)
        if pnl_pct > self.default_take_profit_pct * 2:
            risks.append({
                'type': 'profit_target',
                'severity': 'low',
                'message': f"持仓 {position.symbol} 盈利达 {pnl_pct:.2%}, 考虑止盈"
            })

        # Check holding duration (for swing trading)
        if position.entry_date:
            holding_days = (datetime.utcnow() - position.entry_date).days
            if holding_days > 30:
                risks.append({
                    'type': 'holding_duration',
                    'severity': 'medium',
                    'message': f"持仓 {position.symbol} 已持有 {holding_days} 天"
                })

        return {
            'symbol': position.symbol,
            'pnl_pct': pnl_pct,
            'risks': risks,
            'risk_level': 'high' if any(r['severity'] == 'high' for r in risks) else 'low'
        }
