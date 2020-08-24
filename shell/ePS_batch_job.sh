#!/bin/sh

# Script to run all ePS jobs in /jobs directory.  Output files are copied to Dropbox.
# 26/11/18 Modified to run test jobs, and also set paths on AntonJr
# 28/11/18 AntonJr version, env stuff now set directly in ePolyScat main script

# export LD_LIBRARY_PATH=/opt/pgi/linux86-64/10.0/lib
# export PATH=/opt/openmpi-1.4/bin/:$PATH

# ePSpath=/opt/ePolyScat.E3/bin/ePolyScat
# jobPath=/mnt/Scratch/ePS/jobs
# jobPath=/home/paul/ePS_stuff/jobs
# 23/08/20 - these are now set in calling script, or here.
jobConfFile=$1
source $jobConfFile  # 23/08/20 Settings for local dirs now set here. 

cd $jobPath

files=*.inp

# echo $files

for f in $files
do
  echo "Processing $f file..."
  # take action on each file. $f store current file name
  $ePSpath $jobPath/$f > $jobPath/$f.err

  # cat $f

  # cp $f.out ~/Dropbox/ePSjobs
  # cp $f.out /media/ext4-store/Dropbox/Dropbox/ePSjobs
  mv $f* ./completed

done
