#!/bin/bash

# Wrapper for ePS batch jobs for remote run with Fabric
# 23/10/19

echo Starting batch run with nohup

jobConfFile=$1
source $jobConfFile  # 23/08/20 Settings for local dirs now passed to main script

# Currently set for jobPath, but should change to shell scrip repo?
nohup $scpdir/ePS_batch_job.sh $1 > $jobConfFile.nohup.log 2>&1 &
