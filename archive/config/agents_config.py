"""
MCP Agent configurations.
Defines parameters and weights for each agent in the system.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a single MCP agent."""

    name: str
    enabled: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=1.0)  # Weight in signal aggregation
    timeout: int = Field(default=30, ge=1)  # Timeout in seconds
    retry_attempts: int = Field(default=3, ge=0)
    cache_ttl: int = Field(default=300, ge=0)  # Cache time-to-live in seconds
    params: Dict[str, Any] = Field(default_factory=dict)


class AgentsConfiguration:
    """Central configuration for all MCP agents."""

    # PolicyAnalystAgent configuration
    POLICY_AGENT = AgentConfig(
        name="PolicyAnalystAgent",
        enabled=True,
        weight=0.15,  # 15% weight in signal aggregation
        timeout=60,  # Longer timeout for LLM analysis
        retry_attempts=2,
        cache_ttl=3600,  # Cache policy analysis for 1 hour
        params={
            "sources": [
                "http://www.csrc.gov.cn",  # China Securities Regulatory Commission
                "http://www.pbc.gov.cn",   # People's Bank of China
                "https://www.ndrc.gov.cn"  # National Development and Reform Commission
            ],
            "llm_model": "gpt-4",
            "max_policy_age_days": 30,  # Only analyze policies from last 30 days
            "min_relevance_score": 0.6
        }
    )

    # MarketMonitorAgent configuration
    MARKET_AGENT = AgentConfig(
        name="MarketMonitorAgent",
        enabled=True,
        weight=0.20,  # 20% weight - market sentiment is important
        timeout=15,
        retry_attempts=3,
        cache_ttl=60,  # Cache for 1 minute - real-time data
        params={
            "northbound_threshold": 100000000,  # 100M RMB threshold for signals
            "margin_change_threshold": 0.05,  # 5% change threshold
            "sentiment_sources": ["eastmoney", "xueqiu", "tushare"],
            "market_phases": ["bull", "bear", "consolidation", "volatile"]
        }
    )

    # TechnicalAnalysisAgent configuration
    TECHNICAL_AGENT = AgentConfig(
        name="TechnicalAnalysisAgent",
        enabled=True,
        weight=0.25,  # 25% weight - technical analysis is core
        timeout=10,
        retry_attempts=2,
        cache_ttl=300,  # Cache for 5 minutes
        params={
            "indicators": [
                "rsi",
                "macd",
                "ma_5_10_20_60",
                "bollinger_bands",
                "kdj",
                "turnover_rate"
            ],
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "ma_short": 5,
            "ma_medium": 20,
            "ma_long": 60,
            "lookback_days": 60
        }
    )

    # FundamentalAgent configuration
    FUNDAMENTAL_AGENT = AgentConfig(
        name="FundamentalAgent",
        enabled=True,
        weight=0.20,  # 20% weight - fundamentals important for mid-term
        timeout=20,
        retry_attempts=2,
        cache_ttl=86400,  # Cache for 24 hours - fundamentals change slowly
        params={
            "metrics": [
                "pe_ratio",
                "pb_ratio",
                "roe",
                "debt_to_equity",
                "profit_growth_yoy",
                "revenue_growth_yoy"
            ],
            "pe_low_threshold": 15,
            "pe_high_threshold": 50,
            "pb_low_threshold": 1.0,
            "roe_min_threshold": 0.10,  # 10% minimum ROE
            "debt_max_threshold": 0.70,  # 70% max debt-to-equity
            "industry_comparison": True
        }
    )

    # SentimentAgent configuration
    SENTIMENT_AGENT = AgentConfig(
        name="SentimentAgent",
        enabled=True,
        weight=0.10,  # 10% weight - sentiment is supplementary
        timeout=30,
        retry_attempts=2,
        cache_ttl=600,  # Cache for 10 minutes
        params={
            "sources": [
                "weibo",
                "xueqiu",
                "eastmoney_guba",
                "news_apis"
            ],
            "llm_model": "gpt-3.5-turbo",
            "sentiment_scale": [-1, 1],  # -1 (negative) to 1 (positive)
            "min_mentions": 10,  # Minimum mentions for relevance
            "lookback_hours": 24
        }
    )

    # RiskManagerAgent configuration
    RISK_AGENT = AgentConfig(
        name="RiskManagerAgent",
        enabled=True,
        weight=0.10,  # 10% weight - acts as validator/filter
        timeout=15,
        retry_attempts=3,
        cache_ttl=3600,  # Cache for 1 hour
        params={
            # A-share specific risks
            "pledge_ratio_warning": 0.30,  # 30% pledge ratio warning
            "pledge_ratio_danger": 0.50,   # 50% pledge ratio danger
            "goodwill_ratio_warning": 0.20,  # 20% of assets
            "goodwill_ratio_danger": 0.30,   # 30% of assets
            "restricted_share_unlock_days": 90,  # Alert if unlock within 90 days

            # Portfolio risks
            "max_position_correlation": 0.70,  # Max 0.7 correlation with existing
            "max_sector_concentration": 0.30,  # Max 30% in one sector
            "max_single_position": 0.10,  # Max 10% in one stock

            # General risks
            "volatility_percentile_threshold": 0.80,  # Alert if volatility > 80th percentile
            "liquidity_min_volume": 1000000  # Minimum daily volume in shares
        }
    )

    # ExecutionAgent configuration
    EXECUTION_AGENT = AgentConfig(
        name="ExecutionAgent",
        enabled=True,
        weight=1.0,  # Not used in signal aggregation
        timeout=10,
        retry_attempts=3,
        cache_ttl=0,  # No caching for execution
        params={
            "signal_aggregation_method": "weighted_average",
            "min_signal_strength": 0.60,  # Minimum 60% strength to act
            "min_agent_agreement": 3,  # At least 3 agents must agree
            "position_sizing_method": "volatility_adjusted",
            "max_slippage_pct": 0.005,  # 0.5% max slippage
            "order_timeout_seconds": 30
        }
    )

    @classmethod
    def get_all_agents(cls) -> Dict[str, AgentConfig]:
        """
        Get all agent configurations.

        Returns:
            Dict[str, AgentConfig]: Dictionary of agent name to config
        """
        return {
            "policy": cls.POLICY_AGENT,
            "market": cls.MARKET_AGENT,
            "technical": cls.TECHNICAL_AGENT,
            "fundamental": cls.FUNDAMENTAL_AGENT,
            "sentiment": cls.SENTIMENT_AGENT,
            "risk": cls.RISK_AGENT,
            "execution": cls.EXECUTION_AGENT
        }

    @classmethod
    def get_enabled_agents(cls) -> Dict[str, AgentConfig]:
        """
        Get only enabled agent configurations.

        Returns:
            Dict[str, AgentConfig]: Dictionary of enabled agents
        """
        return {
            name: config
            for name, config in cls.get_all_agents().items()
            if config.enabled
        }

    @classmethod
    def get_agent_weights(cls) -> Dict[str, float]:
        """
        Get agent weights for signal aggregation.
        Excludes ExecutionAgent as it doesn't participate in aggregation.

        Returns:
            Dict[str, float]: Dictionary of agent weights (normalized to sum to 1.0)
        """
        agents = cls.get_enabled_agents()
        # Exclude execution agent from weights
        weights = {
            name: config.weight
            for name, config in agents.items()
            if name != "execution"
        }

        # Normalize weights to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {name: w / total for name, w in weights.items()}

        return weights


# Global agents configuration instance
agents_config = AgentsConfiguration()
