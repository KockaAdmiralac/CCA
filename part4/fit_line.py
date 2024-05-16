import pandas as pd
from termcolor import colored
import matplotlib.pyplot as plt


def load_cpu_data(path):
    df = pd.read_csv(path, header=None, delim_whitespace=True)
    df.columns = ["timestamp", "mem", "cpu0"]  # "mem", "cpu2", "cpu3"]
    # turn mem, cpu0, cpu1, cpu2, cpu3 columns into float
    for col in df.columns[1:]:
        df[col] = df[col].str.replace("%", "").astype(float)
    # print(df.head())
    return df


def load_qps_data(path):
    df = pd.read_csv(path, delim_whitespace=True)
    df["ts_start"] /= 1000
    df["ts_end"] /= 1000
    # print(df.head())
    return df


def join_cpu_df(cpu_df, qps_df):
    # For each row of cpu_df, find the corresponding row in qps_df and add it to that cpu_df row
    for index, cpu_row in cpu_df.iterrows():
        ts = cpu_row["timestamp"]
        qps_row = qps_df[(qps_df["ts_start"] <= ts) & (qps_df["ts_end"] >= ts)]

        if len(qps_row) > 1:
            print(colored(f"More than one QPS data found for timestamp {ts}", "yellow"))
        elif not qps_row.empty:
            cpu_df.at[index, "QPS"] = qps_row["QPS"].values[0]
            cpu_df.at[index, "target"] = qps_row["target"].values[0]
            cpu_df.at[index, "ts_start"] = qps_row["ts_start"].values[0]
            cpu_df.at[index, "ts_end"] = qps_row["ts_end"].values[0]

    # drow rows with Nan values
    cpu_df = cpu_df.dropna()
    return cpu_df


def load_all_data(cpu_paths, qps_paths):
    dfs = []
    for i, (cpu_path, qps_path) in enumerate(zip(cpu_paths, qps_paths)):
        cpu_df = load_cpu_data(cpu_path)
        qps_df = load_qps_data(qps_path)
        df = join_cpu_df(cpu_df, qps_df)

        df["run"] = i
        dfs.append(df)

    # concatenate all dataframes
    df = pd.concat(dfs)
    return df


def plot_cpu_qps(df):
    # scatter plot of all measurements and the maximum of each target
    df.plot.scatter(x="QPS", y="cpu0", c="run", cmap="Set1")  # , ax=axs[0])
    median_df = df.groupby("target")[["QPS", "cpu0"]].max()
    median_df.plot(x="QPS", y="cpu0", color="black", ax=plt.gca())

    # scatter plot of all measurements and the maximum of each target
    df.plot.scatter(x="target", y="cpu0", c="run", cmap="Set1")  # , ax=axs[0])
    median_df = df.groupby("target")["cpu0"].max()
    median_df.plot(color="black", ax=plt.gca())
    plt.show()


def plot_relative_cpu_time_delta(df):
    # to each row add the maximum cpu usage of all rows with the same QPS
    df["max_cpu"] = df.groupby("QPS")["cpu0"].transform("max")
    df["cpu_ratio"] = df["cpu0"] / df["max_cpu"]

    df.plot.scatter(x="time_delta", y="cpu_ratio")
    plt.xlabel("Time since the start of QPS bucket (s)")
    plt.ylabel("Percentage of max CPU usage in that bucket")

    plt.show()


cpu_paths = [
    "measurements/performance-c1-t2-1.txt",
    "measurements/performance-c1-t2-2.txt",
    "measurements/performance-c1-t2-3.txt",
]
qps_paths = [
    "measurements/mcperf-c1-t2-1.txt",
    "measurements/mcperf-c1-t2-2.txt",
    "measurements/mcperf-c1-t2-3.txt",
]

df = load_all_data(cpu_paths, qps_paths)
df["time_delta"] = df["timestamp"] - df["ts_start"]
print(colored("All data loaded", "green"))
print(df.head())

# plot_cpu_qps(df)
plot_relative_cpu_time_delta(df)
