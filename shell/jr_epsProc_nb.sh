#!/bin/bash

# Wrapper for Jupyter-runner batch jobs for remote run with Fabric
# 12/11/19
#
# Pass args: (working dir) (workers) (parameter file) (template file)

echo Starting Jupyter-runner batch run with nohup

# Set env - NOTE THIS MAY FAIL if default shell is not enabled for Conda
# conda activate ePSproc-v1.2
# Now set in Fabric call, e.g.
# with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
cd $1

nohup jupyter-runner --overwrite --workers $2 --parameter-file=$3 --format notebook --allow-errors $4 &
