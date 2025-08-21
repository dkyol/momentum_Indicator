#!/bin/bash
"""
Start Robust Trading System
Comprehensive startup script with process monitoring and auto-restart
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
SCHEDULER_SCRIPT="robust_scheduler.py"
PID_FILE="scheduler.pid"
LOG_FILE="system_startup.log"
RESTART_ATTEMPTS=5

echo "=============================================="
echo "ROBUST TRADING SYSTEM STARTUP"
echo "=============================================="
echo "Features:"
echo "• Multi-layer failsafe scheduling"
echo "• Emergency backup execution"
echo "• Health monitoring & auto-restart"
echo "• Comprehensive logging"
echo "• Missed execution detection"
echo "=============================================="

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if scheduler is running
is_scheduler_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Function to start scheduler
start_scheduler() {
    log_message "Starting robust trading scheduler..."
    
    # Kill any existing processes
    pkill -f "$SCHEDULER_SCRIPT" 2>/dev/null
    sleep 2
    
    # Start new process
    nohup python3 "$SCHEDULER_SCRIPT" >> robust_scheduler.log 2>&1 &
    SCHEDULER_PID=$!
    
    # Save PID
    echo "$SCHEDULER_PID" > "$PID_FILE"
    
    # Wait a moment to check if it started successfully
    sleep 3
    
    if is_scheduler_running; then
        log_message "Scheduler started successfully (PID: $SCHEDULER_PID)"
        return 0
    else
        log_message "Failed to start scheduler"
        return 1
    fi
}

# Function to monitor scheduler health
monitor_scheduler() {
    local attempt=1
    
    while [ $attempt -le $RESTART_ATTEMPTS ]; do
        if is_scheduler_running; then
            log_message "Scheduler is running normally"
            sleep 300  # Check every 5 minutes
        else
            log_message "Scheduler not running, attempting restart (attempt $attempt/$RESTART_ATTEMPTS)"
            
            if start_scheduler; then
                log_message "Scheduler restarted successfully"
                attempt=1  # Reset counter on successful restart
            else
                log_message "Restart attempt $attempt failed"
                attempt=$((attempt + 1))
                sleep 30  # Wait before retry
            fi
        fi
    done
    
    log_message "Max restart attempts exceeded. Manual intervention required."
}

# Function to show system status
show_status() {
    echo "System Status:"
    if is_scheduler_running; then
        PID=$(cat "$PID_FILE")
        echo "  ✅ Scheduler: Running (PID: $PID)"
        echo "  📊 Logs: robust_scheduler.log"
        echo "  📋 Status: scheduler_status.json"
        echo "  📝 Execution Log: execution_log.json"
    else
        echo "  ❌ Scheduler: Not running"
    fi
    
    if [ -f "scheduler_status.json" ]; then
        echo "  📈 Last Status:"
        python3 -c "
import json
try:
    with open('scheduler_status.json', 'r') as f:
        data = json.load(f)
        print(f'    Task: {data.get(\"task\", \"N/A\")}')
        print(f'    Status: {data.get(\"status\", \"N/A\")}')
        print(f'    Time: {data.get(\"last_update\", \"N/A\")}')
except:
    print('    Status file not available')
"
    fi
}

# Main execution based on arguments
case "$1" in
    start)
        log_message "System startup requested"
        if is_scheduler_running; then
            log_message "Scheduler already running"
            show_status
        else
            if start_scheduler; then
                log_message "System started successfully"
                show_status
            else
                log_message "Failed to start system"
                exit 1
            fi
        fi
        ;;
    
    stop)
        log_message "System shutdown requested"
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            kill "$PID" 2>/dev/null
            sleep 2
            rm -f "$PID_FILE"
            log_message "Scheduler stopped"
        else
            log_message "Scheduler was not running"
        fi
        ;;
    
    restart)
        log_message "System restart requested"
        $0 stop
        sleep 2
        $0 start
        ;;
    
    monitor)
        log_message "Starting continuous monitoring"
        monitor_scheduler
        ;;
    
    status)
        show_status
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|monitor|status}"
        echo
        echo "Commands:"
        echo "  start   - Start the robust trading scheduler"
        echo "  stop    - Stop the scheduler"
        echo "  restart - Restart the scheduler"
        echo "  monitor - Start continuous monitoring with auto-restart"
        echo "  status  - Show current system status"
        echo
        echo "Files created:"
        echo "  robust_scheduler.log   - Main scheduler logs"
        echo "  scheduler_status.json  - Current status"
        echo "  execution_log.json     - Execution history"
        echo "  system_startup.log     - Startup/monitoring logs"
        exit 1
        ;;
esac

echo "=============================================="