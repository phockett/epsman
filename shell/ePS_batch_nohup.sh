#!/bin/bash

# Wrapper for ePS batch jobs for remote run with Fabric
# 23/10/19

echo Starting batch run with nohup

jobConfFile=$1
source $jobConfFile  # 23/08/20 Settings for local dirs now set here.

nohup /home/paul/ePS_stuff/jobs/ePS_batch_job.sh &
