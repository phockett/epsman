#!/bin/bash

# Wrapper for Jupyter-runner batch jobs for remote run with Fabric
# 12/11/19
#
# Pass args: (working dir) (workers) (parameter file) (template file)

echo Starting Jupyter-runner batch run with nohup

# Set env
conda activate ePSproc-v1.2
cd $1

nohup jupyter-runner --overwrite --workers $2 --parameter-file=$3 --format notebook --allow-errors $4 &
