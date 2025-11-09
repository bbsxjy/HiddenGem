# Backend Tasks

This file tracks implementation tasks for the HiddenGem backend trading system.

## Task Status Legend
- ⬜ Not Started
- 🟡 In Progress
- ✅ Completed
- ❌ Blocked

---

## Phase 1: Environment Setup & Infrastructure (1-2 months)

### 1.1 Project Initialization
- ⬜ Create Python virtual environment
- ⬜ Set up pyproject.toml with project metadata
- ⬜ Create requirements.txt with all dependencies
- ⬜ Set up .env.example with all required environment variables
- ⬜ Create .gitignore for Python project
- ⬜ Initialize git repository
- ⬜ Create README.md with setup instructions

### 1.2 Database Setup
- ⬜ Install and configure PostgreSQL + TimescaleDB
- ⬜ Create database connection module (database/connection.py)
- ⬜ Define SQLAlchemy models (database/models.py)
  - ⬜ MarketData model (hypertable for time-series)
  - ⬜ Signal model
  - ⬜ Order model
  - ⬜ Position model
  - ⬜ PortfolioSnapshot model
  - ⬜ AgentAnalysis model
  - ⬜ RiskEvent model
- ⬜ Set up Alembic for migrations
- ⬜ Create initial migration
- ⬜ Create database initialization script (scripts/init_db.py)

### 1.3 Redis Setup
- ⬜ Install and configure Redis
- ⬜ Create Redis connection module
- ⬜ Implement caching utilities
- ⬜ Set up Redis Streams for message queue

### 1.4 Configuration Management
- ⬜ Create settings.py with Pydantic BaseSettings
- ⬜ Create database.py for database configuration
- ⬜ Create agents_config.py for agent configurations
- ⬜ Load configuration from environment variables

### 1.5 Data Source Integration
- ⬜ Implement Tushare Pro client (core/data/sources.py)
- ⬜ Implement AkShare client
- ⬜ Create data source aggregator with fallback logic
- ⬜ Implement rate limiting for API calls
- ⬜ Add error handling and retry logic

### 1.6 Data Ingestion Pipeline
- ⬜ Create data ingestion module (core/data/ingestion.py)
- ⬜ Implement real-time data fetcher
- ⬜ Implement historical data fetcher
- ⬜ Create data validation module
- ⬜ Implement TimescaleDB data writer
- ⬜ Set up automatic compression policies
- ⬜ Create data sync script (scripts/data_sync.py)

---

## Phase 2: MCP Agent Architecture & Core Logic (2-3 months)

### 2.1 Base Agent Framework
- ⬜ Create BaseAgent class (core/mcp_agents/base_agent.py)
  - ⬜ Implement JSON-RPC 2.0 message handling
  - ⬜ Add async analyze() method (abstract)
  - ⬜ Implement logging mechanism
  - ⬜ Add error handling
  - ⬜ Create agent state management

### 2.2 MCP Orchestrator
- ⬜ Create MCPOrchestrator class (core/mcp_agents/orchestrator.py)
  - ⬜ Implement agent registration
  - ⬜ Create task dispatcher (parallel agent execution)
  - ⬜ Implement result aggregation
  - ⬜ Add agent health monitoring
  - ⬜ Create agent communication protocol

### 2.3 PolicyAnalystAgent
- ⬜ Create PolicyAnalystAgent class (core/mcp_agents/policy_agent.py)
  - ⬜ Implement policy source scraping (CSRC, PBC, NDRC)
  - ⬜ Add LLM integration for policy analysis
  - ⬜ Implement sector mapping logic
  - ⬜ Create signal generation from policy impacts
  - ⬜ Add caching for policy documents

### 2.4 MarketMonitorAgent
- ⬜ Create MarketMonitorAgent class (core/mcp_agents/market_agent.py)
  - ⬜ Implement northbound capital flow tracker
  - ⬜ Add margin trading balance monitor
  - ⬜ Create market sentiment analyzer
  - ⬜ Implement market phase determination
  - ⬜ Add real-time indicator updates

### 2.5 TechnicalAnalysisAgent
- ⬜ Create TechnicalAnalysisAgent class (core/mcp_agents/technical_agent.py)
  - ⬜ Implement RSI calculation
  - ⬜ Add MACD calculation
  - ⬜ Implement MA (moving average) calculation
  - ⬜ Add turnover rate calculation
  - ⬜ Create pattern recognition (support/resistance)
  - ⬜ Implement trend analysis

### 2.6 FundamentalAgent
- ⬜ Create FundamentalAgent class (core/mcp_agents/fundamental_agent.py)
  - ⬜ Implement PE ratio calculation
  - ⬜ Add PB ratio calculation
  - ⬜ Implement ROE calculation
  - ⬜ Add debt ratio analysis
  - ⬜ Create industry comparison logic
  - ⬜ Implement valuation scoring

### 2.7 SentimentAgent
- ⬜ Create SentimentAgent class (core/mcp_agents/sentiment_agent.py)
  - ⬜ Implement social media scraping (Weibo, etc.)
  - ⬜ Add news sentiment analysis
  - ⬜ Create sentiment scoring algorithm
  - ⬜ Implement LLM-based sentiment extraction
  - ⬜ Add sentiment trend tracking

### 2.8 RiskManagerAgent
- ⬜ Create RiskManagerAgent class (core/mcp_agents/risk_agent.py)
  - ⬜ Implement share pledge ratio checker
  - ⬜ Add restricted share unlock monitor
  - ⬜ Implement goodwill impairment detector
  - ⬜ Create risk scoring system
  - ⬜ Add portfolio correlation analysis
  - ⬜ Implement position size validator

### 2.9 ExecutionAgent
- ⬜ Create ExecutionAgent class (core/mcp_agents/execution_agent.py)
  - ⬜ Implement signal aggregation logic
  - ⬜ Add signal strength calculation
  - ⬜ Create order generation logic
  - ⬜ Implement order routing
  - ⬜ Add execution monitoring

### 2.10 Technical Indicators Library
- ⬜ Create indicators.py (core/utils/indicators.py)
  - ⬜ Implement all TA-Lib wrappers
  - ⬜ Add custom A-share indicators
  - ⬜ Create indicator caching
  - ⬜ Add batch calculation support

---

## Phase 3: Strategy Engine & Backtesting (2-3 months)

### 3.1 Base Strategy Framework
- ⬜ Create BaseStrategy class (core/strategy/base_strategy.py)
  - ⬜ Define strategy interface
  - ⬜ Implement signal generation workflow
  - ⬜ Add portfolio management
  - ⬜ Create performance tracking

### 3.2 Swing Trading Strategy
- ⬜ Create SwingTradingStrategy class (core/strategy/swing_trading.py)
  - ⬜ Implement entry signal logic (RSI, MACD, sentiment)
  - ⬜ Add exit signal logic (take-profit, stop-loss)
  - ⬜ Implement position sizing (volatility-adjusted)
  - ⬜ Add holding period constraints (7 days to 2 weeks)
  - ⬜ Create multi-agent signal integration

### 3.3 Trend Following Strategy
- ⬜ Create TrendFollowingStrategy class (core/strategy/trend_following.py)
  - ⬜ Implement trend detection (MA crossover, ADX)
  - ⬜ Add momentum indicators
  - ⬜ Create trend strength scoring
  - ⬜ Implement trailing stop-loss
  - ⬜ Add trend reversal detection

### 3.4 Backtesting Engine
- ⬜ Create BacktestEngine class
  - ⬜ Implement historical data loader
  - ⬜ Add day-by-day simulation
  - ⬜ Create order execution simulator
  - ⬜ Implement slippage and commission
  - ⬜ Add portfolio tracking
  - ⬜ Create performance calculator

### 3.5 Performance Metrics
- ⬜ Create PerformanceEvaluator class
  - ⬜ Implement return calculations (total, annual)
  - ⬜ Add risk metrics (volatility, Sharpe, Sortino)
  - ⬜ Implement drawdown calculations
  - ⬜ Add win rate and profit/loss ratio
  - ⬜ Create benchmark comparison

### 3.6 Backtesting Script
- ⬜ Create backtest.py script (scripts/backtest.py)
  - ⬜ Add CLI argument parsing
  - ⬜ Implement strategy selection
  - ⬜ Add date range configuration
  - ⬜ Create results export (JSON, CSV)
  - ⬜ Add visualization generation

---

## Phase 4: Trading Execution & Risk Management (3-4 months)

### 4.1 Order Management
- ⬜ Create OrderManager class (core/execution/order_manager.py)
  - ⬜ Implement order creation and validation
  - ⬜ Add order status tracking
  - ⬜ Create order queue management
  - ⬜ Implement order execution workflow
  - ⬜ Add order cancellation logic

### 4.2 Risk Control System
- ⬜ Create RiskControl class (core/execution/risk_control.py)
  - ⬜ Implement position limit checks (10% max)
  - ⬜ Add sector exposure checks (30% max)
  - ⬜ Create stop-loss monitoring (8% default)
  - ⬜ Implement take-profit monitoring (15% default)
  - ⬜ Add A-share special risk checks
  - ⬜ Create correlation limit checks

### 4.3 Broker Interface
- ⬜ Create BrokerInterface class (core/execution/broker_interface.py)
  - ⬜ Implement VNpy integration
  - ⬜ Add CTP gateway connection
  - ⬜ Create order submission
  - ⬜ Implement order status polling
  - ⬜ Add account balance queries
  - ⬜ Create position queries

### 4.4 Trading Mode Support
- ⬜ Implement simulation mode (paper trading)
- ⬜ Implement live trading mode
- ⬜ Add mode switching configuration
- ⬜ Create safety checks for live mode

### 4.5 Compliance Monitoring
- ⬜ Create ComplianceManager class
  - ⬜ Implement order frequency tracking (300/sec, 20,000/day)
  - ⬜ Add automatic throttling
  - ⬜ Create compliance reporting
  - ⬜ Implement circuit breakers

---

## Phase 5: API & Web Interface (3-4 months)

### 5.1 FastAPI Application Setup
- ⬜ Create FastAPI app (api/main.py)
  - ⬜ Add CORS middleware
  - ⬜ Implement logging middleware
  - ⬜ Add error handling middleware
  - ⬜ Create health check endpoint

### 5.2 Authentication & Authorization
- ⬜ Implement JWT authentication (api/middleware/auth.py)
- ⬜ Create user management
- ⬜ Add role-based access control
- ⬜ Implement API key authentication

### 5.3 Strategy API Routes
- ⬜ Create strategy routes (api/routes/strategy.py)
  - ⬜ GET /api/v1/strategies - List all strategies
  - ⬜ GET /api/v1/strategies/{id} - Get strategy details
  - ⬜ POST /api/v1/strategies/backtest - Run backtest
  - ⬜ GET /api/v1/strategies/{id}/performance - Get performance metrics

### 5.4 Market Data API Routes
- ⬜ Create market routes (api/routes/market.py)
  - ⬜ GET /api/v1/market/data/{symbol} - Get market data
  - ⬜ GET /api/v1/market/search - Search stocks
  - ⬜ GET /api/v1/market/indicators/{symbol} - Get indicators
  - ⬜ GET /api/v1/market/overview - Market overview

### 5.5 Portfolio API Routes
- ⬜ Create portfolio routes (api/routes/portfolio.py)
  - ⬜ GET /api/v1/portfolio/summary - Portfolio summary
  - ⬜ GET /api/v1/portfolio/positions - Current positions
  - ⬜ GET /api/v1/portfolio/performance - Performance metrics
  - ⬜ GET /api/v1/portfolio/history - Historical snapshots

### 5.6 Order API Routes
- ⬜ Create order routes (api/routes/orders.py)
  - ⬜ POST /api/v1/orders/create - Create order
  - ⬜ GET /api/v1/orders - List orders
  - ⬜ GET /api/v1/orders/{id} - Get order details
  - ⬜ DELETE /api/v1/orders/{id} - Cancel order
  - ⬜ GET /api/v1/orders/history - Order history

### 5.7 Agent API Routes
- ⬜ Create agent routes (api/routes/agents.py)
  - ⬜ GET /api/v1/agents/status - All agents status
  - ⬜ GET /api/v1/agents/{name}/analysis - Agent analysis
  - ⬜ POST /api/v1/agents/{name}/trigger - Trigger analysis
  - ⬜ GET /api/v1/agents/performance - Agent performance

### 5.8 Signal API Routes
- ⬜ Create signal endpoints
  - ⬜ GET /api/v1/signals/current - Current trading signals
  - ⬜ GET /api/v1/signals/history - Signal history
  - ⬜ GET /api/v1/signals/{id} - Signal details

### 5.9 WebSocket Implementation
- ⬜ Create WebSocket endpoints
  - ⬜ /ws/market - Market data stream
  - ⬜ /ws/orders - Order status stream
  - ⬜ /ws/portfolio - Portfolio updates stream
  - ⬜ /ws/agents - Agent analysis stream
- ⬜ Implement connection management
- ⬜ Add heartbeat mechanism
- ⬜ Create message queue for offline clients

### 5.10 API Documentation
- ⬜ Generate OpenAPI/Swagger documentation
- ⬜ Add API examples and usage guides
- ⬜ Create Postman collection

---

## Phase 6: Testing & Quality Assurance (Ongoing)

### 6.1 Unit Tests
- ⬜ Create test fixtures (tests/conftest.py)
- ⬜ Test agent implementations (tests/unit/test_agents.py)
- ⬜ Test strategy logic (tests/unit/test_strategies.py)
- ⬜ Test indicators (tests/unit/test_indicators.py)
- ⬜ Test risk control (tests/unit/test_risk_control.py)
- ⬜ Test data validation (tests/unit/test_validation.py)

### 6.2 Integration Tests
- ⬜ Test agent orchestration (tests/integration/test_orchestrator.py)
- ⬜ Test API endpoints (tests/integration/test_api.py)
- ⬜ Test database operations (tests/integration/test_database.py)
- ⬜ Test WebSocket connections (tests/integration/test_websocket.py)

### 6.3 Backtesting Validation
- ⬜ Test swing trading strategy with historical data
- ⬜ Test trend following strategy with historical data
- ⬜ Validate performance metrics accuracy
- ⬜ Compare with benchmark performance

### 6.4 Code Quality
- ⬜ Set up pytest for testing
- ⬜ Configure coverage reporting (aim for >80%)
- ⬜ Set up linting (ruff, black)
- ⬜ Add type checking (mypy)
- ⬜ Create pre-commit hooks

---

## Phase 7: Deployment & Operations (4-6 months)

### 7.1 Docker Setup
- ⬜ Create Dockerfile for application
- ⬜ Create docker-compose.yml for all services
  - ⬜ FastAPI application
  - ⬜ PostgreSQL + TimescaleDB
  - ⬜ Redis
  - ⬜ Redis Streams/Kafka
- ⬜ Create development docker-compose
- ⬜ Create production docker-compose

### 7.2 Monitoring & Logging
- ⬜ Implement structured logging
- ⬜ Add performance monitoring
- ⬜ Create alert system for errors
- ⬜ Set up metrics collection (Prometheus)
- ⬜ Create dashboards (Grafana)

### 7.3 Deployment Scripts
- ⬜ Create deployment script
- ⬜ Add database migration workflow
- ⬜ Create backup and restore scripts
- ⬜ Add health check scripts

### 7.4 Documentation
- ⬜ Create deployment guide
- ⬜ Write API usage documentation
- ⬜ Create troubleshooting guide
- ⬜ Document configuration options

---

## Current Priority

**Start with Phase 1: Environment Setup & Infrastructure**

1. Project initialization
2. Database setup
3. Redis setup
4. Configuration management
5. Data source integration

Once Phase 1 is complete, move to Phase 2 for MCP agent implementation.

---

## Notes

- Always commit working code before moving to next task
- Write tests alongside implementation
- Document complex logic and decisions
- Follow the implementation patterns in CLAUDE.md
- Never use mock data - integrate real data sources
- Ensure all A-share market specifics are properly handled
