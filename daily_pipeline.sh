#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FALLBACK_LOG="/home/ugaikwad/preprint-bot/logs/cron/startup_error.log"
mkdir -p "$(dirname "$FALLBACK_LOG")"
exec 2>>"$FALLBACK_LOG"

source venv/bin/activate

# Read config values from config.py
NOTIFY_EMAIL=$(python -c "from src.preprint_bot.config import NOTIFY_EMAIL; print(NOTIFY_EMAIL)")
LOG_RETENTION_DAYS=$(python -c "from src.preprint_bot.config import LOG_RETENTION_DAYS; print(LOG_RETENTION_DAYS)")
PIPELINE_SCRIPT=$(python -c "from src.preprint_bot.config import PIPELINE_SCRIPT; print(PIPELINE_SCRIPT)")
LOG_DIR=$(python -c "from src.preprint_bot.config import LOG_DIR; print(LOG_DIR)")

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Starting unified pipeline at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

TODAY=$(date +%Y-%m-%d)
echo "Running pipeline for date: $TODAY" | tee -a "$LOG_FILE"

python "$PIPELINE_SCRIPT" \
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