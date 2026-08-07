import threading
import time
import traceback
import uuid

_jobs = {}
_lock = threading.Lock()


def create_job():
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "status": "pending",
            "error": None,
            "output_path": None,
            "created_at": time.time(),
        }
    return job_id


def get_job(job_id):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _update_job(job_id, **fields):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def run_in_background(job_id, func, *args, **kwargs):
    def _worker():
        _update_job(job_id, status="running")
        try:
            output_path = func(*args, **kwargs)
            _update_job(job_id, status="done", output_path=str(output_path))
        except Exception as exc:
            traceback.print_exc()
            _update_job(job_id, status="error", error=str(exc))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
