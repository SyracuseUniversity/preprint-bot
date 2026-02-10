# Run pipeline with today's date
TODAY=$(date +%Y-%m-%d)
echo "Running pipeline for date: $TODAY" | tee -a "$LOG_FILE"

python -m preprint_bot.date_pipeline \
    --mode corpus \
    --date $TODAY \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "ERROR: Pipeline failed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Pipeline complete" | tee -a "$LOG_FILE"