#!/bin/bash
set -e

KillPreviousMcperf() {
    RunCommand "$1" "if tmux has-session -t mcperf 2>/dev/null; then tmux kill-session -t mcperf; fi"
}

source common.sh
mkdir -p measurements/part4
GenerateSSHKey
CreateKubernetesCluster part4
TerminalBell

echo "Obtaining relevant node info..."
NODE_INFO=`kubectl get nodes -o wide`
CLIENT_MEASURE_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-measure | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-agent | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_INTERNAL_IP=`echo "$NODE_INFO" | grep client-agent | tr -s ' ' | cut -d' ' -f6`
MEMCACHED_EXTERNAL_IP=`echo "$NODE_INFO" | grep memcache-server | tr -s ' ' | cut -d' ' -f7`
MEMCACHED_INTERNAL_IP=`echo "$NODE_INFO" | grep memcache-server | tr -s ' ' | cut -d' ' -f6`

echo "Setting up tools..."
SetupMcperf "$CLIENT_MEASURE_EXTERNAL_IP" &
SetupMcperf "$CLIENT_AGENT_EXTERNAL_IP" &
RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo apt-get update; sudo apt-get install -y tmux python3-pip memcached libmemcached-tools docker.io; sudo python3 -m pip install psutil docker; sudo groupadd -f docker; sudo usermod -aG docker ubuntu; sudo bash -c 'docker kill \$(docker ps -q) || true; docker container prune -f'; sudo rm -rf ~/logs ~/utilization.csv ~/jobs.csv" > /dev/null
for job in blackscholes canneal dedup ferret freqmine radix vips
do
    if [ "$job" == "radix" ]
    then
        RunCommand "$MEMCACHED_EXTERNAL_IP" "docker pull anakli/cca:splash2x_radix > /dev/null" &
    else
        RunCommand "$MEMCACHED_EXTERNAL_IP" "docker pull anakli/cca:parsec_$job > /dev/null" &
    fi
done
wait

sed -i 's/-t .*/-t 2/' memcached.conf
CopyToVM memcached.conf "$MEMCACHED_EXTERNAL_IP:~/memcached.conf"
RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo mv ~/memcached.conf /etc/memcached.conf; sudo systemctl restart memcached"
MEMCACHED_PID=`RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo systemctl status memcached | grep 'Main PID:' | tr -s ' ' | cut -d' ' -f4"`
echo "Detected Memcached running on PID $MEMCACHED_PID."

echo "Starting mcperf..."
KillPreviousMcperf "$CLIENT_AGENT_EXTERNAL_IP"
KillPreviousMcperf "$CLIENT_MEASURE_EXTERNAL_IP"
RunCommand "$CLIENT_AGENT_EXTERNAL_IP" "tmux new-session -s mcperf -d '~/memcache-perf/mcperf -T 16 -A'"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_INTERNAL_IP --loadonly; tmux new-session -s mcperf -d '~/memcache-perf/mcperf -s $MEMCACHED_INTERNAL_IP -a $CLIENT_AGENT_INTERNAL_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 780 --qps_interval 10 --qps_min 5000 --qps_max 100000 --qps_seed 3274 > ~/mcperf.txt 2>&1'"

CopyToVM part4.py "$MEMCACHED_EXTERNAL_IP:~/scheduler.py"
RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo python3 ~/scheduler.py $MEMCACHED_PID"

echo "Waiting for mcperf to finish..."
while RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "tmux has-session -t mcperf 2>/dev/null"
do
    sleep 1
done
RunCommand "$CLIENT_AGENT_EXTERNAL_IP" "tmux kill-session -t mcperf"
CopyFromVM "$MEMCACHED_EXTERNAL_IP:~/jobs.csv" measurements/part4
CopyFromVM "$MEMCACHED_EXTERNAL_IP:~/utilization.csv" measurements/part4
CopyFromVM "$MEMCACHED_EXTERNAL_IP:~/logs/*.log" measurements/part4
CopyFromVM "$CLIENT_MEASURE_EXTERNAL_IP:~/mcperf.txt" measurements/part4

# echo "Deleting cluster..."
# DeleteKubernetesCluster part4
