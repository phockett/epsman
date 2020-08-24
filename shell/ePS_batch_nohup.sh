#!/bin/bash

# Wrapper for ePS batch jobs for remote run with Fabric
# 23/10/19

echo Starting batch run with nohup

nohup /home/paul/ePS_stuff/jobs/ePS_batch_job.sh &
