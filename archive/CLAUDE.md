# Backend CLAUDE.md

This file provides guidance for implementing the HiddenGem backend quantitative trading system.

## Overall Rules

1. **No Mock Data**: Never use mock data or leave TODO comments. All implementations must be complete and functional.
2. **Follow Specifications**: Strictly follow the rules defined in the root CLAUDE.md and this document.
3. **Git Commits**: Before fixing or adding new content, commit previous work using git.
4. **No Server Startup**: Do not start servers - let the user handle server startup.
5. **Use Ultrathink**: Apply careful reasoning for complex implementations.

## Technology Stack

**Core Frameworks:**
- Python 3.11+
- FastAPI for REST API
- RQAlpha for strategy development & backtesting
- VNpy for live trading execution
- Qlib for AI model research (optional)

**MCP Integration:**
- mcp-agent framework for agent orchestration
- JSON-RPC 2.0 for agent communication

**Data & Storage:**
- TimescaleDB (PostgreSQL extension) for time-series data
- Redis for caching and real-time data
- Redis Streams for message queue (or Kafka for high throughput)

**Data Sources:**
- Tushare Pro for market data
- AkShare for alternative data
- JoinQuant for real-time data (optional)

**Additional Libraries:**
- pandas, numpy for data processing
- TA-Lib for technical indicators
- asyncio for async operations
- pydantic for data validation
- SQLAlchemy for database ORM

## Project Structure

```
backend/
├── core/
│   ├── __init__.py
│   ├── mcp_agents/              # MCP Agent modules
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Base agent class
│   │   ├── policy_agent.py      # Policy analysis agent
│   │   ├── market_agent.py      # Market monitoring agent
│   │   ├── technical_agent.py   # Technical analysis agent
│   │   ├── fundamental_agent.py # Fundamental analysis agent
│   │   ├── sentiment_agent.py   # Sentiment analysis agent
│   │   ├── risk_agent.py        # Risk management agent
│   │   ├── execution_agent.py   # Execution agent
│   │   └── orchestrator.py      # MCP orchestrator
│   ├── strategy/                # Strategy engine
│   │   ├── __init__.py
│   │   ├── base_strategy.py     # Base strategy class
│   │   ├── swing_trading.py     # Swing trading strategies
│   │   └── trend_following.py   # Trend following strategies
│   ├── data/                    # Data processing
│   │   ├── __init__.py
│   │   ├── ingestion.py         # Data ingestion
│   │   ├── preprocessing.py     # Data preprocessing
│   │   ├── sources.py           # Data source integrations
│   │   └── models.py            # Data models
│   ├── execution/               # Trade execution
│   │   ├── __init__.py
│   │   ├── order_manager.py     # Order management
│   │   ├── risk_control.py      # Risk controls
│   │   └── broker_interface.py  # Broker API interface
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── indicators.py        # Technical indicators
│       ├── validators.py        # Data validators
│       └── helpers.py           # Helper functions
├── api/                         # FastAPI application
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── routes/                  # API routes
│   │   ├── __init__.py
│   │   ├── strategy.py          # Strategy endpoints
│   │   ├── market.py            # Market data endpoints
│   │   ├── portfolio.py         # Portfolio endpoints
│   │   ├── orders.py            # Order endpoints
│   │   └── agents.py            # Agent status endpoints
│   ├── models/                  # Pydantic models
│   │   ├── __init__.py
│   │   ├── request.py           # Request models
│   │   └── response.py          # Response models
│   └── middleware/              # Middleware
│       ├── __init__.py
│       ├── auth.py              # Authentication
│       └── logging.py           # Request logging
├── config/                      # Configuration
│   ├── __init__.py
│   ├── settings.py              # Application settings
│   ├── database.py              # Database configuration
│   └── agents_config.py         # Agent configurations
├── database/                    # Database
│   ├── __init__.py
│   ├── connection.py            # DB connection
│   ├── models.py                # SQLAlchemy models
│   └── migrations/              # Alembic migrations
├── tests/                       # Tests
│   ├── __init__.py
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── conftest.py              # Pytest configuration
├── scripts/                     # Utility scripts
│   ├── init_db.py               # Database initialization
│   ├── backtest.py              # Backtesting script
│   └── data_sync.py             # Data synchronization
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Project configuration
├── .env.example                 # Environment variables example
├── docker-compose.yml           # Docker compose for services
├── Dockerfile                   # Docker image definition
├── CLAUDE.md                    # This file
└── TASKS.md                     # Task tracking file
```

## Key Implementation Details

### MCP Agent Architecture

Each agent must:
1. Inherit from `BaseAgent` class
2. Implement `analyze()` method returning structured analysis
3. Support JSON-RPC 2.0 protocol for communication
4. Handle async operations properly
5. Implement error handling and logging

**Agent Communication Flow:**
1. Orchestrator receives analysis request
2. Orchestrator dispatches tasks to relevant agents in parallel
3. Agents perform analysis and return results
4. Orchestrator aggregates results
5. Results are used for signal generation

### A-Share Market Specific Features

**Trading Board Classification:**
- Implement board detection from stock symbol:
  - 688xxx = STAR Market (科创板)
  - 300xxx = ChiNext (创业板)
  - Others = Main Board (主板)
- Apply board-specific rules (price limits, capital requirements)

**Risk Checks Required:**
1. Share pledge ratio monitoring (>50% = HIGH risk)
2. Restricted share unlock schedule tracking
3. Goodwill impairment risk (>30% of assets = ELEVATED risk)
4. Correlation limit checking
5. Position size validation

**Regulatory Compliance:**
- Track order frequency (300/second, 20,000/day thresholds)
- Log trading activities for reporting
- Implement circuit breakers for regulatory limits

### Data Pipeline

**Ingestion:**
1. Real-time data from Tushare/JoinQuant
2. Store in TimescaleDB (compressed time-series)
3. Cache in Redis for fast access
4. Publish updates via Redis Streams

**Preprocessing:**
1. Data cleaning and validation
2. Technical indicator calculation
3. Feature engineering
4. Normalization and scaling

### Risk Management

**Position Sizing:**
```python
position_size = base_position * signal_strength * volatility_adjustment
position_size = min(position_size, max_position_size)  # 10% cap
```

**Portfolio Limits:**
- Single position: ≤10% of portfolio
- Single sector: ≤30% of portfolio
- Stop-loss: 8% default
- Take-profit: 15% default

### API Design

**REST API Endpoints:**
- `POST /api/v1/strategies/backtest` - Run backtesting
- `GET /api/v1/market/data/{symbol}` - Get market data
- `GET /api/v1/portfolio/positions` - Get current positions
- `POST /api/v1/orders/create` - Create new order
- `GET /api/v1/agents/status` - Get agent status
- `GET /api/v1/signals/current` - Get current trading signals

**WebSocket for Real-time:**
- Market data streaming
- Order status updates
- Agent analysis results
- Portfolio updates

### Database Schema

**Key Tables:**
1. `market_data` (hypertable) - OHLCV data
2. `signals` - Trading signals
3. `orders` - Order history
4. `positions` - Current positions
5. `portfolio_snapshots` - Portfolio state over time
6. `agent_analyses` - Agent analysis results
7. `risk_events` - Risk alert events

## Development Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run tests
pytest tests/

# Run development server (user will do this)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run backtesting
python scripts/backtest.py --strategy swing_trading --start 2024-01-01 --end 2024-12-31

# Data synchronization
python scripts/data_sync.py --source tushare --symbols all
```

## Environment Variables

Required environment variables in `.env`:

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hiddengem
REDIS_URL=redis://localhost:6379/0

# Data Sources
TUSHARE_TOKEN=your_tushare_token
AKSHARE_ENABLED=true
JOINQUANT_USERNAME=your_username
JOINQUANT_PASSWORD=your_password

# Trading
BROKER_API_KEY=your_broker_api_key
BROKER_API_SECRET=your_broker_api_secret
TRADING_MODE=simulation  # or live

# MCP Configuration
MCP_TRANSPORT=stdio  # or http, websocket
MCP_PORT=8001

# Application
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key
```

## Testing Strategy

1. **Unit Tests**: Test individual agent logic, indicators, validators
2. **Integration Tests**: Test agent orchestration, API endpoints
3. **Backtesting**: Validate strategies with historical data
4. **Simulation**: Test with paper trading before going live

## Deployment Notes

**Initial Deployment (Modular Monolith):**
- Single Docker container
- PostgreSQL + TimescaleDB
- Redis
- FastAPI application

**Production Deployment (Microservices):**
- Separate services for agents, API, execution
- Message queue (Kafka/Redis Streams)
- Load balancer
- Monitoring (Prometheus + Grafana)

## Important Notes

1. **Never commit sensitive data**: Use `.env` for secrets, add to `.gitignore`
2. **Data validation**: Always validate input data before processing
3. **Error handling**: Implement comprehensive error handling and logging
4. **Rate limiting**: Respect data provider API rate limits
5. **Async operations**: Use async/await for I/O operations
6. **Type hints**: Use Python type hints for all function signatures
7. **Documentation**: Document all public APIs and complex logic
