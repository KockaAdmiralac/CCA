import datetime
from enum import IntEnum
from typing import Any, Iterable, List, Optional
import docker
from docker.models.containers import Container
import os
import psutil
import sys

time_format = '%Y-%m-%dT%H:%M:%S.%f'

class Job:
    def __init__(self, name: str, benchmark: str):
        self.name: str = name
        self.benchmark: str = benchmark
        self.cpus: List[int] = []
        self.finished = False

    def status(self) -> str:
        return self.container.attrs['State']['Status']

    def start_time(self) -> datetime.datetime:
        if self.status() != 'running' and self.status() != 'exited':
            return datetime.datetime.now()
        else:
            return datetime.datetime.strptime(self.container.attrs['State']['StartedAt'][:-4], time_format)

    def end_time(self) -> datetime.datetime:
        if self.status() != 'exited':
            return datetime.datetime.now()
        else:
            return datetime.datetime.strptime(self.container.attrs['State']['FinishedAt'][:-4], time_format)

    def runtime(self) -> float:
        if self.container is None or self.status() not in ('running', 'exited'):
            return 0.0
        return (self.end_time() - self.start_time()).total_seconds()

    def create(self, client: docker.DockerClient, num_threads: int):
        image = f'anakli/cca:{self.benchmark}_{self.name}'
        cmd = f'./run -a run -S {self.benchmark} -p {self.name} -i native -n {num_threads}'
        self.container: Container = client.containers.create(image, cmd, detach=True, name=self.name)

    def get_cpus(self) -> List[int]:
        if self.status() == 'running':
            return self.cpus
        return []

    def set_cpus(self, cpus: List[int], cpu_usage: Optional[float] = None):
        self.cpus = cpus
        self.container.update(cpuset_cpus=','.join([str(cpu) for cpu in cpus]),
            cpu_period=100000,
            cpu_quota=int((cpu_usage if cpu_usage is not None else len(cpus)) * 100000))

    def start(self):
        self.container.start()
        self.container.reload()

    def pause(self):
        self.container.pause()
        self.container.reload()

    def unpause(self):
        self.container.unpause()
        self.container.reload()

    def finish(self):
        self.container.reload()
        with open(f'logs/{job.name}.log', 'wb') as logs_file:
            logs_file.write(self.container.logs())
        with open('jobs.csv', 'a', encoding='utf-8') as jobs_file:
            jobs_file.write(f'{self.name},{self.start_time().isoformat()},{self.end_time().isoformat()}\n')
        self.container.remove()

    def update(self):
        self.container.reload()

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

class LoadLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2

class Strategy1State(IntEnum):
    INIT = 0
    BLACKSCHOLES_VIPS = 1
    BLACKSCHOLES_CANNEAL = 2
    VIPS_CANNEAL = 3
    CANNEAL = 4
    FERRET = 5
    FREQMINE = 6
    FINISH = 7

class Strategy1:
    def __init__(self):
        self.state = Strategy1State.INIT

    def _get_current_mini_job(self) -> Optional[Job]:
        if JOBS['radix'].status() != 'exited':
            return JOBS['radix']
        elif JOBS['dedup'].status() != 'exited':
            return JOBS['dedup']
        else:
            return None

    def get_jobs_to_run(self) -> List[Job]:
        next_mini_job = self._get_current_mini_job()
        next_mini_job_arr = [next_mini_job] if next_mini_job is not None else []
        if self.state == Strategy1State.INIT:
            self.state = Strategy1State.BLACKSCHOLES_VIPS
            return [JOBS['blackscholes'], JOBS['vips'], JOBS['radix']]
        elif self.state == Strategy1State.BLACKSCHOLES_VIPS:
            blackscholes_running = JOBS['blackscholes'].status() == 'running'
            vips_running = JOBS['vips'].status() == 'running'
            if blackscholes_running and vips_running:
                # radix or dedup terminated
                return next_mini_job_arr
            elif blackscholes_running:
                # vips terminated
                self.state = Strategy1State.BLACKSCHOLES_CANNEAL
            elif vips_running:
                # blackscholes terminated
                self.state = Strategy1State.VIPS_CANNEAL
            else:
                # both terminated (somehow)
                self.state = Strategy1State.CANNEAL
            return [JOBS['canneal']]
        elif self.state == Strategy1State.BLACKSCHOLES_CANNEAL or self.state == Strategy1State.VIPS_CANNEAL:
            # There is no way that canneal terminated before either of those
            self.state = Strategy1State.CANNEAL
            return []
        elif self.state == Strategy1State.CANNEAL:
            if JOBS['canneal'].status() == 'exited':
                # canneal terminated
                self.state = Strategy1State.FERRET
                return [JOBS['ferret']]
            return next_mini_job_arr
        elif self.state == Strategy1State.FERRET:
            if JOBS['ferret'].status() == 'exited':
                # ferret terminated
                self.state = Strategy1State.FREQMINE
                return [JOBS['freqmine']]
            return next_mini_job_arr
        elif self.state == Strategy1State.FREQMINE:
            if JOBS['freqmine'].status() == 'exited':
                # freqmine terminated, no new jobs to run
                self.state = Strategy1State.FINISH
                return []
            return next_mini_job_arr
        return []

    def get_threads_for_job(self, job: Job) -> int:
        if job.name == 'radix' or job.name == 'dedup': return 1
        if job.name == 'blackscholes' or job.name == 'vips': return 2
        return 3

    def get_init_cpuset_for_job(self, job: Job) -> List[int]:
        if job.name == 'radix' or job.name == 'dedup': return [1]
        if job.name == 'blackscholes': return [2]
        if job.name == 'vips': return [3]
        return [2, 3]

    def update_load_level(self, load_level: LoadLevel, memcached: psutil.Process):
        if load_level == LoadLevel.LOW:
            memcached.cpu_affinity([0])
        else:
            memcached.cpu_affinity([0, 1])
        if load_level == LoadLevel.LOW or load_level == LoadLevel.MEDIUM:
            mini_job = self._get_current_mini_job()
            cpu1_usage = 1 if load_level == LoadLevel.LOW else 0.25
            if mini_job is None:
                if self.state == Strategy1State.BLACKSCHOLES_VIPS:
                    JOBS['blackscholes'].set_cpus([1, 2], 1 + cpu1_usage)
                    JOBS['vips'].set_cpus([2, 3])
                elif self.state == Strategy1State.BLACKSCHOLES_CANNEAL:
                    JOBS['blackscholes'].set_cpus([1, 2], 1 + cpu1_usage)
                    JOBS['canneal'].set_cpus([3])
                elif self.state == Strategy1State.VIPS_CANNEAL:
                    JOBS['vips'].set_cpus([2, 3])
                    JOBS['canneal'].set_cpus([1], cpu1_usage)
                elif self.state == Strategy1State.CANNEAL:
                    JOBS['canneal'].set_cpus([1, 2, 3], 2 + cpu1_usage)
                elif self.state == Strategy1State.FERRET:
                    JOBS['ferret'].set_cpus([1, 2, 3], 2 + cpu1_usage)
                elif self.state == Strategy1State.FREQMINE:
                    JOBS['freqmine'].set_cpus([1, 2, 3], 2 + cpu1_usage)
            else:
                mini_job.set_cpus([1], cpu1_usage)
                if self.state == Strategy1State.BLACKSCHOLES_VIPS:
                    JOBS['blackscholes'].set_cpus([2])
                    JOBS['vips'].set_cpus([3])
                elif self.state == Strategy1State.BLACKSCHOLES_CANNEAL:
                    JOBS['blackscholes'].set_cpus([2])
                    JOBS['canneal'].set_cpus([3])
                elif self.state == Strategy1State.VIPS_CANNEAL:
                    JOBS['vips'].set_cpus([3])
                    JOBS['canneal'].set_cpus([2])
                elif self.state == Strategy1State.CANNEAL:
                    JOBS['canneal'].set_cpus([2, 3])
                elif self.state == Strategy1State.FERRET:
                    JOBS['ferret'].set_cpus([2, 3])
                elif self.state == Strategy1State.FREQMINE:
                    JOBS['freqmine'].set_cpus([2, 3])
                else:
                    mini_job.set_cpus([1, 2, 3], 2 + cpu1_usage)
                if mini_job.status() == 'paused':
                    mini_job.unpause()
        else:
            mini_job = self._get_current_mini_job()
            if mini_job is not None and self.state != Strategy1State.FINISH and mini_job.status() == 'running':
                mini_job.pause()
            if self.state == Strategy1State.BLACKSCHOLES_VIPS:
                JOBS['blackscholes'].set_cpus([2])
                JOBS['vips'].set_cpus([3])
            elif self.state == Strategy1State.BLACKSCHOLES_CANNEAL:
                JOBS['blackscholes'].set_cpus([2])
                JOBS['canneal'].set_cpus([3])
            elif self.state == Strategy1State.VIPS_CANNEAL:
                JOBS['vips'].set_cpus([3])
                JOBS['canneal'].set_cpus([2])
            elif self.state == Strategy1State.CANNEAL:
                JOBS['canneal'].set_cpus([2, 3])
            elif self.state == Strategy1State.FERRET:
                JOBS['ferret'].set_cpus([2, 3])
            elif self.state == Strategy1State.FREQMINE:
                JOBS['freqmine'].set_cpus([2, 3])
            elif mini_job is not None:
                mini_job.set_cpus([2, 3])

    def get_new_load_level(self, predicted_qps: float, load_level: LoadLevel) -> LoadLevel:
        if predicted_qps < 25000:
            return LoadLevel.LOW
        elif predicted_qps < 30000:
            return LoadLevel.MEDIUM
        else:
            return LoadLevel.HIGH

    def print_debug(self):
        print('Strategy state:  ', self.state, flush=True)

def predict_qps_from_cpu(cpu_percent: float) -> float:
    return 585.58444342 * cpu_percent - 822.4653955572503

def predict_qps_from_net(net: float) -> float:
    return 0.99665492 * net - 846.6694402145367

def get_next_job() -> Optional[Job]:
    for job in JOBS.values():
        if job.status == 'not-created':
            return job
    return None

def write_utilization(data: Iterable[Any]):
    with open('utilization.csv', 'a', encoding='utf-8') as utilization_file:
        utilization_file.write(f'{",".join([str(item) for item in data])}\n')

def run_new_jobs(strategy):
    for new_job in strategy.get_jobs_to_run():
        print('Now running', new_job.name, flush=True)
        new_job.set_cpus(strategy.get_init_cpuset_for_job(new_job))
        new_job.start()

if __name__ == '__main__':
    memcached = psutil.Process(int(sys.argv[1]))
    client = docker.from_env()
    load_level = LoadLevel.LOW
    last_net_counter = psutil.net_io_counters().packets_recv
    strategy = Strategy1()
    os.makedirs('logs', exist_ok=True)
    write_utilization(['time', 'cpu0', 'cpu1', 'cpu2', 'cpu3', 'mcpu', 'mem',
        'qps', 'jobs0', 'jobs1', 'jobs2', 'jobs3'])
    for job in JOBS.values():
        job.create(client, strategy.get_threads_for_job(job))

    run_new_jobs(strategy)
    strategy.update_load_level(load_level, memcached)
    start_time = datetime.datetime.now()
    last_time = start_time

    while True:
        # Obtain environment data
        memcached_cpu_percent = max([memcached.cpu_percent(0.25) for i in range(4)])
        cpu0_percent, cpu1_percent, cpu2_percent, cpu3_percent = psutil.cpu_percent(percpu=True)
        memory_percent = psutil.virtual_memory().percent
        net_counter = psutil.net_io_counters().packets_recv
        now = datetime.datetime.now()
        elapsed_time_since_last_check = now - last_time
        elapsed_time_since_start = now - start_time
        last_time = now
        received_packets_per_second = (net_counter - last_net_counter) / elapsed_time_since_last_check.total_seconds()
        last_net_counter = net_counter
        predicted_qps = predict_qps_from_net(received_packets_per_second)

        # Print scheduler status
        print('===============================================================')
        print(f'CPU%:             {cpu0_percent:.2f} {cpu1_percent:.2f} {cpu2_percent:.2f} {cpu3_percent:.2f}', flush=True)
        print(f'Memcached CPU%:   {memcached_cpu_percent:.2f}', flush=True)
        print(f'Received packets: {received_packets_per_second}')
        print(f'MEM%:             {memory_percent:.2f}', flush=True)
        print(f'Predicted QPS:    {predicted_qps:.2f}', flush=True)
        print('Load level:      ', load_level, flush=True)
        print('Elapsed time:    ', elapsed_time_since_start, flush=True)
        strategy.print_debug()
        print('Containers:', flush=True)
        cpus: List[List[str]] = [[], [], [], []]
        for job in JOBS.values():
            job.update()
            print(f'    {job.name}\t{job.status()}\t{job.runtime():.2f}\t{job.get_cpus()}', flush=True)
            for cpu in job.get_cpus():
                cpus[cpu].append(job.name)

        # Write utilization data to file
        write_utilization([now.isoformat(), cpu0_percent, cpu1_percent,
            cpu2_percent, cpu3_percent, memcached_cpu_percent, memory_percent,
            predicted_qps, *['|'.join(cpu) for cpu in cpus]])

        # Shrink and grow memcached based on the current load
        new_load_level = strategy.get_new_load_level(predicted_qps, load_level)
        if load_level != new_load_level:
            print('Updating load level from', load_level, 'to', new_load_level, flush=True)
            strategy.update_load_level(new_load_level, memcached)
            load_level = new_load_level

        any_job_finished = False
        for job in JOBS.values():
            if job.status() == 'exited' and not job.finished:
                print('Job', job.name, 'exited', flush=True)
                job.finished = True
                any_job_finished = True
        if any_job_finished:
            run_new_jobs(strategy)
            strategy.update_load_level(load_level, memcached)

        if len([job for job in JOBS.values() if job.status() != 'exited']) == 0:
            print('No more jobs to run!', flush=True)
            for job in JOBS.values():
                job.finish()
            memcached.cpu_affinity([0, 1])
            sys.exit(0)
