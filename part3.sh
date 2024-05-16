#!/bin/bash
set -e

source common.sh

LogTiming() {
    mkdir -p measurements/part3
    echo "$1: $(date +"%Y-%m-%d %H:%M:%S")" >> measurements/part3/timing.yaml
}

StartJob() {
    kubectl create -f "part3/$1.yaml"
}

SetupPerformance() {
    CopyToVM performance.py "$1:"
    RunCommand "$1" "sudo apt-get update; sudo apt-get install tmux python3-pip --yes; sudo python3 -m pip install psutil; if ! tmux has-session -t performance 2>/dev/null; then tmux new-session -s performance -d 'python3 ~/performance.py > ~/performance.txt 2>&1'; fi" > /dev/null
}

GetPerformanceMeasurements() {
    RunCommand "$1" "tmux kill-session -t performance"
    CopyFromVM "$1:performance.txt" measurements/part3/performance-$2.txt
}

GenerateSSHKey
LogTiming start

CreateKubernetesCluster part3
LogTiming cluster_created
TerminalBell

echo "Obtaining relevant node info..."
NODE_INFO=`kubectl get nodes -o wide`
CLIENT_MEASURE_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-measure | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_A_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-agent-a | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_A_INTERNAL_IP=`echo "$NODE_INFO" | grep client-agent-a | tr -s ' ' | cut -d' ' -f6`
CLIENT_AGENT_B_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-agent-b | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_B_INTERNAL_IP=`echo "$NODE_INFO" | grep client-agent-b | tr -s ' ' | cut -d' ' -f6`
NODE_A_EXTERNAL_IP=`echo "$NODE_INFO" | grep node-a-2core | tr -s ' ' | cut -d' ' -f7`
NODE_B_EXTERNAL_IP=`echo "$NODE_INFO" | grep node-b-4core | tr -s ' ' | cut -d' ' -f7`
NODE_C_EXTERNAL_IP=`echo "$NODE_INFO" | grep node-c-8core | tr -s ' ' | cut -d' ' -f7`

LogTiming node_info

echo "Setting up Memcached, mcperf and performance measurements..."
SetupMcperf "$CLIENT_MEASURE_EXTERNAL_IP" &
SetupMcperf "$CLIENT_AGENT_A_EXTERNAL_IP" &
SetupMcperf "$CLIENT_AGENT_B_EXTERNAL_IP" &
SetupPerformance "$NODE_A_EXTERNAL_IP" &
SetupPerformance "$NODE_B_EXTERNAL_IP" &
SetupPerformance "$NODE_C_EXTERNAL_IP" &
if ! (kubectl get pods -o wide | grep -q part3-memcached)
then
    kubectl create -f part3/memcached.yaml
    if ! (kubectl get services | grep -q part3-memcached-11211)
    then
        kubectl expose pod part3-memcached --name part3-memcached-11211 \
                                           --type LoadBalancer \
                                           --port 11211 \
                                           --protocol TCP
    fi
    echo "Waiting for Memcached pod to create..."
    while [ "$(kubectl get pods -o wide | grep part3-memcached | tr -s ' ' | cut -d' ' -f3)" != "Running" ]
    do
        sleep 1
    done
fi
MEMCACHED_IP=`kubectl get pods -o wide | grep part3-memcached | tr -s ' ' | cut -d' ' -f6`

echo "Pre-pulling images..."
if ! (kubectl get daemonsets | grep -q prepuller)
then
    kubectl create -f part3/prepuller.yaml
fi
while [ "$(kubectl get pods -o wide | grep part3-prepuller | tr -s ' ' | cut -d' ' -f3 | tr -d $'\n')" != "RunningRunningRunning" ]
do
    sleep 1
done
wait

LogTiming setup_done

echo "Starting mcperf..."
RunCommand "$CLIENT_AGENT_A_EXTERNAL_IP" "if ! tmux has-session -t mcperf 2>/dev/null; then tmux new-session -s mcperf -d '~/memcache-perf/mcperf -T 2 -A'; fi"
RunCommand "$CLIENT_AGENT_B_EXTERNAL_IP" "if ! tmux has-session -t mcperf 2>/dev/null; then tmux new-session -s mcperf -d '~/memcache-perf/mcperf -T 4 -A'; fi"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_IP --loadonly"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "if ! tmux has-session -t mcperf 2>/dev/null; then tmux new-session -s mcperf -d 'while true; do ~/memcache-perf/mcperf -s $MEMCACHED_IP -a $CLIENT_AGENT_A_INTERNAL_IP -a $CLIENT_AGENT_B_INTERNAL_IP --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5 > ~/mcperf.txt 2>&1; done'; fi"

LogTiming jobs_start

echo "Starting jobs..."
StartJob vips
StartJob ferret
StartJob dedup
StartJob blackscholes
StartJob freqmine
StartJob radix
StartJob canneal

TerminalBell

dedup_done="no"
radix_done="no"
vips_done="no"
blackscholes_done="no"
canneal_done="no"
ferret_done="no"
freqmine_done="no"
all_done="no"
while [ "$all_done" != "yes" ]
do
    sleep 1
    PODS_INFO=`kubectl get pods -o wide`
    clear
    echo "====================================================================="
    echo "$PODS_INFO"
    JOB_INFO=`kubectl get jobs`
    if [ "$dedup_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-dedup | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        dedup_done="yes"
    fi
    if [ "$radix_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-radix | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        radix_done="yes"
    fi
    if [ "$vips_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-vips | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        vips_done="yes"
    fi
    if [ "$blackscholes_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-blackscholes | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        blackscholes_done="yes"
    fi
    if [ "$canneal_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-canneal | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        canneal_done="yes"
    fi
    if [ "$ferret_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-ferret | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        ferret_done="yes"
    fi
    if [ "$freqmine_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-freqmine | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        freqmine_done="yes"
    fi
    if [ "$dedup_done" == "yes" ] && [ "$radix_done" == "yes" ] && [ "$ferret_done" == "yes" ] && [ "$vips_done" == "yes" ] && [ "$freqmine_done" == "yes" ] && [ "$canneal_done" == "yes" ] && [ "$blackscholes_done" == "yes" ]
    then
        all_done="yes"
    fi
done

echo "All jobs done!"

LogTiming jobs_done

echo "Retrieving performance measurements..."
kubectl delete daemonset part3-prepuller
kubectl get pods | grep part3-prepuller | tr -s ' ' | cut -d' ' -f1 | xargs kubectl delete pod
GetPerformanceMeasurements "$NODE_A_EXTERNAL_IP" "a" &
GetPerformanceMeasurements "$NODE_B_EXTERNAL_IP" "b" &
GetPerformanceMeasurements "$NODE_C_EXTERNAL_IP" "c" &
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "tmux kill-session -t mcperf" &
RunCommand "$CLIENT_AGENT_A_EXTERNAL_IP" "tmux kill-session -t mcperf" &
RunCommand "$CLIENT_AGENT_B_EXTERNAL_IP" "tmux kill-session -t mcperf" &
CopyFromVM "$CLIENT_MEASURE_EXTERNAL_IP:mcperf.txt" measurements/part3 &
kubectl get pods -o json > measurements/part3/results.json
wait
python3 get_time.py measurements/part3/results.json

LogTiming measurements_retrieved

read -n1 -p 'Delete cluster? [y/N] ' confirmation
if [ "$confirmation" == "y" ] || [ "$confirmation" == "Y" ]
then
    echo "Deleting cluster..."
    kops delete cluster part3.k8s.local --yes
else
    echo "Deleting all pods..."
    kubectl delete pods --all
    kubectl delete jobs --all
    kubectl delete service part3-memcached-11211
fi

LogTiming cluster_deleted

echo "Done!"
