source common.sh

NODE_INFO=`kubectl get nodes -o wide`
CLIENT_MEASURE_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-measure | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_EXTERNAL_IP=`echo "$NODE_INFO" | grep client-agent | tr -s ' ' | cut -d' ' -f7`
CLIENT_AGENT_INTERNAL_IP=`echo "$NODE_INFO" | grep client-agent | tr -s ' ' | cut -d' ' -f6`
MEMCACHED_EXTERNAL_IP=`echo "$NODE_INFO" | grep memcache-server | tr -s ' ' | cut -d' ' -f7`
MEMCACHED_INTERNAL_IP=`echo "$NODE_INFO" | grep memcache-server | tr -s ' ' | cut -d' ' -f6`

# Install Docker
# RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo apt  install docker.io"
# echo "Installed Docker on Memcached server."

# Kill all running containers
all_containers=$(RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo docker ps -q")
all_containers=$(echo $all_containers | tr '\n' ' ')
echo "Running containers: $all_containers"
if [ ! -z "$all_containers" ]; then
    RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo docker kill $all_containers"
fi
echo "Killed all running containers."

all_containers=$(RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo docker ps -q")
echo "Running containers: $all_containers"

exit 0

jobs=( "blackscholes" "canneal" "dedup" "ferret" "freqmine" "radix" "vips")
images=("anakli/cca:parsec_blackscholes" "anakli/cca:parsec_canneal" "anakli/cca:parsec_dedup" "anakli/cca:parsec_ferret" "anakli/cca:parsec_freqmine" "anakli/cca:splash2x_radix" "anakli/cca:parsec_vips")

# run all jobs
for i in "${!jobs[@]}"; do
    job=${jobs[$i]}
    image=${images[$i]}
    RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo docker run --cpuset-cpus="2,3" -d --rm --name $job $image ./run -a run -S parsec -p $job -i native -n 2"
done

sleep 1
start_time=$(date +%s)
while [ $(RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo docker ps -q | wc -l") -gt 0 ]; do
    out=$(RunCommand "$MEMCACHED_EXTERNAL_IP" "sudo docker ps --format "{{.Names}}"")
    clear
    echo "$out"
    
    # print total time
    current_time=$(date +%s)
    elapsed_time=$(($current_time - $start_time))
    echo "Total time elapsed: $elapsed_time seconds"

    sleep 5 # Wait for 5 seconds before checking again
done

echo "No containers are running."