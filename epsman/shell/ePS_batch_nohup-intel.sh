#!/bin/bash

# Wrapper for ePS batch jobs for remote run with Fabric
# 23/10/19

echo Starting batch run with nohup

# nohup /home/paul/ePS/jobs/ePS_batch_job.sh &
# nohup /home/paul/ePS/jobs/ePS-3885d87_batch_job.sh &
nohup source /home/paul/ePS/jobs/ePS_batch_job-intel.sh &
