#!/bin/bash

cd /Users/adiloryspayev/Projects/OSPO/grobid || exit

echo "Running query_arxiv.py at $(date)" >> /tmp/query_cron.log
python3 query_arxiv.py --category cs.CL --max-results 3 --delay 1.0 >> /tmp/query_cron.log 2>&1
