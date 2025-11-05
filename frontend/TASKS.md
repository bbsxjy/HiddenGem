# Frontend Tasks

This file tracks implementation tasks for the HiddenGem frontend trading dashboard.

## Task Status Legend
- ⬜ Not Started
- 🟡 In Progress
- ✅ Completed
- ❌ Blocked

---

## Phase 1: Project Setup & Configuration (Week 1-2)

### 1.1 Project Initialization
- ⬜ Initialize Vite + React + TypeScript project
- ⬜ Configure TypeScript (tsconfig.json)
- ⬜ Set up Tailwind CSS
- ⬜ Configure Tailwind with all color definitions in config
- ⬜ Set up ESLint and Prettier
- ⬜ Create .env.example with required variables
- ⬜ Create .gitignore for Node project
- ⬜ Initialize git repository
- ⬜ Create README.md with setup instructions

### 1.2 Project Structure Setup
- ⬜ Create folder structure (api, components, pages, hooks, store, types, utils, config)
- ⬜ Set up path aliases in tsconfig.json (@/, @components/, etc.)
- ⬜ Create index.css with Tailwind directives
- ⬜ Set up main.tsx entry point

### 1.3 Dependencies Installation
- ⬜ Install React Router
- ⬜ Install TanStack Query (React Query)
- ⬜ Install Zustand
- ⬜ Install HeadlessUI
- ⬜ Install Lucide React
- ⬜ Install Recharts
- ⬜ Install TradingView Lightweight Charts
- ⬜ Install Axios
- ⬜ Install date-fns
- ⬜ Install zod
- ⬜ Install clsx
- ⬜ Install dev dependencies (types, testing libraries)

### 1.4 Configuration Files
- ⬜ Create API configuration (config/api.config.ts)
- ⬜ Create chart configuration (config/chart.config.ts)
- ⬜ Set up Vite configuration for development and production

---

## Phase 2: Core Infrastructure (Week 2-3)

### 2.1 API Client Setup
- ⬜ Create Axios instance (api/client.ts)
- ⬜ Add request interceptors (auth headers)
- ⬜ Add response interceptors (error handling)
- ⬜ Implement token management
- ⬜ Add retry logic for failed requests

### 2.2 API Service Modules
- ⬜ Create agents API service (api/agents.ts)
  - ⬜ getAgentsStatus()
  - ⬜ getAgentAnalysis(agentName)
  - ⬜ triggerAgentAnalysis(agentName)
- ⬜ Create market API service (api/market.ts)
  - ⬜ getMarketData(symbol, period)
  - ⬜ searchStocks(query)
  - ⬜ getStockDetail(symbol)
  - ⬜ getMarketOverview()
- ⬜ Create portfolio API service (api/portfolio.ts)
  - ⬜ getPortfolioSummary()
  - ⬜ getCurrentPositions()
  - ⬜ getPortfolioPerformance()
  - ⬜ getPortfolioHistory()
- ⬜ Create orders API service (api/orders.ts)
  - ⬜ createOrder(orderData)
  - ⬜ getOrders(filters)
  - ⬜ getOrderDetail(orderId)
  - ⬜ cancelOrder(orderId)
  - ⬜ getOrderHistory()
- ⬜ Create strategies API service (api/strategies.ts)
  - ⬜ getStrategies()
  - ⬜ getStrategyDetail(strategyId)
  - ⬜ runBacktest(config)
  - ⬜ getBacktestResults(backtestId)

### 2.3 WebSocket Client
- ⬜ Create WebSocket client (api/websocket.ts)
- ⬜ Implement connection management
- ⬜ Add reconnection logic with exponential backoff
- ⬜ Implement heartbeat mechanism
- ⬜ Create message type definitions
- ⬜ Add message queue for offline handling
- ⬜ Implement subscribe/unsubscribe for channels

### 2.4 Type Definitions
- ⬜ Define API response types (types/api.ts)
- ⬜ Define market data types (types/market.ts)
- ⬜ Define portfolio types (types/portfolio.ts)
- ⬜ Define agent types (types/agent.ts)
- ⬜ Define order types (types/order.ts)
- ⬜ Define strategy types (types/strategy.ts)

### 2.5 State Management
- ⬜ Create auth store (store/useAuthStore.ts)
- ⬜ Create UI store (store/useUIStore.ts)
- ⬜ Create real-time store (store/useRealtimeStore.ts)

### 2.6 React Query Setup
- ⬜ Configure QueryClient
- ⬜ Set up default query options
- ⬜ Add QueryClientProvider to App

---

## Phase 3: Common Components (Week 3-4)

### 3.1 Basic UI Components
- ⬜ Create Button component (components/common/Button.tsx)
- ⬜ Create Card component (components/common/Card.tsx)
- ⬜ Create Input component (components/common/Input.tsx)
- ⬜ Create Select component (components/common/Select.tsx)
- ⬜ Create Table component (components/common/Table.tsx)
- ⬜ Create Modal component (components/common/Modal.tsx)
- ⬜ Create Loading component (components/common/Loading.tsx)
- ⬜ Create ErrorBoundary component (components/common/ErrorBoundary.tsx)

### 3.2 Layout Components
- ⬜ Create Header component (components/layout/Header.tsx)
- ⬜ Create Sidebar component (components/layout/Sidebar.tsx)
- ⬜ Create Layout component (components/layout/Layout.tsx)
- ⬜ Create NavigationMenu component (components/layout/NavigationMenu.tsx)

### 3.3 Utility Functions
- ⬜ Create formatting utilities (utils/format.ts)
  - ⬜ formatCurrency()
  - ⬜ formatPercent()
  - ⬜ formatNumber()
  - ⬜ formatDate()
  - ⬜ formatLargeNumber() (10000 = 1万)
- ⬜ Create calculation utilities (utils/calculation.ts)
  - ⬜ calculateProfitLoss()
  - ⬜ calculatePercentageChange()
  - ⬜ calculateSharpeRatio()
  - ⬜ calculateDrawdown()
- ⬜ Create validation utilities (utils/validation.ts)
- ⬜ Create constants (utils/constants.ts)

---

## Phase 4: Dashboard Page (Week 4-5)

### 4.1 Dashboard Components
- ⬜ Create PortfolioSummary component (components/dashboard/PortfolioSummary.tsx)
  - ⬜ Display total portfolio value
  - ⬜ Show daily P&L
  - ⬜ Display position count
  - ⬜ Show cash balance
- ⬜ Create PerformanceChart component (components/dashboard/PerformanceChart.tsx)
  - ⬜ Line chart for portfolio value over time
  - ⬜ Comparison with benchmark
  - ⬜ Time range selector (1D, 1W, 1M, 3M, 1Y, All)
- ⬜ Create PositionsList component (components/dashboard/PositionsList.tsx)
  - ⬜ Table with current positions
  - ⬜ Real-time P&L updates
  - ⬜ Color coding for profit/loss
  - ⬜ Board type indicators
- ⬜ Create MarketOverview component (components/dashboard/MarketOverview.tsx)
  - ⬜ Display northbound flow
  - ⬜ Show margin balance
  - ⬜ Display market sentiment
  - ⬜ Show major indices
- ⬜ Create RecentSignals component (components/dashboard/RecentSignals.tsx)
  - ⬜ List recent trading signals
  - ⬜ Signal strength indicators
  - ⬜ Agent source labels

### 4.2 Dashboard Page
- ⬜ Create Dashboard page (pages/Dashboard.tsx)
- ⬜ Integrate all dashboard components
- ⬜ Add real-time updates via WebSocket
- ⬜ Implement auto-refresh logic

### 4.3 Custom Hooks for Dashboard
- ⬜ Create usePortfolio hook (hooks/usePortfolio.ts)
- ⬜ Create useMarketData hook (hooks/useMarketData.ts)
- ⬜ Create useWebSocket hook (hooks/useWebSocket.ts)

---

## Phase 5: Market Analysis Page (Week 5-6)

### 5.1 Market Components
- ⬜ Create StockChart component (components/market/StockChart.tsx)
  - ⬜ Integrate TradingView Lightweight Charts
  - ⬜ Display candlestick data
  - ⬜ Add volume bars
  - ⬜ Add technical indicator overlays (MA, RSI, MACD)
  - ⬜ Implement time range selection
- ⬜ Create MarketDepth component (components/market/MarketDepth.tsx)
- ⬜ Create StockList component (components/market/StockList.tsx)
  - ⬜ Searchable and filterable stock list
  - ⬜ Sort by price, volume, change
  - ⬜ Filter by board type
- ⬜ Create StockDetail component (components/market/StockDetail.tsx)
  - ⬜ Basic stock info
  - ⬜ Real-time price
  - ⬜ Key statistics
  - ⬜ Board type badge
- ⬜ Create MarketIndicators component (components/market/MarketIndicators.tsx)
  - ⬜ Technical indicators display
  - ⬜ Fundamental metrics
  - ⬜ Risk indicators

### 5.2 Market Page
- ⬜ Create Market page (pages/Market.tsx)
- ⬜ Integrate market components
- ⬜ Add stock search functionality
- ⬜ Implement real-time price updates

---

## Phase 6: Agents Monitoring Page (Week 6-7)

### 6.1 Agent Components
- ⬜ Create AgentStatus component (components/agents/AgentStatus.tsx)
  - ⬜ Status cards for all 7 agents
  - ⬜ Active/inactive indicators
  - ⬜ Last update timestamp
  - ⬜ Health metrics
- ⬜ Create AgentAnalysis component (components/agents/AgentAnalysis.tsx)
  - ⬜ Display analysis results
  - ⬜ Confidence scores
  - ⬜ Recommendations
- ⬜ Create PolicyAnalysis component (components/agents/PolicyAnalysis.tsx)
- ⬜ Create TechnicalAnalysis component (components/agents/TechnicalAnalysis.tsx)
- ⬜ Create FundamentalAnalysis component (components/agents/FundamentalAnalysis.tsx)
- ⬜ Create RiskAssessment component (components/agents/RiskAssessment.tsx)

### 6.2 Agents Page
- ⬜ Create Agents page (pages/Agents.tsx)
- ⬜ Integrate agent components
- ⬜ Add real-time agent updates
- ⬜ Implement manual trigger functionality

### 6.3 Custom Hooks for Agents
- ⬜ Create useAgents hook (hooks/useAgents.ts)

---

## Phase 7: Trading Interface Page (Week 7-8)

### 7.1 Trading Components
- ⬜ Create OrderForm component (components/trading/OrderForm.tsx)
  - ⬜ Stock symbol input with autocomplete
  - ⬜ Order type selection (market/limit)
  - ⬜ Quantity input
  - ⬜ Price input (for limit orders)
  - ⬜ Risk warnings for A-share specific risks
  - ⬜ Board type validation
  - ⬜ Position size validation
  - ⬜ Submit order functionality
- ⬜ Create OrderList component (components/trading/OrderList.tsx)
  - ⬜ Active orders table
  - ⬜ Order status indicators
  - ⬜ Cancel order action
- ⬜ Create OrderHistory component (components/trading/OrderHistory.tsx)
  - ⬜ Historical orders table
  - ⬜ Filtering and sorting
  - ⬜ Export functionality
- ⬜ Create SignalCard component (components/trading/SignalCard.tsx)
  - ⬜ Display trading signals
  - ⬜ Signal strength visualization
  - ⬜ Agent source display
  - ⬜ Execute from signal action

### 7.2 Trading Page
- ⬜ Create Trading page (pages/Trading.tsx)
- ⬜ Integrate trading components
- ⬜ Add real-time order updates
- ⬜ Implement order notifications

### 7.3 Custom Hooks for Trading
- ⬜ Create useOrders hook (hooks/useOrders.ts)

---

## Phase 8: Portfolio Management Page (Week 8-9)

### 8.1 Portfolio Components (Detailed)
- ⬜ Create detailed PositionsList with more metrics
- ⬜ Create SectorExposure component
  - ⬜ Pie chart for sector allocation
  - ⬜ Sector limit indicators
- ⬜ Create RiskMetrics component
  - ⬜ Portfolio volatility
  - ⬜ Sharpe ratio
  - ⬜ Max drawdown
  - ⬜ VaR (Value at Risk)
- ⬜ Create PerformanceHistory component
  - ⬜ Historical performance chart
  - ⬜ Benchmark comparison
  - ⬜ Time range selector

### 8.2 Portfolio Page
- ⬜ Create Portfolio page (pages/Portfolio.tsx)
- ⬜ Integrate portfolio components
- ⬜ Add real-time updates

---

## Phase 9: Strategy Management Page (Week 9-10)

### 9.1 Strategy Components
- ⬜ Create StrategyList component (components/strategy/StrategyList.tsx)
  - ⬜ List available strategies
  - ⬜ Strategy status (active/inactive)
  - ⬜ Quick stats
- ⬜ Create StrategyConfig component (components/strategy/StrategyConfig.tsx)
  - ⬜ Strategy parameter configuration
  - ⬜ Enable/disable strategy
  - ⬜ Save configuration
- ⬜ Create BacktestResults component (components/strategy/BacktestResults.tsx)
  - ⬜ Performance chart
  - ⬜ Trade list
  - ⬜ Metrics display
  - ⬜ Export results
- ⬜ Create PerformanceMetrics component (components/strategy/PerformanceMetrics.tsx)
  - ⬜ Return metrics
  - ⬜ Risk metrics
  - ⬜ Trade statistics

### 9.2 Strategy Page
- ⬜ Create Strategy page (pages/Strategy.tsx)
- ⬜ Integrate strategy components

### 9.3 Backtest Page
- ⬜ Create Backtest page (pages/Backtest.tsx)
  - ⬜ Strategy selector
  - ⬜ Date range selector
  - ⬜ Parameter configuration
  - ⬜ Run backtest button
  - ⬜ Results visualization

### 9.4 Custom Hooks for Strategies
- ⬜ Create useStrategies hook (hooks/useStrategies.ts)

---

## Phase 10: Settings & Additional Pages (Week 10-11)

### 10.1 Settings Page
- ⬜ Create Settings page (pages/Settings.tsx)
  - ⬜ User profile settings
  - ⬜ API configuration
  - ⬜ Notification preferences
  - ⬜ Risk management settings
  - ⬜ Theme settings

### 10.2 Error Pages
- ⬜ Create 404 page
- ⬜ Create error page

---

## Phase 11: Routing & Navigation (Week 11)

### 11.1 Router Setup
- ⬜ Set up React Router in App.tsx
- ⬜ Define routes for all pages
  - ⬜ /dashboard
  - ⬜ /market
  - ⬜ /portfolio
  - ⬜ /trading
  - ⬜ /agents
  - ⬜ /strategy
  - ⬜ /backtest
  - ⬜ /settings
- ⬜ Add route guards for authentication
- ⬜ Implement lazy loading for routes

### 11.2 Navigation
- ⬜ Implement navigation menu with active states
- ⬜ Add breadcrumbs
- ⬜ Create responsive mobile menu

---

## Phase 12: Real-time Features (Week 12)

### 12.1 WebSocket Integration
- ⬜ Connect to market data WebSocket
- ⬜ Connect to order status WebSocket
- ⬜ Connect to portfolio updates WebSocket
- ⬜ Connect to agent analysis WebSocket
- ⬜ Implement automatic reconnection
- ⬜ Handle connection state in UI

### 12.2 Real-time Updates
- ⬜ Update market prices in real-time
- ⬜ Update order statuses in real-time
- ⬜ Update portfolio values in real-time
- ⬜ Update agent analysis in real-time
- ⬜ Add visual indicators for updates (flash on change)

### 12.3 Notifications
- ⬜ Implement toast notifications
- ⬜ Add order execution notifications
- ⬜ Add signal notifications
- ⬜ Add risk alert notifications

---

## Phase 13: Polish & Optimization (Week 13-14)

### 13.1 Responsive Design
- ⬜ Test on mobile devices
- ⬜ Test on tablets
- ⬜ Test on desktop
- ⬜ Fix responsive issues
- ⬜ Optimize for different screen sizes

### 13.2 Performance Optimization
- ⬜ Implement code splitting
- ⬜ Lazy load heavy components
- ⬜ Optimize re-renders (React.memo, useMemo, useCallback)
- ⬜ Implement virtualization for large lists
- ⬜ Optimize bundle size
- ⬜ Add loading skeletons

### 13.3 Accessibility
- ⬜ Add ARIA labels
- ⬜ Test keyboard navigation
- ⬜ Test with screen reader
- ⬜ Ensure color contrast compliance
- ⬜ Add focus indicators

### 13.4 Error Handling
- ⬜ Implement comprehensive error boundaries
- ⬜ Add user-friendly error messages
- ⬜ Implement retry mechanisms
- ⬜ Add fallback UI

### 13.5 Testing
- ⬜ Set up Vitest for unit tests
- ⬜ Set up React Testing Library
- ⬜ Write component tests
- ⬜ Write hook tests
- ⬜ Set up Playwright for E2E tests
- ⬜ Write critical user flow tests

---

## Phase 14: Documentation & Deployment Prep (Week 14)

### 14.1 Documentation
- ⬜ Document component props
- ⬜ Create developer guide
- ⬜ Document API integration
- ⬜ Create user guide

### 14.2 Build & Deploy
- ⬜ Optimize production build
- ⬜ Test production build locally
- ⬜ Create deployment scripts
- ⬜ Set up environment variables for production

---

## Current Priority

**Start with Phase 1: Project Setup & Configuration**

1. Initialize Vite + React + TypeScript
2. Set up Tailwind CSS with color config
3. Install all dependencies
4. Create project structure
5. Set up configuration files

Once Phase 1 is complete, move to Phase 2 for core infrastructure.

---

## Notes

- Always commit working code before moving to next task
- Never use mock data - connect to real backend APIs
- Follow TypeScript best practices
- Ensure all colors are defined in Tailwind config
- Test responsive design as you build
- Implement loading and error states for all components
- Use React Query for all data fetching
- Implement proper error handling
- Follow accessibility best practices
