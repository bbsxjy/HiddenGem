# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overall rules
1. Please seperate front-end and back-end implementations into different folders. And create claude read me for each of them, so that later you know what to do and what to continue.
2. For front-end project, please follow the following:
 (1) 不要用mock data或者leave todo
 (2) 请严格遵守Claude.md中规定的规则进行实施
 (3) 使用ultrathink
 (4) 不要使用mock data作为fall back的方案
 (5) 在修复或新增新内容前，使用git，commit之前的工作
 (6) 不要启动服务器，由用户自己启动
3. For back-end project, please follow the following:
 (1) 请严格遵守Claude.md中规定的规则进行实施
 (2) 使用ultrathink
 (3) 不要使用mock data作为fall back的方案
 (4) 在修复或新增新内容前，使用git，commit之前的工作
 (5) 不要启动服务器，由用户自己启动

## Project Overview

HiddenGem is a mid-to-low frequency quantitative trading system designed for the Chinese A-share market. The system uses MCP (Model Context Protocol) agents for intelligent trading decisions, supporting swing trading (several days to weeks) and trend following strategies (weeks to months).

**Current Status**: This repository is in the planning/design phase. The codebase contains system design documentation but no implementation code yet.

## System Architecture

### Multi-Agent Architecture (MCP-based)

The system is designed around 7 specialized agents that collaborate via the Model Context Protocol:

1. **PolicyAnalystAgent** - Analyzes government policies, regulations, and industry directives
2. **MarketMonitorAgent** - Tracks northbound capital flows, margin trading, and market sentiment
3. **TechnicalAnalysisAgent** - Computes technical indicators (RSI, turnover rate, MACD, etc.)
4. **FundamentalAgent** - Analyzes financial metrics (PE, PB, ROE, debt ratios)
5. **SentimentAgent** - Processes social media and news sentiment
6. **RiskManagerAgent** - Evaluates A-share specific risks (pledge ratios, restricted shares, goodwill)
7. **ExecutionAgent** - Generates trading signals and executes orders

### Recommended Technology Stack

**Core Frameworks:**
- Strategy development & backtesting: RQAlpha (native A-share support)
- Live trading execution: VNpy (comprehensive broker API integration)
- AI model research: Qlib (Microsoft AI quantitative platform)
- MCP integration: mcp-agent framework

**Data & Storage:**
- Time-series database: TimescaleDB (PostgreSQL extension)
- Real-time cache: Redis
- Message queue: Apache Kafka (high throughput) or Redis Streams (low latency)

**Data Sources:**
- Tushare Pro or JoinQuant for market data
- AkShare for alternative data sources

### Architecture Patterns

Three deployment architectures are planned:

1. **Modular Monolith** (recommended for initial development) - Fast development, simple deployment
2. **Microservices** (recommended for production) - Scalable, fault-isolated, independent deployment
3. **Cloud-Native** (recommended for large-scale) - Kubernetes orchestration with managed cloud services

## Project Structure (Planned)

```
trading_system/
├── core/
│   ├── mcp_agents/          # MCP Agent modules
│   │   ├── policy_agent.py
│   │   ├── market_agent.py
│   │   └── orchestrator.py
│   ├── strategy/            # Strategy engine
│   │   ├── swing_trading.py # Swing trading strategies
│   │   └── trend_following.py # Trend following strategies
│   ├── data/               # Data processing
│   │   ├── ingestion.py
│   │   └── preprocessing.py
│   └── execution/          # Trade execution
│       ├── order_manager.py
│       └── risk_control.py
├── api/                    # FastAPI interfaces
├── config/                 # Configuration management
└── tests/                  # Test modules
```

## A-Share Market Specifics

When implementing features for this system, be aware of Chinese A-share market characteristics:

**Trading Board Support:**
- Main Board (0.1 price limit, no capital requirement)
- ChiNext/Growth Enterprise Board (0.2 price limit, 100K RMB minimum)
- STAR Market (0.2 price limit, 500K RMB minimum)

**Special Risk Factors:**
- Share pledge ratios (high risk if >50%)
- Restricted share unlock schedules
- Goodwill impairment risks (high risk if >30% of assets)

**Regulatory Compliance:**
- Program trading reporting thresholds: 300 orders/second or 20,000 orders/day
- New regulations effective July 7, 2025 require disclosure of fund scale, leverage sources, trading strategies, and server location

**Market-Specific Indicators:**
- Northbound capital flows (via Stock Connect)
- Margin trading balances
- Institutional holding changes
- Turnover rates

## Risk Management Rules

When implementing trading logic:

- Maximum single position: 10% of portfolio
- Maximum sector exposure: 30% of portfolio
- Default stop-loss: 8%
- Default take-profit: 15%
- Position sizing must account for volatility adjustment
- Always check correlation limits before new positions

## Implementation Roadmap

**Phase 1 (1-2 months)**: Environment setup, MCP agent infrastructure, data ingestion
**Phase 2 (2-3 months)**: Strategy development, agent functionality, backtesting system
**Phase 3 (3-4 months)**: Live trading interface integration, risk management refinement
**Phase 4 (4-6 months)**: Simulated trading tests, small-capital live validation, monitoring/operations

## Key Design Patterns

**Event-Driven Architecture**: The system uses event-driven patterns for real-time market data processing and order execution.

**Agent Communication**: All inter-agent communication follows JSON-RPC 2.0 protocol via MCP, supporting stdio, HTTP with SSE, and WebSocket transports.

**Signal Aggregation**: Trading signals from multiple agents are aggregated with weighted scores before execution decisions.

## Documentation Files

- `HiddenGem系统实现方案.md` - Detailed implementation plan including MCP architecture, framework comparisons, code examples, deployment strategies, and compliance considerations
- `HiddenGem系统设计（High&LowLevel&UseCase）.html` - System design document covering high-level architecture, low-level design, and use cases
