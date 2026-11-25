"""
Author: Bart Sjerps
Last modified: 2026-11-25
Purpose: In-memory job registry for Dockhand deploy, stop, and restart actions.
The Dockhand calls run on a background thread; the UI polls /api/jobs.
"""

import os
import threading
import time
import uuid
from collections import deque

JOB_TIMEOUT = int(os.environ.get("DEPLOYER_JOB_TIMEOUT", "1800"))


class Job:
    def __init__(self, project, env_id, env_name, action, description):
        self.id = uuid.uuid4().hex[:12]
        self.project = project
        self.env_id = env_id
        self.env_name = env_name
        self.action = action
        self.description = description
        self.status = "running"
        self.exit_code = None
        self.output = deque(maxlen=4000)
        self.started = time.time()
        self.finished = None
        self.cancel = False

    def to_dict(self, tail=400):
        return {
            "id": self.id,
            "project": self.project,
            "host": self.env_name,
            "action": self.action,
            "description": self.description,
            "status": self.status,
            "exit_code": self.exit_code,
            "started": self.started,
            "finished": self.finished,
            "output": list(self.output)[-tail:],
        }


class JobManager:
    """One running Dockhand operation per project per environment."""

    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()
        threading.Thread(target=self._watchdog, daemon=True).start()

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def running_for(self, project, env_id):
        with self._lock:
            for job in self._jobs.values():
                if job.status == "running" and job.project == project and job.env_id == env_id:
                    return job
        return None

    def start(self, project, env_id, env_name, action, description, run):
        """Start `run(job)` on a daemon thread. `run` returns 0 on success."""
        job = Job(project, env_id, env_name, action, description)
        with self._lock:
            self._jobs[job.id] = job
            finished = [j for j in self._jobs.values() if j.status != "running"]
            if len(finished) > 100:
                for old in sorted(finished, key=lambda j: j.started)[: len(finished) - 100]:
                    del self._jobs[old.id]
        threading.Thread(target=self._run, args=(job, run), daemon=True).start()
        return job

    def _run(self, job, run):
        try:
            code = run(job)
            job.exit_code = 0 if code is None else code
        except Exception as e:
            job.exit_code = -1
            job.output.append(f"error: {e}")
        if job.status == "running":
            job.status = "success" if job.exit_code == 0 else "error"
            job.finished = time.time()

    def _watchdog(self):
        while True:
            time.sleep(30)
            now = time.time()
            with self._lock:
                running = [j for j in self._jobs.values() if j.status == "running"]
            for job in running:
                if now - job.started > JOB_TIMEOUT:
                    job.output.append(f"timed out after {JOB_TIMEOUT}s")
                    job.cancel = True
                    job.status = "error"
                    job.exit_code = -1
                    job.finished = time.time()
