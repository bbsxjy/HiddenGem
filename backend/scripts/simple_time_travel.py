import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from trading.simple_trading_env import SimpleTradingEnv
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

try:
    from tradingagents.dataflows.interface import get_stock_data_dataframe
    DATA_AVAILABLE = True
except ImportError:
    DATA_AVAILABLE = False

def generate_synthetic_data(start_date, end_date):
    dates = pd.date_range(start_date, end_date, freq='D')
    np.random.seed(42)
    n_days = len(dates)
    returns = np.random.randn(n_days) * 0.02 + 0.0005
    prices = 10.0 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.randn(n_days) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(n_days) * 0.02)),
        'low': prices * (1 - np.abs(np.random.randn(n_days) * 0.02)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days)
    })

def load_data(symbol, start_date, end_date):
    logger.info(f'Loading {symbol} from {start_date} to {end_date}')
    
    if DATA_AVAILABLE:
        try:
            df = get_stock_data_dataframe(symbol, start_date, end_date)
            if df is not None and not df.empty:
                logger.info(f'Loaded {len(df)} days of real data')
                return df
        except Exception as e:
            logger.warning(f'Real data failed: {e}')
    
    logger.warning('Using synthetic data')
    return generate_synthetic_data(start_date, end_date)

def create_episodes(data, window_months=6, step_months=1):
    episodes = []
    start = data['date'].min()
    end = data['date'].max()
    current = start
    eid = 0
    
    while current < end:
        window_end = current + pd.DateOffset(months=window_months)
        if window_end > end:
            window_end = end
        
        mask = (data['date'] >= current) & (data['date'] < window_end)
        ep_data = data[mask].copy().reset_index(drop=True)
        
        if len(ep_data) >= 30:
            episodes.append({
                'id': eid,
                'start': current.strftime('%Y-%m-%d'),
                'end': window_end.strftime('%Y-%m-%d'),
                'data': ep_data,
                'days': len(ep_data)
            })
            eid += 1
        
        current += pd.DateOffset(months=step_months)
    
    return episodes

logger.info('='*60)
logger.info('TIME TRAVEL TRAINING')
logger.info('='*60)

symbol = '000001.SZ'
full_data = load_data(symbol, '2022-01-01', '2024-01-01')
episodes = create_episodes(full_data, 6, 1)

logger.info(f'Created {len(episodes)} episodes')
for ep in episodes[:3]:
    logger.info(f"  Ep{ep['id']}: {ep['start']} to {ep['end']}")
if len(episodes) > 3:
    logger.info(f'  ...and {len(episodes)-3} more')

model = None
results = []

for i, ep in enumerate(episodes):
    logger.info('')
    logger.info(f"Episode {ep['id']+1}/{len(episodes)}: {ep['start']} to {ep['end']}")
    
    env = SimpleTradingEnv(df=ep['data'], initial_cash=100000)
    vec_env = DummyVecEnv([lambda: env])
    
    if model is None:
        model = PPO('MlpPolicy', vec_env, learning_rate=0.0003, verbose=0)
    else:
        model.set_env(vec_env)
    
    model.learn(total_timesteps=3000, progress_bar=False)
    
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, r, terminated, truncated, info = env.step(action)
        done = terminated or truncated
    
    fv = info.get('final_value', env._get_portfolio_value())
    ret = (fv - 100000) / 100000
    
    logger.info(f"  Return: {ret:+.2%}, Final: {fv:,.2f}")
    results.append(ret)

os.makedirs('models', exist_ok=True)
model.save('models/ppo_trading_agent')

logger.info('')
logger.info('='*60)
logger.info('COMPLETED')
logger.info(f'Episodes: {len(results)}')
logger.info(f'Avg Return: {np.mean(results):+.2%}')
logger.info(f'Model saved to: models/ppo_trading_agent.zip')
logger.info('='*60)
