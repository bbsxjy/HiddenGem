/**
 * Calculate profit/loss
 */
export function calculateProfitLoss(currentPrice: number, avgCost: number, quantity: number): number {
  return (currentPrice - avgCost) * quantity;
}

/**
 * Calculate profit/loss percentage
 */
export function calculateProfitLossPercent(currentPrice: number, avgCost: number): number {
  if (avgCost === 0) return 0;
  return (currentPrice - avgCost) / avgCost;
}

/**
 * Calculate percentage change
 */
export function calculatePercentageChange(current: number, previous: number): number {
  if (previous === 0) return 0;
  return (current - previous) / previous;
}

/**
 * Calculate position weight in portfolio
 */
export function calculateWeight(positionValue: number, totalValue: number): number {
  if (totalValue === 0) return 0;
  return positionValue / totalValue;
}

/**
 * Calculate Sharpe ratio
 */
export function calculateSharpeRatio(
  returns: number[],
  riskFreeRate: number = 0.03
): number {
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance =
    returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  const stdDev = Math.sqrt(variance);

  if (stdDev === 0) return 0;
  return (avgReturn - riskFreeRate / 252) / stdDev;
}

/**
 * Calculate Sortino ratio (similar to Sharpe but only considers downside deviation)
 */
export function calculateSortinoRatio(
  returns: number[],
  riskFreeRate: number = 0.03
): number {
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const downsideReturns = returns.filter((r) => r < 0);

  if (downsideReturns.length === 0) return Infinity;

  const downsideVariance =
    downsideReturns.reduce((sum, r) => sum + Math.pow(r, 2), 0) / downsideReturns.length;
  const downsideStdDev = Math.sqrt(downsideVariance);

  if (downsideStdDev === 0) return 0;
  return (avgReturn - riskFreeRate / 252) / downsideStdDev;
}

/**
 * Calculate maximum drawdown
 */
export function calculateMaxDrawdown(equityCurve: number[]): number {
  let maxDrawdown = 0;
  let peak = equityCurve[0];

  for (const value of equityCurve) {
    if (value > peak) {
      peak = value;
    }
    const drawdown = (peak - value) / peak;
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }

  return maxDrawdown;
}

/**
 * Calculate Calmar ratio
 */
export function calculateCalmarRatio(
  annualReturn: number,
  maxDrawdown: number
): number {
  if (maxDrawdown === 0) return Infinity;
  return annualReturn / maxDrawdown;
}

/**
 * Calculate Value at Risk (VaR)
 */
export function calculateVaR(
  returns: number[],
  confidenceLevel: number = 0.95
): number {
  const sorted = [...returns].sort((a, b) => a - b);
  const index = Math.floor((1 - confidenceLevel) * sorted.length);
  return sorted[index] || 0;
}

/**
 * Calculate annualized return
 */
export function calculateAnnualizedReturn(
  totalReturn: number,
  days: number
): number {
  const years = days / 365;
  if (years === 0) return 0;
  return Math.pow(1 + totalReturn, 1 / years) - 1;
}

/**
 * Calculate annualized volatility
 */
export function calculateAnnualizedVolatility(returns: number[]): number {
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance =
    returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  const dailyStdDev = Math.sqrt(variance);
  return dailyStdDev * Math.sqrt(252); // 252 trading days per year
}

/**
 * Calculate win rate
 */
export function calculateWinRate(
  winningTrades: number,
  totalTrades: number
): number {
  if (totalTrades === 0) return 0;
  return winningTrades / totalTrades;
}

/**
 * Calculate profit/loss ratio
 */
export function calculateProfitLossRatio(
  avgWin: number,
  avgLoss: number
): number {
  if (avgLoss === 0) return Infinity;
  return Math.abs(avgWin / avgLoss);
}

/**
 * Calculate moving average
 */
export function calculateMovingAverage(data: number[], period: number): number[] {
  const result: number[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(NaN);
    } else {
      const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
      result.push(sum / period);
    }
  }

  return result;
}

/**
 * Calculate position size based on risk management
 */
export function calculatePositionSize(
  portfolioValue: number,
  riskPerTrade: number,
  entryPrice: number,
  stopLossPrice: number
): number {
  const riskAmount = portfolioValue * riskPerTrade;
  const riskPerShare = Math.abs(entryPrice - stopLossPrice);

  if (riskPerShare === 0) return 0;
  return Math.floor(riskAmount / riskPerShare);
}
