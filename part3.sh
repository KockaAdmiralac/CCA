#!/bin/bash
set -e

mkdir -p measurements/part3

LogTiming() {
    echo "$1: $(date +"%Y-%m-%d %H:%M:%S")" >> measurements/part3/timing.yaml
}

RunCommand() {
    ssh -oStrictHostKeyChecking=no -i cloud-computing "ubuntu@$1" "$2"
}

CopyToVM() {
    scp -oStrictHostKeyChecking=no -i cloud-computing "$1" "ubuntu@$2"
}

CopyFromVM() {
    scp -oStrictHostKeyChecking=no -i cloud-computing "ubuntu@$1" "$2"
}

StartJob() {
    kubectl create -f "part3/$1.yaml"
}

SetupMcperf() {
    CopyToVM make-mcperf.sh "$1:"
    RunCommand "$1" "bash make-mcperf.sh"
}

SetupPerformance() {
    CopyToVM performance.py "$1:"
    RunCommand "$1" "sudo apt-get update; sudo apt-get install tmux python3-pip --yes; sudo python3 -m pip install psutil; tmux new-session -s performance -d 'python3 ~/performance.py > ~/performance.txt 2>&1'"
}

GetPerformanceMeasurements() {
    RunCommand "$1" "tmux kill-session -t performance"
    CopyFromVM "$1:performance.txt" measurements/part3/performance-$2.txt
}

if [ ! -f cloud-computing ]
then
    echo "Generating SSH key..."
    ssh-keygen -t rsa -b 4096 -f cloud-computing -N ''
fi

LogTiming start

if [ "$(kubectl config current-context 2>/dev/null || echo none)" == "part3.k8s.local" ]
then
    echo "Cluster already exists -- not creating"
else
    echo "Creating cluster..."
    source profile.sh
    sed -i "s|gs://<your-gs-bucket>/|$KOPS_STATE_STORE|" part*.yaml
    sed -i "s/<your-cloud-computing-architecture-gcp-project>/$PROJECT/" part*.yaml
    kops create -f part3.yaml
    kops create secret --name part3.k8s.local sshpublickey admin -i cloud-computing.pub
    kops update cluster --name part3.k8s.local --yes --admin
    echo "Validating cluster..."
    kops validate cluster --wait 10m
fi

LogTiming cluster_created
printf '\a'
printf '\a'
printf '\a'

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
kubectl create -f part3/memcached.yaml
kubectl expose pod part3-memcached --name part3-memcached-11211 \
                                   --type LoadBalancer \
                                   --port 11211 \
                                   --protocol TCP

echo "Waiting for Memcached pod to create..."
while [ "$(kubectl get pods -o wide | grep part3-memcached | tr -s ' ' | cut -d' ' -f3)" != "Running" ]
do
    sleep 1
done
MEMCACHED_IP=`kubectl get pods -o wide | grep part3-memcached | tr -s ' ' | cut -d' ' -f6`
wait

LogTiming setup_done

echo "Starting mcperf..."
RunCommand "$CLIENT_AGENT_A_EXTERNAL_IP" "tmux new-session -d '~/memcache-perf/mcperf -T 2 -A'"
RunCommand "$CLIENT_AGENT_B_EXTERNAL_IP" "tmux new-session -d '~/memcache-perf/mcperf -T 4 -A'"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_IP --loadonly"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "tmux new-session -s mcperf -d 'while true; do ~/memcache-perf/mcperf -s $MEMCACHED_IP -a $CLIENT_AGENT_A_INTERNAL_IP -a $CLIENT_AGENT_B_INTERNAL_IP --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5 >> ~/mcperf.txt; done'"

LogTiming jobs_start

echo "Stating dedup, vips, blackscholes and ferret jobs..."
StartJob vips
sleep 30
StartJob ferret
sleep 20
StartJob dedup
StartJob blackscholes
StartJob freqmine
StartJob radix
StartJob canneal

printf '\a'
printf '\a'
printf '\a'
printf '\a'
printf '\a'

dedup_done="no"
radix_done="no"
vips_done="no"
blackscholes_done="no"
# canneal_started="no"
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
        echo "dedup finished"
    fi
    if [ "$radix_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-radix | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        radix_done="yes"
        echo "radix finished"
    fi
    if [ "$vips_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-vips | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        vips_done="yes"
        echo "vips finished"
    fi
    if [ "$blackscholes_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-blackscholes | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        blackscholes_done="yes"
        echo "blackscholes finished"
    fi
    if [ "$canneal_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-canneal | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        canneal_done="yes"
        echo "canneal finished"
    fi
    if [ "$ferret_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-ferret | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        ferret_done="yes"
        echo "ferret finished"
    fi
    if [ "$freqmine_done" == "no" ] && [ "$(echo "$JOB_INFO" | grep part3-freqmine | tr -s ' ' | cut -d' ' -f2)" == "1/1" ]
    then
        freqmine_done="yes"
        echo "freqmine finished"
    fi
    if [ "$dedup_done" == "yes" ] && [ "$radix_done" == "yes" ] && [ "$ferret_done" == "yes" ] && [ "$vips_done" == "yes" ] && [ "$freqmine_done" == "yes" ] && [ "$canneal_done" == "yes" ] && [ "$blackscholes_done" == "yes" ]
    then
        echo "All jobs done!"
        all_done="yes"
    fi
done

LogTiming jobs_done

echo "Retrieving performance measurements..."
GetPerformanceMeasurements "$NODE_A_EXTERNAL_IP" "a" &
GetPerformanceMeasurements "$NODE_B_EXTERNAL_IP" "b" &
GetPerformanceMeasurements "$NODE_C_EXTERNAL_IP" "c" &
kubectl get pods -o json > measurements/part3/results.json
python3 get_time.py measurements/part3/results.json
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "tmux kill-session -t mcperf"
CopyFromVM "$CLIENT_MEASURE_EXTERNAL_IP:mcperf.txt" measurements/part3
wait

LogTiming measurements_retrieved

echo "Deleting cluster..."
kops delete cluster part3.k8s.local --yes

LogTiming cluster_deleted

echo "Done!"
