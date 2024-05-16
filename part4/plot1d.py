from typing import List, Tuple
from matplotlib import pyplot as plt
import numpy as np
from labellines import labelLine, labelLines

def read_measurements(filename: str) -> Tuple[List[float], List[float]]:
    with open(filename, 'r', encoding='utf-8') as file:
        qps: List[float] = []
        p95: List[float] = []
        start_times: List[float] = []
        end_times: List[float] = []
        for line in file:
            if line.startswith('read'):
                reading = line.split()
                qps.append(float(reading[16]) / 1000)
                p95.append(float(reading[12]) / 1000)
                start_times.append(float(reading[18][:10]))
                end_times.append(float(reading[19][:10]))
        return qps, p95, start_times, end_times
    
def read_cpu_utilization(filename: str) -> List[float]:
    cpu_info = {
        'c1': [],
        'time': [],
    }
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            reading = line.split()
            cpu_info['c1'].append(float(reading[2][:-1]))
            cpu_info['time'].append(float(reading[0].split('.')[0]))
        return cpu_info

def get_cpu_utilization(start_times, end_times, qpss, cpu_info):
    # take buckets of qps times
    qps_to_cpu = {}
    qps_to_cpu_median = {}
    for i in range(len(qpss)):
        start_time = start_times[i]
        end_time = end_times[i]
        cpu_utilization_curr = []
        for j in range(len(cpu_info['time'])):
            if start_time <= cpu_info['time'][j] <= end_time:
                cpu_utilization_curr.append(cpu_info['c1'][j])
        cpu_utilization_median = np.median(cpu_utilization_curr)
        qps_to_cpu[qpss[i]] = cpu_utilization_curr
        qps_to_cpu_median[qpss[i]] = cpu_utilization_median

    res = []
    for q in qpss[:-2]:
        for c in qps_to_cpu[q]:
            res.append([q, c])
    res = np.array(res)

    cpu_medians = []
    for q in qpss[:-2]:
        cpu_medians.append(qps_to_cpu_median[q])
    return res, np.array(cpu_medians)

fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(12, 6))

# ======================== First plot ========================
# read measurements
qpss = []
p95s = []
cpu_utilizations = []
qps_for_cpu = []
for i in range(1, 4):
    measurement_filename = f'measurements/mcperf-c1-t2-{i}.txt'
    qps, p95, start_times, end_times = read_measurements(measurement_filename)
    performance_filename = f'measurements/performance-c1-t2-{i}.txt'
    cpu_info = read_cpu_utilization(performance_filename)
    cpu_utilization, cpu_median = get_cpu_utilization(start_times, end_times, qps, cpu_info)
    cpu_utilizations.append(cpu_median)
    qpss.append(qps)
    p95s.append(p95)

qps_mean = np.mean(np.array(qpss), axis=0)
p95_mean = np.mean(np.array(p95s), axis=0)
cpu_utilizations = np.mean(np.array(cpu_utilizations), axis=0)

# x-axis
plt.xlim(0, 130)
plt.xticks(range(0, 140, 10))

# left y-axis
ax1.plot(qps_mean, p95_mean, 'g-', marker='>', label='95th percentile latency')
ax1.set_xlabel('Achieved queries per second [thousands]')
ax1.set_ylabel('95th percentile latency [ms]', color='g')
ax1.set_ylim(0, 5.5)
ax1.tick_params(axis='y', labelcolor='g')
ax1.set_title('T = 2, C = 1')
ax1.axhline(y=1, color='r', linestyle='--', linewidth=2)
ax1.grid(linestyle='--')
labelLines(ax1.get_lines(), align=False, fontsize=8)

# right y-axis
ax2 = ax1.twinx()
ax2.plot(qps_mean[:-2], cpu_utilizations, 'b-'  , marker='*', label='CPU utilization')
# ax2.scatter(cpu_utilization[:, 0], cpu_utilization[:, 1], color='b')
ax2.set_ylabel('CPU utilization [%]', color='b')
ax2.set_ylim(0, 110)
ax2.tick_params(axis='y', labelcolor='b')
ax2.grid(linestyle='--')
labelLines(ax2.get_lines(), align=False, fontsize=8)
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')
# ======================== Second plot ========================
# read measurements
qpss = []
p95s = []
cpu_utilizations = []
qps_for_cpu = []
for i in range(1, 4):
    measurement_filename = f'measurements/mcperf-c2-t2-{i}.txt'
    qps, p95, start_times, end_times = read_measurements(measurement_filename)
    performance_filename = f'measurements/performance-c2-t2-{i}.txt'
    cpu_info = read_cpu_utilization(performance_filename)
    cpu_utilization, cpu_median = get_cpu_utilization(start_times, end_times, qps, cpu_info)
    cpu_utilizations.append(cpu_median)
    qpss.append(qps)
    p95s.append(p95)

qps_mean = np.mean(np.array(qpss), axis=0)
p95_mean = np.mean(np.array(p95s), axis=0)
cpu_utilizations = np.mean(np.array(cpu_utilizations), axis=0)

# x-axis
plt.xlim(0, 130)
plt.xticks(range(0, 140, 10))

# left y-axis
ax3.plot(qps_mean, p95_mean, 'g-', marker='>', label='95th percentile latency')
ax3.set_xlabel('Achieved queries per second [thousands]')
ax3.set_ylabel('95th percentile latency [ms]', color='g')
ax3.set_ylim(0, 1.1)
ax3.tick_params(axis='y', labelcolor='g')
ax3.set_title('T = 2, C = 2')
ax3.axhline(y=1, color='r', linestyle='--', linewidth=2)
ax3.grid(linestyle='--')
labelLines(ax3.get_lines(), align=False, fontsize=8, yoffsets=0.05)
# right y-axis
ax4 = ax3.twinx()
ax4.plot(qps_mean[:-2], cpu_utilizations, 'b-', marker='*', label='CPU utilization')
ax4.set_ylabel('CPU utilization [%]', color='b')
ax4.set_yticks(range(0, 220, 20))
ax4.set_ylim(0, 220)
ax4.tick_params(axis='y', labelcolor='b')
ax4.grid(linestyle='--')
labelLines(ax4.get_lines(), align=False, fontsize=8)
ax3.legend(loc='upper left')
ax4.legend(loc='upper right')

# Adjust layout
plt.tight_layout()
plt.savefig('plot1d.svg')
# Display the plot
plt.show()