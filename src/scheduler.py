import time
import subprocess
import logging
import argparse
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Scheduler")

def run_pipeline():
    """
    Executes the full quant pipeline: Data -> Factors -> Strategy (with Email).
    """
    logger.info("--- Starting Daily Quant Pipeline ---")
    
    scripts = [
        ["python3", "src/main_data.py"],
        ["python3", "src/main_factors.py"],
        ["python3", "src/main_strategy.py", "--notify"]
    ]
    
    for cmd in scripts:
        try:
            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing {cmd[1]}: {e.stderr}")
            # We continue to the next script if one fails, or decide to stop
            break
            
    logger.info("--- Daily Quant Pipeline Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autofin Bot Scheduler")
    parser.add_argument("--now", action="store_true", help="Run pipeline immediately and exit")
    args = parser.parse_args()

    if args.now:
        logger.info("Manual trigger detected (--now). Starting pipeline...")
        run_pipeline()
        exit(0)

    # Define Timezone (Eastern Standard Time for US Markets)
    tz = timezone('America/New_York')
    scheduler = BlockingScheduler(timezone=tz)
    
    # Schedule the job for 08:30 AM EST every day
    # This is roughly 1 hour before US Market Open
    scheduler.add_job(run_pipeline, 'cron', hour=8, minute=30)
    
    logger.info(f"Scheduler started. Next run at 08:30 AM EST (America/New_York).")
    
    # Initial run check via environment variable
    if os.getenv("RUN_IMMEDIATELY", "false").lower() == "true":
        logger.info("RUN_IMMEDIATELY env var is true. Starting initial pipeline run...")
        run_pipeline()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
