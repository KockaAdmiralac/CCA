import psutil
import sys
import time

while True:
    memcached = psutil.Process(int(sys.argv[1]))
    try:
        timestamp = str(time.time())
        mem_percent = f'{memcached.memory_percent():.2f}%'
        cpu_percent = f'{memcached.cpu_percent(1):.2f}%'
        print('\t'.join([timestamp, mem_percent, cpu_percent]), flush=True)
    except KeyboardInterrupt:
        break
