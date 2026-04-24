"""Scheduled job implementations registered in `app.services.scheduler`.

Each module exports a single top-level function named `run_*` that the
scheduler calls with no arguments. Jobs must:
    • Open and close their own DB sessions
    • Be safe to run concurrently with normal request traffic
    • Log their own start/finish — the scheduler wrapper also logs, but
      job-level logs add business-level context (users processed, alerts
      created, rows written)
    • Never raise out of the top-level function — the scheduler wrapper
      catches exceptions, but jobs should prefer to log-and-continue per
      user so one bad user doesn't starve the rest
"""
