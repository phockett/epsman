"""
ePSman run functions
--------------------

03/10/19    First attempt.

"""

from pathlib import Path

# Run a set of jobs
# Not sure if nohup will work as expected here...
def runJobs(self):
    """Basic wrapper for running ePS jobs remotely."""

    result = self.c.run('nohup ' + Path(self.hostDefn[self.host]['jobPath'], 'ePS_batch_job.sh').as_posix())
