#!/bin/bash
set -e  # Exit on any error

cd /home/ugaikwad/preprint-bot
source venv/bin/activate

LOG_DIR="logs/cron"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Starting unified pipeline at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Run unified pipeline with today's date
TODAY=$(date +%Y-%m-%d)
echo "Running pipeline for date: $TODAY" | tee -a "$LOG_FILE"

python date_pipeline.py \
    --date $TODAY \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "ERROR: Pipeline failed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Pipeline completed at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Clean old logs (keep last 30 days)
find "$LOG_DIR" -name "*.log" -mtime +30 -delete