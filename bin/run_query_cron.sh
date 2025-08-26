#!/bin/bash

# cd to repo root no matter where it’s called from
cd "$(dirname "$0")/.." || exit

echo "Running query_arxiv.py at $(date)" >> /tmp/query_cron.log
python3 src/preprint_bot/query_arxiv.py --category cs.CL --max-results 3 --delay 1.0 >> /tmp/query_cron.log 2>&1
