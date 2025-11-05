# Frontend-Backend API Integration Summary

## ✅ Completed Tasks

### 1. API Endpoints Configuration
**File**: `frontend/src/config/api.config.ts`

**Updated endpoints to match backend API.md:**
- **Strategies**:
  - List: `GET /api/v1/strategies/`
  - Create: `POST /api/v1/strategies/`
  - Detail: `GET /api/v1/strategies/{strategyName}`
  - Update: `PATCH /api/v1/strategies/{strategyName}`
  - Delete: `DELETE /api/v1/strategies/{strategyName}`
  - Backtest: `POST /api/v1/strategies/{strategyName}/backtest`
  - Stats: `GET /api/v1/strategies/{strategyName}/stats`

- **Market Data**:
  - Quote: `GET /api/v1/market/quote/{symbol}`
  - Bars: `GET /api/v1/market/bars/{symbol}`
  - Indicators: `GET /api/v1/market/indicators/{symbol}`
  - Search: `GET /api/v1/market/search`
  - Info: `GET /api/v1/market/info/{symbol}`

- **Portfolio**:
  - Summary: `GET /api/v1/portfolio/summary`
  - Positions: `GET /api/v1/portfolio/positions`
  - Position: `GET /api/v1/portfolio/positions/{symbol}`
  - History: `GET /api/v1/portfolio/history`

- **Orders**:
  - Create: `POST /api/v1/orders/`
  - List: `GET /api/v1/orders/`
  - Detail: `GET /api/v1/orders/{orderId}`
  - Cancel: `DELETE /api/v1/orders/{orderId}`
  - Recent: `GET /api/v1/orders/history/recent`

- **Agents**:
  - Status: `GET /api/v1/agents/status`
  - Analyze: `POST /api/v1/agents/analyze/{agentName}`
  - Analyze All: `POST /api/v1/agents/analyze-all/{symbol}`
  - Performance: `GET /api/v1/agents/performance`

- **Signals**:
  - Current: `GET /api/v1/signals/current`
  - History: `GET /api/v1/signals/history`
  - Detail: `GET /api/v1/signals/{signalId}`
  - Stats: `GET /api/v1/signals/stats/summary`

### 2. Type Definitions
**Updated files to match backend response formats:**

**`frontend/src/types/strategy.ts`:**
- `Strategy`: Uses `strategy_type`, `enabled`, snake_case fields
- `StrategyStats`: Matches backend stats response
- `BacktestConfig` & `BacktestResult`: Aligned with backend
- `CreateStrategyRequest` & `UpdateStrategyRequest`: New request types

**`frontend/src/types/market.ts`:**
- `Quote`: Real-time market quote
- `BarData` & `BarsResponse`: Historical OHLCV data
- `TechnicalIndicators`: All backend indicators (RSI, MACD, MA, KDJ, BB, ATR, ADX)
- `StockInfo`: Stock basic information
- `StockSearchResult`: Search response format

**`frontend/src/types/order.ts`:**
- `Order`: Using `order_type`, `filled_quantity`, `avg_filled_price`
- `OrderStatus`: Added `partial_filled` status
- `TradingSignal`: Using `direction`, `agent_name`, `entry_price`, `stop_loss_price`, `is_executed`
- `RecentOrdersResponse` & `SignalStatsResponse`: New response types

**`frontend/src/types/portfolio.ts`:**
- `Position`: Using snake_case fields
- `PortfolioSummary`: Matches backend summary response
- `PortfolioSnapshot` & `PortfolioHistoryResponse`: History format

**`frontend/src/types/agent.ts`:**
- `AgentConfig`: Agent configuration from backend
- `AgentAnalysisResult`: Single agent analysis result
- `AnalyzeAllResponse`: Multi-agent analysis response
- `AgentPerformanceResponse`: Performance metrics

### 3. API Service Functions
**Updated all API service files:**

**`frontend/src/api/strategies.ts`:**
- `getStrategies()`: List all strategies
- `createStrategy(data)`: Create new strategy
- `getStrategyDetail(strategyName)`: Get strategy details
- `updateStrategy(strategyName, data)`: Update strategy
- `deleteStrategy(strategyName)`: Delete strategy
- `runBacktest(strategyName, config)`: Run backtest
- `getStrategyStats(strategyName)`: Get strategy statistics

**`frontend/src/api/market.ts`:**
- `getQuote(symbol)`: Get real-time quote
- `getBars(symbol, params)`: Get historical bars
- `getTechnicalIndicators(symbol, days)`: Get indicators
- `searchStocks(query, limit)`: Search stocks
- `getStockInfo(symbol)`: Get stock info

**`frontend/src/api/orders.ts`:**
- `createOrder(orderData)`: Create order
- `getOrders(params)`: List orders
- `getOrderDetail(orderId)`: Get order details
- `cancelOrder(orderId)`: Cancel order
- `getRecentOrders(days)`: Get recent orders
- `getCurrentSignals(limit)`: Get current signals
- `getSignalHistory(params)`: Get signal history
- `getSignalDetail(signalId)`: Get signal details
- `getSignalStats(days)`: Get signal statistics

**`frontend/src/api/portfolio.ts`:**
- `getPortfolioSummary()`: Get portfolio summary
- `getCurrentPositions()`: Get current positions
- `getPosition(symbol)`: Get specific position
- `getPortfolioHistory(days)`: Get portfolio history

**`frontend/src/api/agents.ts`:**
- `getAgentsStatus()`: Get all agents status
- `analyzeWithAgent(agentName, symbol)`: Analyze with specific agent
- `analyzeWithAllAgents(symbol)`: Analyze with all agents
- `getAgentsPerformance()`: Get agents performance

### 4. WebSocket Configuration
**File**: `frontend/src/api/websocket.ts`

**Updated message types to match backend:**
- `MarketConnectionMessage`: Connection confirmation
- `MarketSubscriptionMessage`: Subscription confirmation
- `MarketDataMessage`: Real-time market data
- `OrderUpdateMessage`: Order status updates
- `PortfolioUpdateMessage`: Portfolio updates
- `AgentAnalysisMessage`: Agent analysis results

**WebSocket client features:**
- Separate clients for each channel (market, orders, portfolio, agents)
- Auto-reconnection with exponential backoff
- Heartbeat mechanism (ping/pong)
- Type-safe message handling
- Subscribe/unsubscribe for market symbols

## 🧪 Testing Guide

### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Frontend dev server running on `http://localhost:5188`

### Manual Testing Steps

#### 1. Test Health Check
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{
  "status": "healthy",
  "service": "HiddenGem Trading API",
  "version": "0.1.0",
  "environment": "development"
}
```

#### 2. Test Strategy API
```bash
# Create strategy
curl -X POST http://localhost:8000/api/v1/strategies/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_strategy",
    "strategy_type": "swing_trading",
    "enabled": true,
    "symbols": ["000001"],
    "max_positions": 5,
    "position_size": 0.2,
    "stop_loss_pct": 0.08,
    "take_profit_pct": 0.15
  }'

# List strategies
curl http://localhost:8000/api/v1/strategies/

# Get strategy detail
curl http://localhost:8000/api/v1/strategies/test_strategy
```

#### 3. Test Market Data API
```bash
# Get quote
curl http://localhost:8000/api/v1/market/quote/000001

# Get bars
curl "http://localhost:8000/api/v1/market/bars/000001?days=60"

# Get indicators
curl http://localhost:8000/api/v1/market/indicators/000001

# Search stocks
curl "http://localhost:8000/api/v1/market/search?query=平安"
```

#### 4. Test Portfolio API
```bash
# Get portfolio summary
curl http://localhost:8000/api/v1/portfolio/summary

# Get positions
curl http://localhost:8000/api/v1/portfolio/positions

# Get portfolio history
curl "http://localhost:8000/api/v1/portfolio/history?days=30"
```

#### 5. Test Orders API
```bash
# Create order
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001",
    "side": "buy",
    "order_type": "limit",
    "quantity": 1000,
    "price": 12.50,
    "strategy_name": "test_strategy"
  }'

# List orders
curl http://localhost:8000/api/v1/orders/

# Get recent orders
curl "http://localhost:8000/api/v1/orders/history/recent?days=7"
```

#### 6. Test Agents API
```bash
# Get agents status
curl http://localhost:8000/api/v1/agents/status

# Analyze with specific agent
curl -X POST http://localhost:8000/api/v1/agents/analyze/technical \
  -H "Content-Type: application/json" \
  -d '{"symbol": "000001"}'

# Analyze with all agents
curl -X POST http://localhost:8000/api/v1/agents/analyze-all/000001 \
  -H "Content-Type: application/json"
```

#### 7. Test Signals API
```bash
# Get current signals
curl http://localhost:8000/api/v1/signals/current

# Get signal history
curl "http://localhost:8000/api/v1/signals/history?days=7"

# Get signal stats
curl "http://localhost:8000/api/v1/signals/stats/summary?days=30"
```

### Frontend Integration Testing

#### 1. Test in Browser Console
Open browser DevTools console at `http://localhost:5188` and run:

```javascript
// Test strategy API
import { getStrategies } from '@/api/strategies';
const strategies = await getStrategies();
console.log('Strategies:', strategies);

// Test market data
import { getQuote } from '@/api/market';
const quote = await getQuote('000001');
console.log('Quote:', quote);

// Test portfolio
import { getPortfolioSummary } from '@/api/portfolio';
const portfolio = await getPortfolioSummary();
console.log('Portfolio:', portfolio);

// Test agents
import { getAgentsStatus } from '@/api/agents';
const agents = await getAgentsStatus();
console.log('Agents:', agents);
```

#### 2. Test WebSocket Connections
```javascript
import { marketWebSocket } from '@/api/websocket';

// Connect to market data WebSocket
marketWebSocket.connect();

// Subscribe to market data
marketWebSocket.subscribe((message) => {
  console.log('Market data:', message);
});

// Subscribe to symbols
marketWebSocket.subscribeToSymbols(['000001', '600519']);
```

### Automated Testing (TODO)
Create integration tests using:
- **Vitest**: For unit tests
- **React Testing Library**: For component tests
- **MSW (Mock Service Worker)**: For API mocking during tests

Example test file: `frontend/src/api/__tests__/strategies.test.ts`

## 📝 Notes

### Breaking Changes from Initial Implementation
1. **IDs vs Names**: Strategies use `name` as identifier, not `id`
2. **Order IDs**: Changed from `string` to `number`
3. **Signal IDs**: Changed from `string` to `number`
4. **Field Naming**: Backend uses `snake_case`, TypeScript types now match
5. **Status Values**: Order status uses `partial_filled` instead of `partial`

### Environment Variables
Ensure `.env` file has correct backend URL:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### CORS Configuration
Backend must enable CORS for frontend origin:
```python
# Backend CORS settings
allow_origins=["http://localhost:5188"]
```

### Next Steps
1. Start backend server: `cd backend && uvicorn api.main:app --reload`
2. Start frontend server: `cd frontend && npm run dev`
3. Test each API endpoint manually
4. Verify WebSocket connections
5. Test frontend components with real data
6. Write automated integration tests

## 🐛 Common Issues

### 1. CORS Errors
**Problem**: Browser blocks requests due to CORS policy
**Solution**: Ensure backend CORS middleware allows frontend origin

### 2. WebSocket Connection Failed
**Problem**: WebSocket fails to connect
**Solution**:
- Check backend WebSocket server is running
- Verify WebSocket URL is correct (`ws://` not `http://`)
- Check firewall/proxy settings

### 3. Type Mismatches
**Problem**: TypeScript errors about field types
**Solution**:
- Ensure backend responses match type definitions
- Check snake_case vs camelCase field names
- Verify number vs string for IDs

### 4. 404 Not Found
**Problem**: API endpoints return 404
**Solution**:
- Verify endpoint URL matches backend exactly
- Check API prefix `/api/v1` is correct
- Ensure backend routes are registered

## 📚 Documentation References
- Backend API: `backend/API.md`
- Frontend CLAUDE guide: `frontend/CLAUDE.md`
- Backend CLAUDE guide: `backend/CLAUDE.md`
- Type definitions: `frontend/src/types/*.ts`
- API services: `frontend/src/api/*.ts`
