"""Vercel FastAPI entry point for the Gridyn research service."""

import os

# Vercel functions do not provide the semaphore needed by joblib's optional
# multiprocessing backend. Gridyn's tree forecast uses serial joblib work.
if os.environ.get("VERCEL"):
    os.environ.setdefault("JOBLIB_MULTIPROCESSING", "0")
    # Pyomo upgrades its output-capture lock when multiprocessing is imported.
    # This function uses no child processes, so retain a thread lock instead.
    import multiprocessing
    import threading

    original_lock = multiprocessing.Lock
    multiprocessing.Lock = threading.Lock
    try:
        import pyomo.common.dependencies
    finally:
        multiprocessing.Lock = original_lock

from energy_lab.api.app import app
