import psutil
import time

while True:
    try:
        timestamp = str(time.time())
        mem_percent = f'{psutil.virtual_memory().percent:.2f}%'
        cpu_percents = [f'{cpu:.2f}%' for cpu in psutil.cpu_percent(percpu=True)]
        print('\t'.join([timestamp, mem_percent] + cpu_percents))
        time.sleep(1)
    except KeyboardInterrupt:
        break
