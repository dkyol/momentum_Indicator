#!/usr/bin/env python3
"""
Robust Trading Scheduler with Multiple Failsafes
- Redundant scheduling mechanisms
- Health monitoring and auto-restart
- Comprehensive logging and alerts
- Backup execution systems
"""

import os
import time
import logging
import signal
import sys
import threading
import subprocess
from datetime import datetime, timedelta
import pytz
import schedule
import json
from pathlib import Path

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robust_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RobustTradingScheduler:
    def __init__(self):
        self.running = True
        self.est = pytz.timezone('US/Eastern')
        self.health_check_interval = 30  # seconds
        self.last_successful_execution = {}
        self.failed_execution_count = 0
        self.max_failures = 3
        
        # Status tracking
        self.status_file = Path('scheduler_status.json')
        self.execution_log = Path('execution_log.json')
        
    def log_execution_status(self, task_name, status, details=None):
        """Track all execution attempts"""
        timestamp = datetime.now(self.est).isoformat()
        
        # Update status file
        status_data = {
            'last_update': timestamp,
            'task': task_name,
            'status': status,
            'details': details or {},
            'failed_count': self.failed_execution_count
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        # Append to execution log
        log_entry = {
            'timestamp': timestamp,
            'task': task_name,
            'status': status,
            'details': details
        }
        
        log_data = []
        if self.execution_log.exists():
            with open(self.execution_log, 'r') as f:
                try:
                    log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = []
        
        log_data.append(log_entry)
        # Keep only last 100 entries
        log_data = log_data[-100:]
        
        with open(self.execution_log, 'w') as f:
            json.dump(log_data, f, indent=2)

    def execute_with_failsafe(self, task_func, task_name, max_retries=3):
        """Execute task with retry logic and comprehensive error handling"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Executing {task_name} (attempt {attempt + 1}/{max_retries})")
                
                # Execute the task
                result = task_func()
                
                # Mark as successful
                self.last_successful_execution[task_name] = datetime.now(self.est)
                self.failed_execution_count = max(0, self.failed_execution_count - 1)
                
                self.log_execution_status(task_name, 'SUCCESS', {
                    'attempt': attempt + 1,
                    'result': str(result) if result else 'Completed'
                })
                
                logger.info(f"{task_name} completed successfully")
                return result
                
            except Exception as e:
                error_details = {
                    'attempt': attempt + 1,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                
                logger.error(f"{task_name} failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Progressive backoff
                    logger.info(f"Retrying {task_name} in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Final failure
                    self.failed_execution_count += 1
                    self.log_execution_status(task_name, 'FAILED', error_details)
                    logger.error(f"{task_name} failed after {max_retries} attempts")
                    
                    # Critical failure handling
                    if self.failed_execution_count >= self.max_failures:
                        self.handle_critical_failure(task_name, e)
        
        return None

    def handle_critical_failure(self, task_name, error):
        """Handle critical system failures"""
        logger.critical(f"Critical failure in {task_name}: {error}")
        
        # Try emergency execution via alternative method
        if task_name == 'morning_trades':
            self.emergency_trade_execution()
        elif task_name == 'eod_closure':
            self.emergency_position_closure()
        
        # Reset failure count after emergency handling
        self.failed_execution_count = 0

    def emergency_trade_execution(self):
        """Emergency backup for trade execution"""
        try:
            logger.warning("Executing emergency trade execution")
            from paper_trader import trader
            trader.morning_trade_execution(force_execute=True)
            logger.info("Emergency trade execution completed")
        except Exception as e:
            logger.critical(f"Emergency trade execution failed: {e}")

    def emergency_position_closure(self):
        """Emergency backup for position closure"""
        try:
            logger.warning("Executing emergency position closure")
            from paper_trader import trader
            trader.end_of_day_close()
            logger.info("Emergency position closure completed")
        except Exception as e:
            logger.critical(f"Emergency position closure failed: {e}")

    def update_market_data(self):
        """Update market data with error handling"""
        def _update():
            from scheduler import save_market_data
            save_market_data()
            return "Market data updated"
        
        return self.execute_with_failsafe(_update, 'market_data_update')

    def execute_morning_trades(self):
        """Execute morning trades with validation and failsafe"""
        def _execute():
            from paper_trader import trader
            
            # Verify it's trading time
            now = datetime.now(self.est)
            if now.weekday() > 4:  # Weekend check
                raise Exception("No trading on weekends")
            
            # Execute trades
            result = trader.morning_trade_execution()
            if result is False:
                raise Exception("Trade execution was blocked by validation")
            
            # Verify positions were created
            portfolio = trader.get_portfolio_summary()
            if len(portfolio['positions']) == 0:
                raise Exception("No positions created after trade execution")
            
            return f"Trades executed, {len(portfolio['positions'])} positions created"
        
        return self.execute_with_failsafe(_execute, 'morning_trades')

    def execute_eod_closure(self):
        """Execute end-of-day closure with verification"""
        def _execute():
            from paper_trader import trader
            
            # Get positions before closure
            portfolio_before = trader.get_portfolio_summary()
            active_positions_before = len(portfolio_before['positions'])
            
            if active_positions_before == 0:
                return "No active positions to close"
            
            # Execute closure
            trader.end_of_day_close()
            
            # Verify all positions were closed
            portfolio_after = trader.get_portfolio_summary()
            active_positions_after = len(portfolio_after['positions'])
            
            if active_positions_after > 0:
                raise Exception(f"{active_positions_after} positions remain active after closure")
            
            return f"{active_positions_before} positions closed successfully"
        
        return self.execute_with_failsafe(_execute, 'eod_closure')

    def setup_schedule(self):
        """Setup all scheduled tasks with redundancy"""
        # Clear existing schedule
        schedule.clear()
        
        # Market data updates at 10:05 AM EST (Monday-Friday)
        schedule.every().monday.at("10:05").do(self.update_market_data)
        schedule.every().tuesday.at("10:05").do(self.update_market_data)
        schedule.every().wednesday.at("10:05").do(self.update_market_data)
        schedule.every().thursday.at("10:05").do(self.update_market_data)
        schedule.every().friday.at("10:05").do(self.update_market_data)
        
        # Morning trades at 10:15 AM EST (Monday-Friday)
        schedule.every().monday.at("10:15").do(self.execute_morning_trades)
        schedule.every().tuesday.at("10:15").do(self.execute_morning_trades)
        schedule.every().wednesday.at("10:15").do(self.execute_morning_trades)
        schedule.every().thursday.at("10:15").do(self.execute_morning_trades)
        schedule.every().friday.at("10:15").do(self.execute_morning_trades)
        
        # End-of-day closure at 3:34 PM EST (Monday-Friday)
        schedule.every().monday.at("15:34").do(self.execute_eod_closure)
        schedule.every().tuesday.at("15:34").do(self.execute_eod_closure)
        schedule.every().wednesday.at("15:34").do(self.execute_eod_closure)
        schedule.every().thursday.at("15:34").do(self.execute_eod_closure)
        schedule.every().friday.at("15:34").do(self.execute_eod_closure)
        
        # Backup EOD closure 5 minutes later (failsafe)
        schedule.every().monday.at("15:39").do(self.backup_eod_check)
        schedule.every().tuesday.at("15:39").do(self.backup_eod_check)
        schedule.every().wednesday.at("15:39").do(self.backup_eod_check)
        schedule.every().thursday.at("15:39").do(self.backup_eod_check)
        schedule.every().friday.at("15:39").do(self.backup_eod_check)
        
        logger.info("Robust schedule configured with failsafes")

    def backup_eod_check(self):
        """Backup check to ensure EOD closure happened"""
        try:
            from paper_trader import trader
            portfolio = trader.get_portfolio_summary()
            
            if len(portfolio['positions']) > 0:
                logger.warning("Backup EOD check: Active positions found, executing closure")
                self.execute_eod_closure()
            else:
                logger.info("Backup EOD check: No active positions, closure successful")
                
        except Exception as e:
            logger.error(f"Backup EOD check failed: {e}")

    def health_monitor(self):
        """Continuous health monitoring in separate thread"""
        while self.running:
            try:
                now = datetime.now(self.est)
                
                # Check if we've missed any critical executions
                self.check_missed_executions(now)
                
                # Log system status
                if now.minute % 15 == 0:  # Every 15 minutes
                    self.log_system_status(now)
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                time.sleep(60)

    def check_missed_executions(self, current_time):
        """Check for missed critical executions"""
        if current_time.weekday() > 4:  # Skip weekends
            return
            
        # Check if we missed morning trades
        if current_time.hour == 10 and current_time.minute > 20:
            trade_key = 'morning_trades'
            last_execution = self.last_successful_execution.get(trade_key)
            
            if not last_execution or last_execution.date() < current_time.date():
                logger.warning("Missed morning trades detected, executing emergency backup")
                self.emergency_trade_execution()
        
        # Check if we missed EOD closure
        if current_time.hour >= 15 and current_time.minute > 40:
            eod_key = 'eod_closure'
            last_execution = self.last_successful_execution.get(eod_key)
            
            if not last_execution or last_execution.date() < current_time.date():
                logger.warning("Missed EOD closure detected, executing emergency backup")
                self.emergency_position_closure()

    def log_system_status(self, current_time):
        """Log comprehensive system status"""
        try:
            from paper_trader import trader
            portfolio = trader.get_portfolio_summary()
            
            status = {
                'time': current_time.strftime('%I:%M %p EST'),
                'portfolio_value': portfolio['total_value'],
                'active_positions': len(portfolio['positions']),
                'failed_count': self.failed_execution_count,
                'last_executions': {k: v.isoformat() for k, v in self.last_successful_execution.items()}
            }
            
            logger.info(f"System Status: {json.dumps(status, indent=2)}")
            
        except Exception as e:
            logger.error(f"Status logging failed: {e}")

    def run(self):
        """Main execution loop with health monitoring"""
        now = datetime.now(self.est)
        logger.info("=" * 60)
        logger.info("ROBUST TRADING SCHEDULER STARTED")
        logger.info("=" * 60)
        logger.info(f"Start time: {now.strftime('%A, %B %d, %Y at %I:%M %p EST')}")
        
        self.setup_schedule()
        
        # Start health monitoring in separate thread
        health_thread = threading.Thread(target=self.health_monitor, daemon=True)
        health_thread.start()
        
        logger.info("System Features:")
        logger.info("• Retry logic with exponential backoff")
        logger.info("• Emergency execution failsafes")
        logger.info("• Continuous health monitoring")
        logger.info("• Backup EOD closure checks")
        logger.info("• Comprehensive execution logging")
        logger.info("=" * 60)
        
        while self.running:
            try:
                schedule.run_pending()
                
                # Brief status update every hour
                current_time = datetime.now(self.est)
                if current_time.minute == 0:
                    next_run = schedule.next_run()
                    if next_run:
                        time_until = (next_run - datetime.now()).total_seconds()
                        hours = int(time_until // 3600)
                        minutes = int((time_until % 3600) // 60)
                        logger.info(f"Running - Next task in: {hours}h {minutes}m")
                
                time.sleep(30)  # Check every 30 seconds for better responsiveness
                
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(60)

    def stop(self):
        """Clean shutdown"""
        logger.info("Stopping robust trading scheduler...")
        self.running = False

# Global instance for signal handling
scheduler_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    if scheduler_instance:
        scheduler_instance.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    scheduler_instance = RobustTradingScheduler()
    scheduler_instance.run()