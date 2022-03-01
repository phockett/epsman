#!/bin/bash

# Wrapper for ePS batch jobs for remote run with Fabric
# 09/09/21  v2, with updated output file.
# 23/10/19  v1

echo Starting batch run with nohup

jobConfFile=$1
source $jobConfFile  # 23/08/20 Settings for local dirs now passed to main script

# For intel case need to set env - NOTE THIS SHOULD BE PASSED (via jobConfFile)
source /opt/ePolyScat.3885d87/ePS_v3885d87_env.sh

# Currently set for jobPath, but should change to shell scrip repo?
nohup $scpdir/ePS_batch_job.sh $1 > $jobConfFile.nohup.log 2>&1 &
