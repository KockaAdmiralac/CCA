import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

mcperf_start = 1715940983644 / 1000
mcperf_end = 1715941584255 / 1000
# print(pd.to_datetime(mcperf_start, unit="ms"))
# print(pd.to_datetime(mcperf_end, unit="ms"))
mcperf_df = pd.read_csv("mcperf.txt", sep="\s+")
times = np.linspace(mcperf_start, mcperf_end, num=len(mcperf_df))
mcperf_df["time"] = times
mcperf_df["time"] = mcperf_df["time"].astype(int)
mcperf_df["time"] = mcperf_df["time"] - mcperf_start
print(mcperf_df.head())

util_df = pd.read_csv("utilization.csv")
# convert time in util_df from 2024-05-17T10:16:25.310071 to ms format
util_df["time"] = pd.to_datetime(util_df["time"])
util_df["time"] = util_df["time"].dt.strftime("%s")
util_df["time"] = pd.to_numeric(util_df["time"]) + 7200
util_df["time"] -= mcperf_start
# # print time in readable format
# util_df["time"] = pd.to_datetime(util_df["time"], unit="ms")
# # increment by 2 hours to match the time in mcperf_df
# util_df["time"] = util_df["time"] + pd.Timedelta(hours=2)
print(util_df.head(20))

print(mcperf_df.columns)
# mcperf_df.plot(x="time", y="target")
# step function for target
plt.step(mcperf_df["time"], mcperf_df["target"], where="pre", label="target")

util_df.plot(x="time", y="qps", ax=plt.gca())
plt.show()

# print(len(util_df))
# print(len(util_df[util_df["time"] >= mcperf_start]))
# print(len(util_df[util_df["time"] <= mcperf_end]))
