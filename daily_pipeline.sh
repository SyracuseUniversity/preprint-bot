#!/bin/bash
set -e  # Exit on any error

cd /home/your-username/preprint-bot  # UPDATE THIS PATH LATER ON VM
source venv/bin/activate

LOG_DIR="logs/cron"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Starting daily pipeline at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Step 1: Corpus mode
echo "Step 1: Fetching arXiv papers..." | tee -a "$LOG_FILE"
python -m preprint_bot.pipeline \
    --mode corpus \
    --max-per-category 20 \
    --combined-query \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "ERROR: Corpus mode failed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Step 1: Complete" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 2: User mode
echo "Step 2: Processing user papers and generating recommendations..." | tee -a "$LOG_FILE"
python -m preprint_bot.pipeline \
    --mode user \
    --threshold medium \
    --method faiss \
    --use-sections \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "ERROR: User mode failed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Step 2: Complete" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Daily pipeline completed at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Clean old logs (keep last 30 days)
find "$LOG_DIR" -name "*.log" -mtime +30 -delete