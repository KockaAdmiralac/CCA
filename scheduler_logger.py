from datetime import datetime
from enum import Enum
import urllib.parse


LOG_STRING = "{timestamp} {event} {job_name} {args}"

class Job(Enum):
    SCHEDULER = "scheduler"
    MEMCACHED = "memcached"
    BLACKSCHOLES = "blackscholes"
    CANNEAL = "canneal"
    DEDUP = "dedup"
    FERRET = "ferret"
    FREQMINE = "freqmine"
    RADIX = "radix"
    VIPS = "vips"


class SchedulerLogger:
    def __init__(self, i: int, start_date: str):
        self.file = open(f"jobs_{i}.txt", "w")
        self._log("start", start_date, Job.SCHEDULER)

    def _log(self, start_date: str, event: str, job_name: Job, args: str = "") -> None:
        self.file.write(
            LOG_STRING.format(timestamp=start_date, event=event, job_name=job_name.value,
                              args=args).strip() + "\n")

    def job_start(self, start_date: str, job: Job, initial_cores: list[str], initial_threads: int) -> None:
        assert job != Job.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("start", start_date, job, "["+(",".join(str(i) for i in initial_cores))+"] "+str(initial_threads))

    def job_end(self, start_date: str, job: Job) -> None:
        assert job != Job.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("end", start_date, job)

    def update_cores(self, start_date: str, job: Job, cores: list[str]) -> None:
        assert job != Job.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("update_cores", start_date, job, "["+(",".join(str(i) for i in cores))+"]")

    def job_pause(self, start_date: str, job: Job) -> None:
        assert job != Job.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("pause", start_date, job)

    def job_unpause(self, start_date: str, job: Job) -> None:
        assert job != Job.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("unpause", start_date, job)

    def custom_event(self, start_date: str, job:Job, comment: str):
        self._log("custom", start_date, job, urllib.parse.quote_plus(comment))

    def end(self, start_date: str) -> None:
        self._log("end", start_date, Job.SCHEDULER)
        self.file.flush()
        self.file.close()
