import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Layout } from './components/layout/Layout';

// Pages
import { Dashboard } from './pages/Dashboard';
import { Analysis } from './pages/Analysis';
import { Market } from './pages/Market';
import { Portfolio } from './pages/Portfolio';
import { TradingHub } from './pages/TradingHub';
import { TradeHistory } from './pages/TradeHistory';
import { Strategy } from './pages/Strategy';
import { Agents } from './pages/Agents';
import { Backtest } from './pages/Backtest';
import { Settings } from './pages/Settings';
import { MemoryBank } from './pages/MemoryBank';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <Routes>
            {/* Redirect root to dashboard */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Main app routes */}
            <Route
              path="/*"
              element={
                <Layout>
                  <Routes>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/analysis" element={<Analysis />} />
                    <Route path="/market" element={<Market />} />
                    <Route path="/portfolio" element={<Portfolio />} />
                    <Route path="/trading" element={<TradingHub />} />
                    <Route path="/trade-history" element={<TradeHistory />} />
                    <Route path="/strategy" element={<Strategy />} />
                    <Route path="/agents" element={<Agents />} />
                    <Route path="/backtest" element={<Backtest />} />
                    <Route path="/memory" element={<MemoryBank />} />
                    <Route path="/settings" element={<Settings />} />
                  </Routes>
                </Layout>
              }
            />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
