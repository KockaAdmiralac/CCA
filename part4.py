import datetime
from typing import Any, Iterable, Optional
import docker
from docker.models.containers import Container
import os
import psutil
import sys

time_format = '%Y-%m-%dT%H:%M:%S.%fZ'

class Job:
    def __init__(self, name: str, benchmark: str):
        self.name: str = name
        self.benchmark: str = benchmark

    def status(self) -> str:
        return self.container.attrs['State']['Status']

    def start_time(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.container.attrs['State']['StartedAt'], time_format)

    def end_time(self) -> datetime.datetime:
        if self.status() == 'running':
            return datetime.datetime.now()
        else:
            return datetime.datetime.strptime(self.container.attrs['State']['FinishedAt'], time_format)

    def runtime(self) -> float:
        if self.container is None:
            return 0.0
        return (self.end_time() - self.start_time()).total_seconds()

    def create(self, client: docker.DockerClient, num_threads: int):
        image = f'anakli/cca:{self.benchmark}_{self.name}'
        cmd = f'./run -a run -S {self.benchmark} -p {self.name} -i native -n {num_threads}'
        self.container: Container = client.containers.create(image, cmd, detach=True, name=self.name)

    def start(self, **kwargs):
        self.container.update(**kwargs)
        self.container.start()

    def finish(self, container: Container):
        with open(f'logs/{job.name}.log', 'wb') as logs_file:
            logs_file.write(container.logs())
        container.remove()
        with open('jobs.csv', 'a', encoding='utf-8') as jobs_file:
            jobs_file.write(f'{self.name},{self.start_time().isoformat()},{self.end_time().isoformat()}\n')

# Constants
JOBS = {
    'blackscholes': Job('blackscholes', 'parsec'),
    'canneal': Job('canneal', 'parsec'),
    'dedup': Job('dedup', 'parsec'),
    'ferret': Job('ferret', 'parsec'),
    'freqmine': Job('freqmine', 'parsec'),
    'radix': Job('radix', 'splash2x'),
    'vips': Job('vips', 'parsec')
}

def predict_qps(cpu_percent: float) -> int:
    return 35000

def get_next_job() -> Optional[Job]:
    for job in JOBS.values():
        if job.status == 'not-created':
            return job
    return None

def write_utilization(data: Iterable[Any]):
    with open('utilization.csv', 'a', encoding='utf-8') as utilization_file:
        utilization_file.write(f'{",".join([str(item) for item in data])}\n')

if __name__ == '__main__':
    memcached = psutil.Process(int(sys.argv[1]))
    client = docker.from_env()
    memcached.cpu_affinity([0])
    memcached_cpus = 1
    os.makedirs('logs', exist_ok=True)
    write_utilization(['time', 'cpu0', 'cpu1', 'cpu2', 'cpu3', 'mcpu', 'mem', 'qps'])
    for job in JOBS.values():
        job.create(client, 3)
    
    for job in JOBS.values():
        job.start(cpuset_cpus='1,2,3')

    while True:
        # Obtain environment data
        cpu0_percent, cpu1_percent, cpu2_percent, cpu3_percent = psutil.cpu_percent(percpu=True)
        memcached_cpu_percent = memcached.cpu_percent(1)
        memory_percent = psutil.virtual_memory().percent
        predicted_qps = predict_qps(memcached_cpu_percent)
        now = datetime.datetime.now()

        # Print scheduler status
        print(f'CPU%:           {cpu0_percent:.2f} {cpu1_percent:.2f} {cpu2_percent:.2f} {cpu3_percent:.2f}', flush=True)
        print(f'Memcached CPU%: {memcached_cpu_percent:.2f}', flush=True)
        print(f'MEM%:           {memory_percent:.2f}', flush=True)
        print(f'Predicted QPS:  {predicted_qps:.2f}', flush=True)
        print('Containers:', flush=True)
        for job in JOBS.values():
            print(f'    {job.name}\t{job.status()}\t{job.runtime()}', flush=True)

        # Write utilization data to file
        write_utilization([now.isoformat(), cpu0_percent, cpu1_percent,
            cpu2_percent, cpu3_percent, memcached_cpu_percent, memory_percent,
            predicted_qps])

        # Shrink and grow memcached based on 
        if predicted_qps > 25000 and memcached_cpus == 1:
            print('Giving memcached another CPU', flush=True)
            memcached_cpus = 2
            memcached.cpu_affinity([0, 1])
            for container in client.containers.list():
                container.update(cpuset_cpus='2,3')
        elif predicted_qps < 25000 and memcached_cpus == 2:
            print('Giving containers another CPU', flush=True)
            memcached_cpus = 1
            memcached.cpu_affinity([0])
            for container in client.containers.list():
                container.update(cpuset_cpus='1,2,3')

        # Update job statuses and run new jobs
        # for container in client.containers.list(all=True):
        #     job = JOBS[container.name]
        #     job.status = container.status
        #     if container.status == 'exited':
        #         print(container.name, 'exited', flush=True)
        #         job.finish(container)
        #         next_job = get_next_job()
        #         if next_job is None:
        #             print('Scheduler finished!', flush=True)
        #             sys.exit(0)
        #         print('Now running', next_job.name, flush=True)
        #         cpus = '1,2,3' if memcached_cpus == 1 else '2,3'
        #         print(next_job.start(cpuset_cpus=cpus), flush=True)
        if len([job for job in JOBS.values() if job.status() != 'exited']) == 0:
            print('No more jobs to run!')
            sys.exit(0)
