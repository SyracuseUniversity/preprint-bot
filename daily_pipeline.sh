#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FALLBACK_LOG="/home/preprint-bot/logs/cron/startup_error.log"
mkdir -p "$(dirname "$FALLBACK_LOG")"
exec 2>>"$FALLBACK_LOG"

source venv/bin/activate

# Read config values from config.py
NOTIFY_EMAIL="ugaikwad@syr.edu"
LOG_RETENTION_DAYS=30
LOG_DIR="logs/cron"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Starting unified pipeline at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

TODAY=$(date +%Y-%m-%d)
echo "Running pipeline for date: $TODAY" | tee -a "$LOG_FILE"

preprint_bot \
    --date "$TODAY" \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "ERROR: Pipeline failed" | tee -a "$LOG_FILE"
    echo "Preprint-bot pipeline failed at $(date). Check $LOG_FILE for details." | \
        mail -s "Preprint-bot Pipeline Failure" "$NOTIFY_EMAIL"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Pipeline completed at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

find "$LOG_DIR" -name "*.log" -mtime +"$LOG_RETENTION_DAYS" -delete
