#!/bin/bash

# Wrapper for nbHeaderPost.py
# Post-processing script for notebook headers.
# 29/12/19
#
# Pass args: (script path) (notebook path) (doi)


# TROUBLESHOOTING....
# whoami

# Enable shell for conda - this will fail if install dir is different to that set here.
# THIS doesn't seem to make any difference.
# echo ". ~/anaconda3/etc/profile.d/conda.sh" >> ~/.bashrc

# Set env - currently machine dependent!
# conda activate ePSproc-v1.2
# conda activate epsdev
source activate epsdev
conda env list
which python
echo $1 $2

# /home/femtolab/anaconda3/envs/epsdev/bin/python /home/femtolab/python/epsman/nbHeaderPost.py $1 $2
python /home/femtolab/python/epsman/nbHeaderPost.py $1 $2
