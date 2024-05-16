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

threads=2
cores=2
run=0

seq_input=$(($cores - 1))
taskset_cpus=$(seq -s, 0 $seq_input)

echo "Rerunning Memcached and performance measurements..."
sed -i "s/-t .*/-t $threads/" memcached.conf
CopyToVM "memcached.conf" "$MEMCACHED_EXTERNAL_IP:~/memcached.conf"
RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo mv ~/memcached.conf /etc/memcached.conf; sudo systemctl restart memcached"
MEMCACHED_PID=`RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo systemctl status memcached | grep 'Main PID:' | tr -s ' ' | cut -d' ' -f4"`
echo "Detected Memcached running on PID $MEMCACHED_PID."
sleep 3
RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo taskset -a -cp $taskset_cpus $MEMCACHED_PID"
(RunCommand "$MEMCACHED_EXTERNAL_IP" "python3 ~/performance_memcached.py $MEMCACHED_PID" | tee "measurements/part4/performance-c$cores-t$threads-$run.txt" &)
