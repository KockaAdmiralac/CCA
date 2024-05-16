import os

path = "measurements"
# iterate through the files in path
for filename in os.listdir(path):
    if filename.startswith("mcperf"):
        # remove all lines that don't start with read
        with open(f"{path}/{filename}", "r") as file:
            lines = file.readlines()

        with open(f"{path}/{filename}", "w") as file:
            for line in lines:
                if line.startswith("read") or line.startswith("#type"):
                    file.write(line)
