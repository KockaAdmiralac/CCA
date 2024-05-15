import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from datetime import datetime


# Read Jobs
jobs_path = "measurements/part3/results.json"
jobs_json = json.load(open(jobs_path))

jobs_dict = {}
for job_result in jobs_json["items"]:
    name = job_result["status"]["containerStatuses"][0]["name"]
    name = name.split("-")[1]
    job_dict = job_result["status"]["containerStatuses"][0]["state"]
    if "terminated" not in job_dict:
        continue

    start_time = job_dict["terminated"]["startedAt"]
    start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ").timestamp()

    end_time = job_dict["terminated"]["finishedAt"]
    end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%SZ").timestamp()

    jobs_dict[name] = {
        "start_time": start_time,
        "end_time": end_time,
    }

start_time = min([jobs_dict[name]["start_time"] for name in jobs_dict])

for name in jobs_dict:
    jobs_dict[name]["start_time"] -= start_time
    jobs_dict[name]["end_time"] -= start_time

for name in jobs_dict:
    print(name, jobs_dict[name]["start_time"], jobs_dict[name]["end_time"])

# Add colors
name_to_color = {
    "blackscholes": "CCA000",
    "canneal": "CCCCAA",
    "dedup": "CCACCA",
    "ferret": "AACCCA",
    "freqmine": "0CCA00",
    "radix": "00CCA0",
    "vips": "CC0A00",
}
rgb_colors = {
    name: mcolors.hex2color("#" + hex_color)
    for name, hex_color in name_to_color.items()
}


for name in rgb_colors:
    jobs_dict[name]["color"] = rgb_colors[name]

# Read memcached latencies
p95_path = "measurements/part3/mcperf.txt"
# read csv, first row is header
df = pd.read_csv(p95_path, header=0, delim_whitespace=True)

memcached_start = df["ts_start"] / 1000
memcached_end = df["ts_end"] / 1000

memcached_start = memcached_start - start_time
memcached_end = memcached_end - start_time
bar_widths = [end - start for start, end in zip(memcached_start, memcached_end)]

latencies = df["p95"]


# Plot
plt.bar(memcached_start, latencies, width=bar_widths, align="edge")
# horizontal line
plt.axhline(y=1000, color="gray", linestyle="--")
plt.text(0, 1005, "SLO", rotation=0)

plt.show()
for name in jobs_dict:
    plt.vlines(
        x=[jobs_dict[name]["start_time"], jobs_dict[name]["end_time"]],
        ymin=0,
        ymax=1000,
        color=jobs_dict[name]["color"],
        linestyle="-",
    )

plt.ylabel("p95 latency (micro s)")
plt.xlabel("time (s)")

plt.show()
