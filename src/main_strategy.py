import os
import sys
import argparse
import pandas as pd
from utils.config_loader import load_config
from utils.logger import setup_logger
from data_engine.db_manager import DBManager
from analysis_engine.ic_analyzer import ICAnalyzer
from analysis_engine.backtester import Backtester
from strategy_optimizer.allocator import Allocator
from utils.notifier import Notifier

def main():
    parser = argparse.ArgumentParser(description="Universal Automated Strategy Analysis")
    parser.add_argument("--notify", action="store_true", help="Send email notification")
    args = parser.parse_args()

    # Setup environment
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        sys.path.append(os.path.join(base_dir, "src"))
        
    logger = setup_logger("StrategyAnalysis")
    config = load_config("config.yaml")
    
    db_manager = DBManager(config['database']['path'])
    logger.info("Starting Universal Automated Strategy Analysis...")
    
    # 1. Fetch Data
    all_prices = db_manager.get_raw_prices()
    factor_matrix = db_manager.get_factor_matrix()
    
    if factor_matrix.empty or all_prices.empty:
        logger.warning("Insufficient data in database.")
        return

    # 2. Factor Validation (IC Analysis)
    fwd_returns = ICAnalyzer.calculate_forward_returns(all_prices, period=1)
    factor_long = factor_matrix.melt(id_vars=['timestamp', 'ticker'], var_name='factor_name', value_name='value')
    
    ic_series = ICAnalyzer.calculate_rank_ic(factor_long, fwd_returns)
    ic_summary = ICAnalyzer.get_summary_stats(ic_series)
    
    # 3. Signal Synthesis (IC-Weighted)
    # Filter factors with valid IC/IR stats
    ic_summary = ic_summary.dropna(subset=['mean_ic', 'ir'])
    
    if ic_summary.empty:
        logger.warning("No valid factors found after IC analysis. Using equal weights.")
        factor_names = factor_matrix.columns.drop(['timestamp', 'ticker']).tolist()
        ic_summary = pd.DataFrame(index=factor_names)
        ic_summary['weight'] = 1.0 / len(factor_names)
    else:
        # Use IR (stability) as the weight for each factor
        ic_summary['abs_ir'] = ic_summary['ir'].abs().fillna(0)
        total_ir = ic_summary['abs_ir'].sum()
        
        if total_ir > 0:
            ic_summary['weight'] = ic_summary['ir'] / total_ir
        else:
            ic_summary['weight'] = 1.0 / len(ic_summary)
        
    logger.info("\n=== Factor Weights (based on IC/IR) ===")
    print(ic_summary[['mean_ic', 'ir', 'weight']])
    
    # Calculate weighted signal
    # We use the full matrix and dot product with weights
    factor_names = ic_summary.index.tolist()
    weights_vec = ic_summary['weight'].values
    
    signal_df = factor_matrix.copy()
    signal_df['value'] = signal_df[factor_names].dot(weights_vec)
    
    # 4. Risk-Based Allocation
    logger.info("Calculating Risk-Managed Weights...")
    risk_weights = Allocator.calculate_inverse_vol_weights(all_prices, window=30)
    
    # Calculate Market Volatility (average of all tickers) for the adaptive buffer
    # Actually use average ticker volatility as market risk proxy
    mkt_vol_series = all_prices.sort_values(['ticker', 'timestamp'])
    mkt_vol_series['ret'] = mkt_vol_series.groupby('ticker')['close'].pct_change()
    mkt_vol_series['vol'] = mkt_vol_series.groupby('ticker')['ret'].transform(lambda x: x.rolling(30).std())
    market_vol = mkt_vol_series.groupby('timestamp')['vol'].mean()

    # Target Weights (Alpha * Beta + Constraints)
    final_weights = Allocator.allocate_weights(
        signal_df[['timestamp', 'ticker', 'value']], 
        risk_weights,
        max_weight=0.2 # No asset > 20%
    )
    
    # 4.5 Apply Adaptive Rebalance Buffer (Enhanced Optimization)
    rebalance_threshold = config.get('factors', {}).get('rebalance_threshold', 0.05)
    logger.info(f"Applying Adaptive Rebalance Buffer (Base Threshold: {rebalance_threshold:.1%})...")
    final_weights = Allocator.apply_rebalance_buffer(
        final_weights, 
        threshold=rebalance_threshold,
        vol_series=market_vol
    )
    
    # 5. Realistic Backtest (Including Transaction Costs)
    logger.info("Executing backtest with transaction costs...")
    results = Backtester.calculate_strategy_returns(final_weights, fwd_returns, tc=0.001)
    
    # 6. Performance Factsheet
    metrics = Backtester.calculate_performance_metrics(results)
    
    print("\n" + "="*45)
    print("      UNIVERSAL STRATEGY PERFORMANCE")
    print("="*45)
    for k, v in metrics.items():
        print(f"{k:25}: {v}")
    print("="*45)

    # 7. Latest Target Portfolio (Actionable Output)
    latest_ts = final_weights['timestamp'].max()
    latest_portfolio = final_weights[final_weights['timestamp'] == latest_ts]
    
    print("\n" + "="*45)
    print(f"   TARGET PORTFOLIO (As of {latest_ts.date()})")
    print("="*45)
    formatted_port = latest_portfolio[['ticker', 'weight']].sort_values('weight', ascending=False)
    for _, row in formatted_port.iterrows():
        print(f"{row['ticker']:10}: {row['weight']:.2%}")
    print("="*45)

    # 8. Send Notification (If requested)
    if args.notify:
        api_url = os.getenv("EMAIL_API_URL", "http://100.124.61.26/mail-sender/api/v1/email/send")
        recipient = os.getenv("EMAIL_RECIPIENT", "uchuang9128@gmail.com")
        
        notifier = Notifier(api_url, recipient)
        portfolio_list = formatted_port.to_dict('records')
        notifier.send_report(metrics, portfolio_list)

if __name__ == "__main__":
    main()
