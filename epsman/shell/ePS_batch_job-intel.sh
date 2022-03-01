#!/bin/sh

# Script to run all ePS jobs in /jobs directory.  Output files are copied to Dropbox.
# 26/11/18 Modified to run test jobs, and also set paths on AntonJr
# 28/11/18 AntonJr version, env stuff now set directly in ePolyScat main script
# 19/03/21 Version for new build 3885d87

# export LD_LIBRARY_PATH=/opt/pgi/linux86-64/10.0/lib
# export PATH=/opt/openmpi-1.4/bin/:$PATH
# ePSpath=/opt/ePolyScat.E3/bin/ePolyScat

source /opt/ePolyScat.3885d87/ePS_v3885d87_env.sh
ePSpath=/opt/ePolyScat.3885d87/bin/ub-ifort/ePolyScat
# jobPath=/mnt/Scratch/ePS/jobs
jobPath=/home/paul/ePS/jobs

cd $jobPath

files=*.inp

# echo $files

for f in $files
do
  echo "Processing $f file..."
  # take action on each file. $f store current file name
  # 27/03/21 - changed from .err for new version.
  # Could alternatively add:  rename -v s/.err/.out/ *.err
  $ePSpath $jobPath/$f > $jobPath/$f.out

  # cat $f

  # cp $f.out ~/Dropbox/ePSjobs
  # cp $f.out /media/ext4-store/Dropbox/Dropbox/ePSjobs
  mv $f* ./completed

done
