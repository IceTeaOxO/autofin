import os
import sys
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from utils.config_loader import load_config
from utils.logger import setup_logger
from data_engine.db_manager import DBManager
from factor_factory.stats import StatsAnalyzer
from factor_factory.transforms import Transformers
from factor_factory.utils import FactorUtils
from factor_factory.factors.alpha_factors import MomentumFactor, MeanReversionFactor, VolatilityFactor
from strategy_optimizer.scorer import Scorer

def calculate_ticker_frac_diff(ticker, ticker_prices, factor_cfg):
    """
    Helper function to calculate FracDiff for a single ticker.
    Designed to run in a separate process.
    """
    close_series = ticker_prices.set_index('timestamp')['close']
    
    # Determine d
    if factor_cfg.get('frac_diff', {}).get('dynamic_d'):
        d = Transformers.find_optimal_d(close_series)
    else:
        d = factor_cfg.get('frac_diff', {}).get('default_d', 0.4)
        
    # Apply FracDiff
    fd_series = Transformers.frac_diff_ffd(close_series, d)
    
    # Convert to feature format
    fd_df = fd_series.to_frame(name='value').reset_index()
    fd_df.columns = ['timestamp', 'value']
    fd_df['ticker'] = ticker
    fd_df['factor_name'] = f'frac_diff_d{d}'
    return fd_df

def main():
    # Setup environment
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        sys.path.append(os.path.join(base_dir, "src"))
        
    logger = setup_logger("FactorFactory")
    config = load_config("config.yaml")
    
    db_manager = DBManager(config['database']['path'])
    logger.info("Factor Factory starting advanced feature generation...")
    
    # 1. Fetch Cleaned Prices
    all_prices = db_manager.get_raw_prices()
    if all_prices.empty:
        logger.warning("No data found in database.")
        return
        
    # 2. Fractional Differentiation (Advanced Transform) - Parallelized
    factor_cfg = config.get('factors', {})
    tickers = all_prices['ticker'].unique()
    
    logger.info(f"Starting parallel FracDiff calculation for {len(tickers)} tickers...")
    
    frac_diff_results = []
    with ProcessPoolExecutor() as executor:
        futures = []
        for ticker in tickers:
            ticker_prices = all_prices[all_prices['ticker'] == ticker].sort_values('timestamp')
            futures.append(executor.submit(calculate_ticker_frac_diff, ticker, ticker_prices, factor_cfg))
        
        for future in futures:
            try:
                res = future.result()
                frac_diff_results.append(res)
                logger.info(f"Completed FracDiff for {res['ticker'].iloc[0]} (Factor: {res['factor_name'].iloc[0]})")
            except Exception as e:
                logger.error(f"Error in parallel FracDiff calculation: {e}")
    
    if frac_diff_results:
        fd_final = pd.concat(frac_diff_results)
        fd_final['timestamp'] = pd.to_datetime(fd_final['timestamp'])
        db_manager.save_factor_scores(fd_final)
        logger.info("Fractional Differentiation scores saved.")

    # 3. Alpha Factors Calculation
    factors_to_run = [
        MomentumFactor(windows=factor_cfg.get('momentum', {}).get('windows', [20, 60])),
        MeanReversionFactor(window=factor_cfg.get('mean_reversion', {}).get('window', 20)),
        VolatilityFactor(window=factor_cfg.get('volatility', {}).get('window', 30))
    ]
    
    for factor in factors_to_run:
        try:
            scores = factor.calculate(all_prices)
            scores['timestamp'] = pd.to_datetime(scores['timestamp'])
            
            # Optional Neutralization
            if factor_cfg.get('neutralize'):
                # Basic market neutralization (removing global mean)
                scores['value'] = FactorUtils.neutralize(scores, 'value')
            
            # 4. Robust Scoring (New Optimization)
            scoring_cfg = factor_cfg.get('scoring', {})
            if scoring_cfg.get('enabled'):
                scores = Scorer.process_scores(scores, method=scoring_cfg.get('method', 'rank'))
                logger.info(f"Robust scoring applied to {factor.__class__.__name__} ({scoring_cfg.get('method')})")
                
            db_manager.save_factor_scores(scores)
            logger.info(f"Factor {factor.__class__.__name__} calculated and saved.")
        except Exception as e:
            logger.error(f"Error calculating {factor.__class__.__name__}: {e}")

    # 4. Final Verification: Check Factor Matrix
    matrix = db_manager.get_factor_matrix()
    logger.info(f"Factor Factory run complete. Matrix shape: {matrix.shape}")
    logger.info(f"Available factors: {matrix.columns.tolist()}")

if __name__ == "__main__":
    main()
