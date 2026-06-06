import os
import sys
from datetime import datetime, timedelta
from utils.config_loader import load_config
from utils.logger import setup_logger
from data_engine.providers.yfinance import YFinanceProvider
from data_engine.db_manager import DBManager
from data_engine.processor import Processor

def main():
    # 1. Setup Environment
    # Add src to python path for local execution
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        sys.path.append(os.path.join(base_dir, "src"))

    logger = setup_logger("DataEngine")
    
    try:
        config = load_config("config.yaml")
        logger.info("Configuration loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    # 2. Initialize Components
    db_path = config['database']['path']
    db_manager = DBManager(db_path)
    provider = YFinanceProvider()
    processor = Processor()
    
    # 3. Process Asset Pools
    lookback = config['processing'].get('lookback_days', 60)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
    
    for pool_name, pool_info in config['asset_pools'].items():
        tickers = pool_info['tickers']
        logger.info(f"Processing asset pool: {pool_name} ({len(tickers)} tickers)")
        
        for ticker in tickers:
            # Determine incremental start date
            latest_ts = db_manager.get_latest_timestamp(ticker)
            ticker_start = start_date
            
            if latest_ts:
                # Add 1 day to latest timestamp to avoid overlap
                ticker_start = (latest_ts + timedelta(days=1)).strftime("%Y-%m-%d")
            
            if ticker_start >= end_date:
                logger.info(f"Ticker {ticker} is already up to date (Latest: {latest_ts.date() if latest_ts else 'N/A'})")
                continue

            logger.info(f"Fetching {ticker} from {ticker_start} to {end_date}")
            
            # A. Fetch
            try:
                raw_df = provider.fetch_data([ticker], ticker_start, end_date)
                if raw_df.empty:
                    logger.warning(f"No new data fetched for {ticker}")
                    continue
                
                # B. Store Raw
                cleaned_raw = processor.clean_data(raw_df)
                db_manager.save_raw_prices(cleaned_raw)
                logger.info(f"Cleaned and saved {len(cleaned_raw)} rows for {ticker}")
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                continue

        # C. Process & Store (Log Returns) - Re-calculate for all to ensure continuity
        if config['processing'].get('log_returns'):
            try:
                all_prices = db_manager.get_raw_prices(tickers)
                processed_df = processor.calculate_log_returns(all_prices)
                db_manager.save_processed_data(processed_df)
                logger.info(f"Processed and saved log returns for {pool_name}")
            except Exception as e:
                logger.error(f"Error processing log returns for {pool_name}: {e}")

    # 4. Final Verification
    with db_manager.connection() as conn:
        raw_count = conn.execute("SELECT count(*) FROM raw_prices").fetchone()[0]
        proc_count = conn.execute("SELECT count(*) FROM processed_data").fetchone()[0]
        logger.info(f"Data Engine Run Complete. Total Raw: {raw_count}, Total Processed: {proc_count}")

if __name__ == "__main__":
    main()
