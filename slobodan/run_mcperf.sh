source common.sh

NODE_INFO=`kubectl get nodes -o wide`
CLIENT_MEASURE_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-measure | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-agent | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_INTERNAL_IP=`echo "$NODE_INFO" | grep client-agent | tr -s ' ' | cut -d' ' -f6`
MEMCACHED_EXTERNAL_IP=`echo "$NODE_INFO" | grep memcache-server | tr -s ' ' | cut -d' ' -f7`
MEMCACHED_INTERNAL_IP=`echo "$NODE_INFO" | grep memcache-server | tr -s ' ' | cut -d' ' -f6`

echo "Starting mcperf..."
RunCommand "$CLIENT_AGENT_EXTERNAL_IP" "if ! tmux has-session -t mcperf 2>/dev/null; then tmux new-session -s mcperf -d '~/memcache-perf/mcperf -T 16 -A'; fi"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_INTERNAL_IP --loadonly"
RunCommand "$CLIENT_MEASURE_EXTERNAL_IP" "~/memcache-perf/mcperf -s $MEMCACHED_INTERNAL_IP -a $CLIENT_AGENT_INTERNAL_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 5 --scan 5000:125000:5000" | tee "measurements/part4/mcperf-c$cores-t$threads-$run.txt"
RunCommand "$CLIENT_AGENT_EXTERNAL_IP" "tmux kill-session -t mcperf"

