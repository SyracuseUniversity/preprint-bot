 # SCHEDULE WITH CRON
#   1) Get the repo’s absolute path (from repo_root): `pwd`
#   2) Edit crontab:
#        crontab -e
#   3) Add a nightly entry (2:00 AM example). Replace /abs/path with your repo path:
#        0 2 * * * /abs/path/bin/preprint_bot_run_query_cron cs.CL 3 1.0 /abs/path/to/grobid >> /tmp/query_cron.log 2>&1
#   4) Verify:
#        crontab -l

#!/bin/bash

# Usage: ./preprint_bot_run_query_cron.sh /path/to/project

cd "$1" || exit

echo "Running query_arxiv.py at $(date)" >> /tmp/query_cron.log
python3 src/preprint_bot/query_arxiv.py --category cs.CL --max-results 3 --delay 1.0 >> /tmp/query_cron.log 2>&1
