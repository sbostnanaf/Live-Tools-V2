#\!/bin/bash
cd /home/ubuntu/Live-Tools-V2
source .venv/bin/activate
export PYTHONPATH=/home/ubuntu/Live-Tools-V2:$PYTHONPATH
echo "--- Execution started at $(date) ---" >> cron.log
#python3 strategies/trix/multi_bitmart_lite.py >> cron.log 2>&1
python3 strategies/envelopes/multi_bitget.py >> cron.log 2>&1
echo "--- Execution finished at $(date) ---" >> cron.log
