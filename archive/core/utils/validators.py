"""
Data validation utilities.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from loguru import logger


class DataValidator:
    """Validates market data and trading inputs."""

    @staticmethod
    def validate_ohlcv(data: Dict[str, Any]) -> bool:
        """
        Validate OHLCV data structure and values.

        Args:
            data: Dictionary with OHLCV data

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['open', 'high', 'low', 'close', 'volume']

        # Check all required fields present
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required OHLCV fields: {required_fields}")
            return False

        try:
            open_price = float(data['open'])
            high_price = float(data['high'])
            low_price = float(data['low'])
            close_price = float(data['close'])
            volume = int(data['volume'])

            # Validate price relationships
            if not (low_price <= open_price <= high_price):
                logger.error("Invalid OHLCV: open not within high/low range")
                return False

            if not (low_price <= close_price <= high_price):
                logger.error("Invalid OHLCV: close not within high/low range")
                return False

            # Validate positive values
            if any(p <= 0 for p in [open_price, high_price, low_price, close_price]):
                logger.error("Invalid OHLCV: prices must be positive")
                return False

            if volume < 0:
                logger.error("Invalid OHLCV: volume cannot be negative")
                return False

            return True

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid OHLCV data types: {e}")
            return False

    @staticmethod
    def validate_price_movement(
        old_price: Decimal,
        new_price: Decimal,
        max_change_pct: float = 0.25
    ) -> bool:
        """
        Validate that price movement is reasonable.

        Args:
            old_price: Previous price
            new_price: New price
            max_change_pct: Maximum allowed change percentage

        Returns:
            True if movement is reasonable
        """
        try:
            if old_price <= 0 or new_price <= 0:
                logger.error("Prices must be positive")
                return False

            change_pct = abs(float((new_price - old_price) / old_price))

            if change_pct > max_change_pct:
                logger.warning(
                    f"Large price movement: {change_pct:.2%} "
                    f"(old={old_price}, new={new_price})"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating price movement: {e}")
            return False

    @staticmethod
    def validate_order_quantity(
        quantity: int,
        min_lot: int = 100,
        max_quantity: int = 1000000
    ) -> bool:
        """
        Validate order quantity for A-share.

        Args:
            quantity: Number of shares
            min_lot: Minimum lot size (100 for A-share)
            max_quantity: Maximum allowed quantity

        Returns:
            True if valid
        """
        # Must be positive
        if quantity <= 0:
            logger.error("Quantity must be positive")
            return False

        # Must be multiple of lot size
        if quantity % min_lot != 0:
            logger.error(f"Quantity must be multiple of {min_lot}")
            return False

        # Check maximum
        if quantity > max_quantity:
            logger.error(f"Quantity exceeds maximum {max_quantity}")
            return False

        return True

    @staticmethod
    def validate_price(
        price: Decimal,
        min_price: Decimal = Decimal('0.01'),
        max_price: Decimal = Decimal('10000.00')
    ) -> bool:
        """
        Validate price value.

        Args:
            price: Price to validate
            min_price: Minimum allowed price
            max_price: Maximum allowed price

        Returns:
            True if valid
        """
        try:
            if price < min_price:
                logger.error(f"Price {price} below minimum {min_price}")
                return False

            if price > max_price:
                logger.error(f"Price {price} above maximum {max_price}")
                return False

            # Check decimal places (A-share uses 2 decimal places)
            if price.as_tuple().exponent < -2:
                logger.error("Price has too many decimal places (max 2)")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating price: {e}")
            return False

    @staticmethod
    def validate_date_range(
        start_date: datetime,
        end_date: datetime,
        max_days: int = 3650
    ) -> bool:
        """
        Validate date range for data queries.

        Args:
            start_date: Start date
            end_date: End date
            max_days: Maximum allowed days in range

        Returns:
            True if valid
        """
        if start_date >= end_date:
            logger.error("Start date must be before end date")
            return False

        days_diff = (end_date - start_date).days

        if days_diff > max_days:
            logger.error(f"Date range {days_diff} days exceeds maximum {max_days}")
            return False

        if end_date > datetime.now():
            logger.warning("End date is in the future")
            # Allow but warn
            return True

        return True

    @staticmethod
    def validate_position_size(
        position_value: Decimal,
        portfolio_value: Decimal,
        max_position_pct: float = 0.10
    ) -> bool:
        """
        Validate position size against portfolio limits.

        Args:
            position_value: Value of the position
            portfolio_value: Total portfolio value
            max_position_pct: Maximum position percentage

        Returns:
            True if within limits
        """
        if portfolio_value <= 0:
            logger.error("Portfolio value must be positive")
            return False

        position_pct = float(position_value / portfolio_value)

        if position_pct > max_position_pct:
            logger.error(
                f"Position size {position_pct:.2%} exceeds "
                f"maximum {max_position_pct:.2%}"
            )
            return False

        return True

    @staticmethod
    def validate_signal_strength(strength: float) -> bool:
        """
        Validate signal strength value.

        Args:
            strength: Signal strength (should be 0.0 to 1.0)

        Returns:
            True if valid
        """
        if not (0.0 <= strength <= 1.0):
            logger.error(f"Signal strength {strength} not in range [0.0, 1.0]")
            return False

        return True

    @staticmethod
    def validate_risk_metrics(
        pledge_ratio: Optional[float] = None,
        goodwill_ratio: Optional[float] = None,
        debt_to_equity: Optional[float] = None
    ) -> Dict[str, bool]:
        """
        Validate A-share specific risk metrics.

        Args:
            pledge_ratio: Share pledge ratio
            goodwill_ratio: Goodwill to assets ratio
            debt_to_equity: Debt to equity ratio

        Returns:
            Dictionary of metric to validity
        """
        results = {}

        if pledge_ratio is not None:
            # Valid range: 0% to 100%
            results['pledge_ratio'] = 0.0 <= pledge_ratio <= 1.0
            if not results['pledge_ratio']:
                logger.error(f"Invalid pledge ratio: {pledge_ratio}")

        if goodwill_ratio is not None:
            # Valid range: 0% to 100% (though >100% is theoretically possible)
            results['goodwill_ratio'] = 0.0 <= goodwill_ratio <= 2.0
            if not results['goodwill_ratio']:
                logger.error(f"Invalid goodwill ratio: {goodwill_ratio}")

        if debt_to_equity is not None:
            # Valid range: 0 to reasonable max (10x)
            results['debt_to_equity'] = 0.0 <= debt_to_equity <= 10.0
            if not results['debt_to_equity']:
                logger.error(f"Invalid debt to equity: {debt_to_equity}")

        return results


class SanityChecker:
    """Performs sanity checks on trading system state."""

    @staticmethod
    def check_portfolio_consistency(
        positions_value: Decimal,
        cash: Decimal,
        total_value: Decimal,
        tolerance: Decimal = Decimal('0.01')
    ) -> bool:
        """
        Check portfolio value consistency.

        Args:
            positions_value: Sum of all position values
            cash: Cash balance
            total_value: Reported total portfolio value
            tolerance: Allowed difference

        Returns:
            True if consistent
        """
        calculated_total = positions_value + cash
        difference = abs(calculated_total - total_value)

        if difference > tolerance:
            logger.error(
                f"Portfolio inconsistency: "
                f"positions({positions_value}) + cash({cash}) = {calculated_total} "
                f"!= total({total_value}), diff={difference}"
            )
            return False

        return True

    @staticmethod
    def check_order_fill_price(
        order_price: Decimal,
        fill_price: Decimal,
        max_slippage: float = 0.01
    ) -> bool:
        """
        Check if fill price is reasonable compared to order price.

        Args:
            order_price: Original order price
            fill_price: Actual fill price
            max_slippage: Maximum allowed slippage

        Returns:
            True if reasonable
        """
        if order_price <= 0:
            # Market order or invalid price
            return True

        slippage = abs(float((fill_price - order_price) / order_price))

        if slippage > max_slippage:
            logger.warning(
                f"High slippage: {slippage:.2%} "
                f"(order={order_price}, fill={fill_price})"
            )
            return False

        return True
