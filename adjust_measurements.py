import datetime
from typing import List
import pandas as pd
import sys
from scheduler_logger import SchedulerLogger, Job

utilization = pd.read_csv(f'{sys.argv[1]}/utilization.csv')
jobs = pd.read_csv(f'{sys.argv[1]}/jobs.csv', names=['job', 'start_time', 'end_time'], header=None)
logger = SchedulerLogger(int(sys.argv[2]), str(utilization['time'][0]))
time_format = '%Y-%m-%dT%H:%M:%S.%f'

mcperf_start = datetime.datetime.now()
mcperf_end = datetime.datetime.now()
with open(f'{sys.argv[1]}/mcperf.txt', 'r', encoding='utf-8') as mcperf_file:
    for line in mcperf_file:
        if line.startswith('Timestamp start: '):
            mcperf_start = datetime.datetime.fromtimestamp(int(line.replace('Timestamp start: ', '')) / 1000)
        if line.startswith('Timestamp end: '):
            mcperf_end = datetime.datetime.fromtimestamp(int(line.replace('Timestamp end: ', '')) / 1000)
logger.job_start(mcperf_start.strftime(time_format), Job.MEMCACHED, ['0', '1'], 2)

def parse_date_string(date_string: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_string, time_format)

def get_unix_timestamp(date: datetime.datetime) -> int:
    return int(date.timestamp() * 1000)

def get_threads_for_job(job: str) -> int:
    if job == 'radix' or job == 'dedup': return 1
    if job == 'blackscholes' or job == 'vips': return 2
    return 3

def get_init_cpuset_for_job(job: str) -> List[str]:
    if job == 'radix' or job == 'dedup': return ['1']
    if job == 'blackscholes': return ['2']
    if job == 'vips': return ['3']
    return ['2', '3']

def get_cores_for_job(job: str, event) -> List[int]:
    cores = []
    if job in str(event.jobs0): cores.append(0)
    if job in str(event.jobs1): cores.append(1)
    if job in str(event.jobs2): cores.append(2)
    if job in str(event.jobs3): cores.append(3)
    return cores

JOBS = {}

prev_time = 0
for _, event in utilization.iterrows():
    curr_time = get_unix_timestamp(parse_date_string(event.time))
    for _, job in jobs.iterrows():
        job_type = Job(job.job)
        start_time = parse_date_string(job.start_time)
        end_time = parse_date_string(job.end_time)
        job_started = prev_time < get_unix_timestamp(start_time) < curr_time
        job_ended = prev_time < get_unix_timestamp(end_time) < curr_time
        if job_started:
            logger.job_start(job.start_time, job_type, get_init_cpuset_for_job(job.job), get_threads_for_job(job.job))
            JOBS[job.job] = {
                'cores': [int(core) for core in get_init_cpuset_for_job(job.job)]
            }
        if job.job in JOBS:
            curr_cores = get_cores_for_job(job.job, event)
            if JOBS[job.job]['cores'] != curr_cores and not job_ended:
                if len(curr_cores) == 0:
                    logger.job_pause(event.time, job_type)
                elif len(JOBS[job.job]['cores']) == 0:
                    logger.job_unpause(event.time, job_type)
                else:
                    logger.update_cores(event.time, job_type, [str(core) for core in curr_cores])
                JOBS[job.job]['cores'] = curr_cores
        if job_ended:
            logger.job_end(job.end_time, job_type)
    prev_time = curr_time

logger.job_end(mcperf_end.strftime(time_format), Job.MEMCACHED)
logger.end(str(utilization['time'][len(utilization) - 1]))
