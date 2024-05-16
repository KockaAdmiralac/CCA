#!/bin/bash
set -e

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
CopyToVM performance_memcached.py "$MEMCACHED_EXTERNAL_IP:"
RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo apt-get update; sudo apt-get install -y tmux python3-pip memcached libmemcached-tools; sudo python3 -m pip install psutil" > /dev/null
wait

for threads in 1 2
do
    for cores in 1 2
    do
        seq_input=$(($cores - 1))
        taskset_cpus=$(seq -s, 0 $seq_input)

        for run in 1 2 3
        do
            echo "Rerunning Memcached and performance measurements..."
            sed -i "s/-t .*/-t $threads/" memcached.conf
            CopyToVM "memcached.conf" "$MEMCACHED_EXTERNAL_IP:~/memcached.conf"
            RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo mv ~/memcached.conf /etc/memcached.conf; sudo systemctl restart memcached"
            MEMCACHED_PID=`RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo systemctl status memcached | grep 'Main PID:' | tr -s ' ' | cut -d' ' -f4"`
            echo "Detected Memcached running on PID $MEMCACHED_PID."
            RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo taskset -a -cp $taskset_cpus $MEMCACHED_PID"
            (RunCommand "$MEMCACHED_EXTERNAL_IP" "python3 ~/performance_memcached.py $MEMCACHED_PID" | tee "measurements/part4/performance-c$cores-t$threads-$run.txt" &)

            echo "Starting mcperf..."
            RunCommand "$CLIENT_AGENT_EXTERNAL_IP" "if ! tmux has-session -t mcperf 2>/dev/null; then tmux new-session -s mcperf -d '~/memcache-perf/mcperf -T 16 -A'; fi"
            RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_INTERNAL_IP --loadonly"
            RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_INTERNAL_IP -a $CLIENT_AGENT_INTERNAL_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 5 --scan 5000:125000:5000" | tee "measurements/part4/mcperf-c$cores-t$threads-$run.txt"
            RunCommand "$CLIENT_AGENT_EXTERNAL_IP" "tmux kill-session -t mcperf"
        done
    done
done

echo "Deleting cluster..."
DeleteKubernetesCluster part4
