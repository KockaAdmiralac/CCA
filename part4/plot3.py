from matplotlib import pyplot as plt
import numpy as np
from labellines import labelLine, labelLines
import json
from datetime import datetime
import matplotlib.colors as mcolors
import pandas as pd
import time

def time_to_timestamp(time_str):
    return float(datetime.fromisoformat(time_str).timestamp())

def get_job_dict(jobs_path):
    # Read csv file
    df = pd.read_csv(jobs_path, header=0)
    job_dict = {}

    job_names = ["radix", "blackscholes", "vips", "ferret", "canneal", "dedup", "freqmine"]
    for name in job_names:
        job_dict[name] = {
            "start_time": None,
            "end_time": None,
            "start_idx": None,
            "end_idx": None,
            "color": None,
            "duration": 0,
        }

    name_to_color = {
        "blackscholes": "CCA000",
        "canneal": "CCCCAA",
        "dedup": "CCACCA",
        "ferret": "AACCCA",
        "freqmine": "0CCA00",
        "radix": "00CCA0",
        "vips": "CC0A00",
    }

    first_timestamp = time_to_timestamp(df["time"][0])

    # find times
    for name in job_names:
        job_dict[name]["color"] = name_to_color[name]
        for i in range(len(df)):
            if df["jobs1"][i] == name or df["jobs2"][i] == name or df["jobs3"][i] == name:
                job_dict[name]["start_time"] = [time_to_timestamp(df["time"][i]) - first_timestamp]
                job_dict[name]["start_idx"] = [i]
                # find end time
                for j in range(i, len(df)):
                    if df["jobs1"][j] == name or df["jobs2"][j] == name or df["jobs3"][j] == name:
                        job_dict[name]["end_time"] = [time_to_timestamp(df["time"][j]) - first_timestamp]
                        job_dict[name]["end_idx"] = [j]
                break

    # print start and end times
    # for name in job_names:
    #     print(f"{name}: {job_dict[name]['start_time']} - {job_dict[name]['end_time']}")

    # check for pauses 
    for name in job_names:
        i = job_dict[name]["start_idx"][0]
        end_idx = job_dict[name]["end_idx"][0]
        total_end_time = time_to_timestamp(df["time"].iloc[end_idx]) - first_timestamp
        while i < end_idx:
            if df["jobs1"].iloc[i] != name and df["jobs2"].iloc[i] != name and df["jobs3"].iloc[i] != name:
                job_dict[name]["end_time"][-1] = time_to_timestamp(df["time"].iloc[i]) - first_timestamp
                job_dict[name]["end_idx"][-1] = df.index[i - 1]
                while df["jobs1"].iloc[i] != name and df["jobs2"].iloc[i] != name and df["jobs3"].iloc[i] != name:
                    i += 1
                job_dict[name]["start_time"].append(time_to_timestamp(df["time"].iloc[i]) - first_timestamp)
                job_dict[name]["start_idx"].append(df.index[i])
                for j in range(i, end_idx):
                    if df["jobs1"].iloc[j] != name and df["jobs2"].iloc[j] != name and df["jobs3"].iloc[j] != name:
                        job_dict[name]["end_time"].append(time_to_timestamp(df["time"].iloc[j]) - first_timestamp)
                        job_dict[name]["end_idx"].append(df.index[j])
                        break
            i += 1
        job_dict[name]["end_time"].append(total_end_time)
    
    # # print start and end times
    # for name in job_names:
    #     print(f"{name}: {job_dict[name]['start_time']} - {job_dict[name]['end_time']}")
    rgb_colors = {
        name: mcolors.hex2color("#" + hex_color)
        for name, hex_color in name_to_color.items()
    }
    for name in rgb_colors:
        job_dict[name]["color"] = rgb_colors[name]

    total_time = time_to_timestamp(df["time"].iloc[-1]) - first_timestamp
    return job_dict, total_time



def get_jobs_info(jobs_path, mcperf_path):
    # Read csv file
    df = pd.read_csv(jobs_path, header=0)

    # convert date time to timestamp
    jobs_timestamps = df["time"]
    jobs_timestamps = [datetime.fromisoformat(t).timestamp() for t in jobs_timestamps]
    # convert to int
    jobs_timestamps = np.array(jobs_timestamps, dtype=int)
    # rebase to 0
    jobs_timestamps = jobs_timestamps - jobs_timestamps[0]
    jobs_qps = df["qps"] / 1000
    cores = [1 if isinstance(df["jobs1"][i], str) else 2 for i in range(len(df))]
    qpss = []
    p95s = []

    # Read mcperf txt
    with open(mcperf_path, "r") as f:
        lines = f.readlines()
        timestamp_start = int(lines[3].split()[-1])
        timestamp_end = int(lines[4].split()[-1])
        for line in lines:
            if line.startswith("read"):
                reading = line.split()
                qpss.append(float(reading[16]) / 1000)
                p95s.append(float(reading[12]) / 1000)
    
    # get timestamps from start to end with step of 10s
    mcperf_timestamps = np.arange(0, timestamp_end - timestamp_start, 4000)
    # convert timestamps to seconds
    mcperf_timestamps = mcperf_timestamps / 1000
    return mcperf_timestamps, qpss, p95s, cores, jobs_timestamps, jobs_qps
    
def plot_A(ax, title, x, y, y2, label, label2):
    ax.plot(x, y, color='navy', label=label)
    ax.set_title(title)
    ax.set_xlabel('Time[s]')
    ax.set_ylabel('95th percentile latency[ms]', color='navy')
    ax.grid(linestyle='--', axis='y')
    ax.set_ylim(0, 2.3)
    ax.yaxis.set_ticks(np.arange(0, 1.25, 0.25))
    ax.axhline(y=1, color='purple', linestyle='--', linewidth=1)
    ax.text(-25, 1, "SLO", rotation=0, color="purple")
    ax.legend(loc='upper left')
    # labelLines(ax.get_lines(), align=False, fontsize=10, xvals=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90])

    ax2 = ax.twinx()
    ax2.plot(x, y2, color='cornflowerblue', label=label2)
    ax2.set_ylabel('QPS [thousands]', color='cornflowerblue')
    ax2.tick_params(axis='y')
    ax2.grid(axis='y', linestyle='--')
    ax2.yaxis.set_ticks(np.arange(0, 125, 25))
    ax2.set_ylim(0, 230)
    ax2.legend(loc='upper right')
    # labelLines(ax2.get_lines(), align=False, fontsize=10)


def plot_B(ax, title, x, y, y2, label, label2):
    ax.plot(x, y, color='purple', label=label)
    ax.set_title(title)
    ax.set_xlabel('Time[s]')
    ax.set_ylabel('CPU cores', color='purple')
    ax.grid(linestyle='--', axis='y')
    ax.yaxis.set_ticks(np.arange(1, 2.5, 0.5))
    ax.set_ylim(1, 5.5)
    ax.legend(loc='upper left')
    # labelLines(ax.get_lines(), align=False, fontsize=10)

    ax2 = ax.twinx()
    ax2.plot(x, y2, color='cornflowerblue', label=label2)
    ax2.set_ylabel('QPS [thousands]', color='cornflowerblue')
    ax2.tick_params(axis='y')
    ax2.grid(axis='y', linestyle='--')
    ax2.yaxis.set_ticks(np.arange(0, 125, 25))
    ax2.set_ylim(0, 225)
    ax2.legend(loc='upper right')
    # labelLines(ax2.get_lines(), align=False, fontsize=10)

def plot_jobs(ax, jobs_dict, plot_type="A"):
    for i, name in enumerate(jobs_dict):
        if plot_type == "A":
            spot = 1.2 + 0.15 * i
        else:
            spot = 3.1 + 0.3 * i

        for j in range(len(jobs_dict[name]["start_time"])):
            ax.vlines(
                x=[
                    jobs_dict[name]["start_time"][j],
                    jobs_dict[name]["end_time"][j],
                ],
                ymin=0,
                ymax= spot,
                color=jobs_dict[name]["color"],
                linestyle="-",
                linewidths=1,
                label=name,
            )
            # horizontal line between start and end 
            ax.hlines(
                y= spot,
                xmin=jobs_dict[name]["start_time"][j],
                xmax=jobs_dict[name]["end_time"][j],
                color=jobs_dict[name]["color"],
                linestyle="-",
                linewidths=2,
            )
            
            # add text on top of horizontal line
            if j != 0:
                continue
            ax.text(
                jobs_dict[name]["start_time"][j] + 10,
                spot + 0.03,
                name,
                rotation=0,
                color=jobs_dict[name]["color"],
            )

def calculate_durations(jobs_dict):
    for name in jobs_dict:
        for i in range(len(jobs_dict[name]["start_time"])):
            job_dict[name]["duration"] += jobs_dict[name]["end_time"][i] - jobs_dict[name]["start_time"][i]

def get_slo_violations(p95s, mcperf_ts, jobs_ts):
    # filter qps after last job
    first_job_start = jobs_ts[0]
    last_job_end = jobs_ts[-1]
    print(f"Last job end: {last_job_end}")
    new_p95s = [p95 for p95, t in zip(p95s, mcperf_ts) if t <= last_job_end and t >= first_job_start]
    # find violations over 1ms
    violations = [p95 for p95 in new_p95s if p95 > 1]
    # find percentage of violations
    print(f"Number of latecies: {len(new_p95s)}")
    percentage = len(violations) / len(new_p95s) * 100
    print(f"Percentage of violations: {percentage}%")
    return percentage, len(violations), len(new_p95s)

if __name__ == "__main__":
    # plot six plots in one figure with 3 rows and 2 columns
    fig, axs = plt.subplots(3, 2, figsize=(20, 20))

    # ======================== First row ========================
    # plot a line with a marker
    mcperf_ts, mcperf_qps, p95s, cores, jobs_ts, jobs_qps = get_jobs_info("measurements/part44-interval4/utilization.csv", "measurements/part44-interval4/mcperf.txt")
    plot_A(axs[0, 0], '1A', mcperf_ts[:-1], p95s, mcperf_qps, '95th percentile latency', 'QPS')
    job_dict, total_time1 = get_job_dict("measurements/part44-interval4/utilization.csv")
    plot_jobs(axs[0, 0], job_dict)
    plot_B(axs[0, 1], '1B', jobs_ts[1:], cores[1:], jobs_qps[1:], 'CPU cores', 'QPS')
    plot_jobs(axs[0, 1], job_dict, plot_type="B")
    print("============== Run 1 ==============")
    calculate_durations(job_dict)
    for name in job_dict:
        print(f"{name}: {job_dict[name]['duration']}")

    durations = {}
    for name in job_dict:
        durations[name] = [job_dict[name]["duration"]]
   
    slo_perc, slo_violations, len_p95s = get_slo_violations(p95s, mcperf_ts, jobs_ts)
    total_slo_violations = slo_violations
    total_len_p95s = len_p95s
    # ======================== Second row ========================
    # plot a bar chart
    mcperf_ts, mcperf_qps, p95s, cores, jobs_ts, jobs_qps = get_jobs_info("measurements/part44-interval4-2/utilization.csv", "measurements/part44-interval4-2/mcperf.txt")
    plot_A(axs[1, 0], '2A', mcperf_ts[:-1], p95s, mcperf_qps, '95th percentile latency', 'QPS')
    job_dict, total_time2 = get_job_dict("measurements/part44-interval4-2/utilization.csv")
    plot_jobs(axs[1, 0], job_dict)
    plot_B(axs[1, 1], '2B', jobs_ts[1:], cores[1:], jobs_qps[1:], 'CPU cores', 'QPS')
    plot_jobs(axs[1, 1], job_dict, plot_type="B")

    print("============== Run 2 ==============")
    calculate_durations(job_dict)
    for name in job_dict:
        print(f"{name}: {job_dict[name]['duration']}")
        durations[name].append(job_dict[name]["duration"])


    slo_perc, slo_violations, len_p95s = get_slo_violations(p95s, mcperf_ts, jobs_ts)
    total_slo_violations += slo_violations
    total_len_p95s += len_p95s
    # ======================== Third row ========================
    # plot a pie chart
    mcperf_ts, mcperf_qps, p95s, cores, jobs_ts, jobs_qps = get_jobs_info("measurements/part44-interval4-3/utilization.csv", "measurements/part44-interval4-3/mcperf.txt")
    plot_A(axs[2, 0], '3A', mcperf_ts[:-1], p95s, mcperf_qps, '95th percentile latency', 'QPS')
    job_dict, total_time3 = get_job_dict("measurements/part44-interval4-3/utilization.csv")
    plot_jobs(axs[2, 0], job_dict)
    plot_B(axs[2, 1], '3B', jobs_ts[1:], cores[1:], jobs_qps[1:], 'CPU cores', 'QPS')
    plot_jobs(axs[2, 1], job_dict, plot_type="B")

    print("============== Run 3 ==============")
    calculate_durations(job_dict)
    for name in job_dict:
        print(f"{name}: {job_dict[name]['duration']}")
        durations[name].append(job_dict[name]["duration"])

    slo_perc, slo_violations, len_p95s = get_slo_violations(p95s, mcperf_ts, jobs_ts)
    total_slo_violations += slo_violations
    total_len_p95s += len_p95s

    print("============== Average ==============")
    for name in durations:
        print(f"mean({name}): {np.mean(durations[name])}")
        print(f"std({name}): {np.std(durations[name])}")

    print("============== Total time ==============")
    print(f"Run 1: {total_time1}")
    print(f"Run 2: {total_time2}")
    print(f"Run 3: {total_time3}")
    print(f"Mean: {np.mean([total_time1, total_time2, total_time3])}")
    print(f"std: {np.std([total_time1, total_time2, total_time3])}")

    print("============== SLO violations ==============")
    print(f"Total SLO violations: {total_slo_violations}")
    print(f"Total number of latencies: {total_len_p95s}")
    print(f"Total percentage of violations: {total_slo_violations / total_len_p95s * 100}%")
    # add space between subplots
    plt.tight_layout()
    plt.subplots_adjust(hspace=0.35, wspace=0.2)
    # fig.legend(loc='upper left', fancybox=True, shadow=True)

    plt.savefig('plot4_4.svg')

    plt.show()