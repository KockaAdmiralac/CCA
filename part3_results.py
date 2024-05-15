import json
from datetime import datetime
from typing import Dict, List
import numpy as np

time_format = "%Y-%m-%dT%H:%M:%SZ"
results: Dict[str, List[float]] = {}
total_times: List[float] = []
for i in range(1, 4):
    starting_times: List[datetime] = []
    completion_times: List[datetime] = []
    with open(f'measurements/final/pods_{i}.json', "r") as file:
        json_file = json.load(file)
        for item in json_file["items"]:
            name = item["status"]["containerStatuses"][0]["name"]
            if str(name) != "part3-memcached":
                results[str(name)] = results.get(str(name), [])
                start_time = datetime.strptime(
                    item["status"]["containerStatuses"][0]["state"]["terminated"][
                        "startedAt"
                    ],
                    time_format,
                )
                completion_time = datetime.strptime(
                    item["status"]["containerStatuses"][0]["state"]["terminated"][
                        "finishedAt"
                    ],
                    time_format,
                )
                results[str(name)].append((completion_time - start_time).total_seconds())
                starting_times.append(start_time)
                completion_times.append(completion_time)

    total_times.append((max(completion_times) - min(starting_times)).total_seconds())

for key, times in results.items():
    print(f'            \\coloredcell{{{key.replace('part3-', '')}}}    & {round(np.mean(times), 2)}s & {round(np.std(times), 2)}s \\\\  \\hline')
print(f'            total time    & {round(np.mean(total_times), 2)}s & {round(np.std(total_times), 2)}s \\\\  \\hline')
