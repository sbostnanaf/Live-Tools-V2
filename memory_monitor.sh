#\!/bin/bash
echo "=== Memory Status $(date) ===" >> /home/ubuntu/Live-Tools-V2/memory.log
free -h >> /home/ubuntu/Live-Tools-V2/memory.log
echo "=== Top Memory Processes ===" >> /home/ubuntu/Live-Tools-V2/memory.log  
ps aux --sort=-%mem | head -5 >> /home/ubuntu/Live-Tools-V2/memory.log
echo "" >> /home/ubuntu/Live-Tools-V2/memory.log
