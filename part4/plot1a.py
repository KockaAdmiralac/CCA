from typing import List, Tuple
from matplotlib import pyplot as plt
import numpy as np

def read_measurements(filename: str) -> Tuple[List[float], List[float]]:
    with open(filename, 'r', encoding='utf-8') as file:
        qps: List[float] = []
        p95: List[float] = []
        for line in file:
            if line.startswith('read'):
                reading = line.split()
                qps.append(float(reading[16]) / 1000)
                p95.append(float(reading[12]) / 1000)
        return qps, p95

plt.figure(figsize=(10, 6))
T = [1, 2]
C = [1, 2]

markers = ['o', 's', 'v', 'X', 'd']

interference_values = [[t, c] for t in T for c in C]
for (t, c) in interference_values:
    interference = f'c{c}-t{t}'
    qpss = []
    p95s = []
    for i in range(1, 4):
        measurement_filename = f'measurements/mcperf-{interference}-{i}.txt'
        qps, p95 = read_measurements(measurement_filename)
        qpss.append(qps)
        p95s.append(p95)
    qps_mean = np.mean(np.array(qpss), axis=0)
    qps_std = np.std(np.array(qpss), axis=0)
    p95_mean = np.mean(np.array(p95s), axis=0)
    p95_std = np.std(np.array(p95s), axis=0)
    curr_marker = markers.pop(0)
    plt.errorbar(qps_mean, p95_mean, xerr=qps_std, yerr=p95_std, label=f'T = {t}, C = {c}', fmt='-' + curr_marker, linewidth=1)
    plt.scatter(qps_mean, p95_mean, marker=curr_marker)

plt.legend()
plt.xlim(0, 125)
plt.xticks(range(0, 130, 10))
plt.xlabel('Achieved queries per second [thousands]')
plt.yticks(range(3))
plt.ylim(0, 3)
plt.ylabel('95th percentile latency [ms]')
plt.setp(plt.gca().get_xticklabels(), rotation=45, ha='right')
plt.grid(linestyle='--')
plt.savefig('plot1.svg')
plt.show()