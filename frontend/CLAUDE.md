# Frontend CLAUDE.md

This file provides guidance for implementing the HiddenGem frontend trading dashboard.

## Overall Rules

1. **No Mock Data**: Never use mock data or leave TODO comments. All implementations must connect to real backend APIs.
2. **Follow Specifications**: Strictly follow the rules defined in the root CLAUDE.md and this document.
3. **Git Commits**: Before fixing or adding new content, commit previous work using git.
4. **No Server Startup**: Do not start development servers - let the user handle server startup.
5. **Use Ultrathink**: Apply careful reasoning for complex implementations.

## Technology Stack

**Core:**
- React 18+
- Vite (build tool)
- TypeScript
- React Router for navigation

**UI & Styling:**
- Tailwind CSS (all colors in config file)
- HeadlessUI for accessible components
- Lucide React for icons
- Recharts for data visualization
- TradingView Lightweight Charts for candlestick charts

**State Management:**
- React Query (TanStack Query) for server state
- Zustand for client state
- WebSocket for real-time updates

**Utilities:**
- Axios for HTTP requests
- date-fns for date manipulation
- zod for schema validation
- clsx for conditional classnames

## Project Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                     # API client
│   │   ├── client.ts            # Axios instance
│   │   ├── agents.ts            # Agent APIs
│   │   ├── market.ts            # Market data APIs
│   │   ├── portfolio.ts         # Portfolio APIs
│   │   ├── orders.ts            # Order APIs
│   │   ├── strategies.ts        # Strategy APIs
│   │   └── websocket.ts         # WebSocket client
│   ├── components/              # React components
│   │   ├── common/              # Common reusable components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Loading.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── layout/              # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Layout.tsx
│   │   │   └── NavigationMenu.tsx
│   │   ├── dashboard/           # Dashboard components
│   │   │   ├── PortfolioSummary.tsx
│   │   │   ├── PerformanceChart.tsx
│   │   │   ├── PositionsList.tsx
│   │   │   ├── MarketOverview.tsx
│   │   │   └── RecentSignals.tsx
│   │   ├── market/              # Market components
│   │   │   ├── StockChart.tsx
│   │   │   ├── MarketDepth.tsx
│   │   │   ├── StockList.tsx
│   │   │   ├── StockDetail.tsx
│   │   │   └── MarketIndicators.tsx
│   │   ├── agents/              # Agent components
│   │   │   ├── AgentStatus.tsx
│   │   │   ├── AgentAnalysis.tsx
│   │   │   ├── PolicyAnalysis.tsx
│   │   │   ├── TechnicalAnalysis.tsx
│   │   │   ├── FundamentalAnalysis.tsx
│   │   │   └── RiskAssessment.tsx
│   │   ├── trading/             # Trading components
│   │   │   ├── OrderForm.tsx
│   │   │   ├── OrderList.tsx
│   │   │   ├── OrderHistory.tsx
│   │   │   └── SignalCard.tsx
│   │   └── strategy/            # Strategy components
│   │       ├── StrategyList.tsx
│   │       ├── StrategyConfig.tsx
│   │       ├── BacktestResults.tsx
│   │       └── PerformanceMetrics.tsx
│   ├── pages/                   # Page components
│   │   ├── Dashboard.tsx        # Main dashboard
│   │   ├── Market.tsx           # Market analysis page
│   │   ├── Portfolio.tsx        # Portfolio management
│   │   ├── Trading.tsx          # Trading interface
│   │   ├── Agents.tsx           # Agent monitoring
│   │   ├── Strategy.tsx         # Strategy management
│   │   ├── Backtest.tsx         # Backtesting interface
│   │   └── Settings.tsx         # Settings page
│   ├── hooks/                   # Custom React hooks
│   │   ├── useWebSocket.ts      # WebSocket hook
│   │   ├── useMarketData.ts     # Market data hook
│   │   ├── usePortfolio.ts      # Portfolio data hook
│   │   ├── useAgents.ts         # Agents data hook
│   │   ├── useOrders.ts         # Orders hook
│   │   └── useStrategies.ts     # Strategies hook
│   ├── store/                   # Zustand stores
│   │   ├── useAuthStore.ts      # Authentication state
│   │   ├── useUIStore.ts        # UI state (theme, sidebar, etc.)
│   │   └── useRealtimeStore.ts  # Real-time data state
│   ├── types/                   # TypeScript types
│   │   ├── api.ts               # API response types
│   │   ├── market.ts            # Market data types
│   │   ├── portfolio.ts         # Portfolio types
│   │   ├── agent.ts             # Agent types
│   │   ├── order.ts             # Order types
│   │   └── strategy.ts          # Strategy types
│   ├── utils/                   # Utility functions
│   │   ├── format.ts            # Formatting utilities
│   │   ├── calculation.ts       # Financial calculations
│   │   ├── validation.ts        # Validation functions
│   │   └── constants.ts         # Constants
│   ├── config/                  # Configuration
│   │   ├── api.config.ts        # API configuration
│   │   └── chart.config.ts      # Chart configuration
│   ├── App.tsx                  # Root component
│   ├── main.tsx                 # Entry point
│   └── index.css                # Global styles
├── tailwind.config.js           # Tailwind configuration
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts               # Vite configuration
├── package.json                 # Dependencies
├── .env.example                 # Environment variables example
├── CLAUDE.md                    # This file
└── TASKS.md                     # Task tracking file
```

## Tailwind Configuration

All colors must be defined in `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',  // Main primary
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Trading specific colors
        profit: {
          light: '#22c55e',
          DEFAULT: '#16a34a',
          dark: '#15803d',
        },
        loss: {
          light: '#ef4444',
          DEFAULT: '#dc2626',
          dark: '#b91c1c',
        },
        // A-Share board colors
        board: {
          main: '#3b82f6',      // Main board - blue
          chinext: '#8b5cf6',   // ChiNext - purple
          star: '#f59e0b',      // STAR - orange
        },
        // Agent status colors
        agent: {
          active: '#10b981',    // Green
          inactive: '#6b7280',  // Gray
          error: '#ef4444',     // Red
          warning: '#f59e0b',   // Orange
        },
        // Risk level colors
        risk: {
          low: '#10b981',
          medium: '#f59e0b',
          high: '#ef4444',
          critical: '#dc2626',
        },
        // UI colors
        background: {
          DEFAULT: '#ffffff',
          secondary: '#f9fafb',
          dark: '#111827',
        },
        surface: {
          DEFAULT: '#ffffff',
          hover: '#f3f4f6',
          active: '#e5e7eb',
        },
        text: {
          primary: '#111827',
          secondary: '#6b7280',
          disabled: '#9ca3af',
          inverse: '#ffffff',
        },
        border: {
          DEFAULT: '#e5e7eb',
          focus: '#3b82f6',
          error: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      },
    },
  },
}
```

## Key Features to Implement

### 1. Dashboard
- Portfolio performance overview (daily P&L, total value, positions)
- Real-time market indicators (northbound flow, margin balance, sentiment)
- Recent trading signals from agents
- Quick access to key metrics

### 2. Market Analysis
- Real-time candlestick charts (TradingView Lightweight Charts)
- Technical indicators overlay (RSI, MACD, MA)
- Stock search and filtering by board type
- Market depth visualization
- Volume analysis

### 3. Portfolio Management
- Current positions list with real-time P&L
- Position sizing visualization
- Sector exposure breakdown
- Risk metrics display
- Historical performance charts

### 4. Trading Interface
- Order form with validation
- Real-time order status
- Order history with filtering
- Trading signals from agents
- Risk warnings for A-share specific risks

### 5. Agent Monitoring
- Status dashboard for all 7 agents
- Real-time analysis results from each agent
- Agent performance metrics
- Historical agent predictions vs actual

### 6. Strategy Management
- Strategy list and configuration
- Backtesting interface with date range selection
- Performance metrics visualization
- Strategy comparison tools
- Parameter optimization interface

### 7. Real-time Updates
- WebSocket connection for live data
- Real-time price updates
- Order status notifications
- Agent analysis updates
- Portfolio value updates

## API Integration

**Base URL Configuration:**
```typescript
// src/config/api.config.ts
export const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  wsURL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000',
  timeout: 30000,
}
```

**API Client Setup:**
```typescript
// src/api/client.ts
import axios from 'axios'
import { API_CONFIG } from '@/config/api.config'

export const apiClient = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request/response interceptors for auth, error handling
```

**React Query Setup:**
```typescript
// Use React Query for all data fetching
// Enable automatic refetching, caching, background updates
// Handle loading and error states properly
```

## WebSocket Integration

**Real-time Data Streams:**
1. Market data (price, volume updates)
2. Order status changes
3. Agent analysis results
4. Portfolio updates
5. Trading signals

**Implementation:**
- Reconnection logic with exponential backoff
- Heartbeat mechanism
- Message queue for offline handling
- Type-safe message parsing

## Component Guidelines

**Common Component Requirements:**
1. Fully typed with TypeScript
2. Accessible (ARIA labels, keyboard navigation)
3. Responsive design (mobile, tablet, desktop)
4. Loading states
5. Error states with retry mechanisms
6. No hardcoded colors (use Tailwind config)

**Chart Components:**
- Use Recharts for standard charts (line, bar, pie)
- Use TradingView Lightweight Charts for candlesticks
- Responsive and performant with large datasets
- Color-coded for profit/loss
- Interactive tooltips

**Data Tables:**
- Sortable columns
- Filterable data
- Pagination for large datasets
- Export functionality
- Column customization

## A-Share Specific UI Elements

**Board Indicators:**
- Color-code stocks by board (Main/ChiNext/STAR)
- Display price limit percentages
- Show capital requirements

**Risk Indicators:**
- Share pledge ratio warnings
- Restricted unlock alerts
- Goodwill impairment flags
- Compliance status

**Chinese Market Features:**
- Support for Chinese characters
- Date formats (YYYY-MM-DD)
- Number formatting (10,000 = 1万)
- Trading hours display (9:30-15:00)

## Development Commands

```bash
# Install dependencies
npm install

# Run development server (user will do this)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint

# Format code
npm run format
```

## Environment Variables

Required environment variables in `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=HiddenGem Trading System
```

## Performance Optimization

1. **Code Splitting**: Lazy load routes and heavy components
2. **Virtualization**: Use react-window for large lists
3. **Memoization**: Use React.memo, useMemo, useCallback appropriately
4. **Debouncing**: Debounce search inputs and API calls
5. **Image Optimization**: Use optimized formats, lazy loading
6. **Bundle Size**: Monitor and optimize bundle size

## Error Handling

1. **Error Boundaries**: Wrap major sections in error boundaries
2. **API Errors**: Display user-friendly error messages
3. **Validation**: Client-side validation before API calls
4. **Retry Logic**: Implement retry for failed requests
5. **Fallbacks**: Provide fallback UI for failed components

## Accessibility

1. **Keyboard Navigation**: All interactive elements accessible via keyboard
2. **Screen Readers**: Proper ARIA labels and roles
3. **Color Contrast**: WCAG AA compliant contrast ratios
4. **Focus Management**: Visible focus indicators
5. **Semantic HTML**: Use proper HTML elements

## Testing Strategy

1. **Component Tests**: Test individual components with React Testing Library
2. **Integration Tests**: Test page-level functionality
3. **E2E Tests**: Test critical user flows with Playwright
4. **Visual Tests**: Screenshot testing for UI consistency

## Important Notes

1. **No Mock Data**: Always fetch from real backend APIs
2. **Type Safety**: Use TypeScript strictly, no `any` types
3. **Responsive**: Test on mobile, tablet, desktop
4. **Real-time**: Implement WebSocket for live updates
5. **Performance**: Monitor render performance, optimize re-renders
6. **Security**: Sanitize user inputs, handle auth tokens securely
7. **Documentation**: Comment complex logic, document component props
