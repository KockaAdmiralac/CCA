import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from datetime import datetime
import random


def plot_run(jobs_path, memcached_path, run):
    # Read Jobs
    jobs_json = json.load(open(jobs_path))

    jobs_dict = {}
    for job_result in jobs_json["items"]:
        name = job_result["status"]["containerStatuses"][0]["name"]
        name = name.split("-")[1]

        node = job_result["spec"]["nodeSelector"]["cca-project-nodetype"]
        node = node.split("-")[2]

        time_dict = job_result["status"]["containerStatuses"][0]["state"]
        if "terminated" not in time_dict:
            continue

        start_time = time_dict["terminated"]["startedAt"]
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ").timestamp()

        end_time = time_dict["terminated"]["finishedAt"]
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%SZ").timestamp()

        jobs_dict[name] = {
            "start_time": start_time,
            "end_time": end_time,
            "node": node,
        }

    start_time = min([jobs_dict[name]["start_time"] for name in jobs_dict])

    for name in jobs_dict:
        jobs_dict[name]["start_time"] -= start_time
        jobs_dict[name]["end_time"] -= start_time

    # sort jobs by node
    jobs_dict = dict(sorted(jobs_dict.items(), key=lambda item: item[1]["node"]))

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

    # Add cores
    name_to_core = {
        "blackscholes": "2 cores",
        "canneal": "4 cores",
        "dedup": "1 core",
        "ferret": "4 cores",
        "freqmine": "4 cores",
        "radix": "4 cores",
        "vips": "2 cores",
    }
    for name in name_to_core:
        jobs_dict[name]["core"] = name_to_core[name]

    # Read memcached latencies
    df = pd.read_csv(memcached_path, header=0, delim_whitespace=True)

    memcached_start = df["ts_start"] / 1000
    memcached_end = df["ts_end"] / 1000

    memcached_start = memcached_start - start_time - 7200  # time zone difference
    memcached_end = memcached_end - start_time - 7200  # time zone difference
    bar_widths = [end - start for start, end in zip(memcached_start, memcached_end)]

    latencies = df["p95"]

    # Plot
    plt.bar(memcached_start, latencies, width=bar_widths, align="edge")
    # horizontal line
    # plt.axhline(y=1000, color="gray", linestyle="--")
    plt.text(-8, 1010, "SLO", rotation=0, color="gray")

    for i, name in enumerate(jobs_dict):
        plt.vlines(
            x=[
                jobs_dict[name]["start_time"],
                jobs_dict[name]["end_time"],
            ],
            ymin=0,
            ymax=1100 + 100 * i,
            color=jobs_dict[name]["color"],
            linestyle="--",
            linewidths=1,
            label=name,
        )

        # horizontal line between start and end at y=1200
        plt.hlines(
            y=1100 + 100 * i,
            xmin=jobs_dict[name]["start_time"],
            xmax=jobs_dict[name]["end_time"],
            color=jobs_dict[name]["color"],
            linestyle="-",
            linewidths=2,
        )
        # add text on top of horizontal line
        plt.text(
            jobs_dict[name]["start_time"] + 5,
            1100 + 100 * i + 8,
            name + " " + jobs_dict[name]["core"],
            rotation=0,
            color=jobs_dict[name]["color"],
        )

    plt.text(-9, 1620, "node\nc", rotation=0)
    plt.vlines(x=-2, ymin=1590, ymax=1750, color="black", linestyle="-")
    plt.hlines(y=[1590, 1750], xmin=-2, xmax=-1, color="black", linestyle="-")

    plt.text(-9, 1270, "node\nb", rotation=0)
    plt.vlines(x=-2, ymin=1100, ymax=1560, color="black", linestyle="-")
    plt.hlines(y=[1100, 1560], xmin=-2, xmax=-1, color="black", linestyle="-")

    plt.xlim(-10, 130)
    # plt.ylim(0, 1300)

    plt.ylabel("p95 latency (micro seconds)")
    plt.xlabel("time (seconds)")
    plt.yticks([250, 500, 750, 1000])
    # add horizontal lines of grid, dashed lines
    plt.grid(axis="y", linestyle="--")

    # ax title
    plt.title(f"Run {run}")

    # plt.legend(bbox_to_anchor=(1.13, 1))
    # plt.legend(
    #     loc="upper center", bbox_to_anchor=(0.5, 1.05), ncol=4, fancybox=True, shadow=True
    # )


plt.figure(figsize=(10, 15))
plt.subplot(3, 1, 1)
plot_run(
    "part_3_results_group_019/pods_1.json", "part_3_results_group_019/mcperf_1.txt", 1
)

plt.subplot(3, 1, 2)
plot_run(
    "part_3_results_group_019/pods_2.json", "part_3_results_group_019/mcperf_2.txt", 2
)

plt.subplot(3, 1, 3)
plot_run(
    "part_3_results_group_019/pods_3.json", "part_3_results_group_019/mcperf_3.txt", 3
)

plt.savefig("part_3_results_group_019/plot3_1.png")
# plt.show()
