#!/bin/bash

# Test Anaconda for shell script use & remote run with Fabric
# 29/12/19
#
# Pass args: (working dir) (workers) (parameter file) (template file)

# TO DO: test solutions from https://stackoverflow.com/questions/51469569/conda-and-python-shell-scripts

echo Testing Conda...

which python

# Set env - NOTE THIS MAY FAIL if default shell is not enabled for Conda
conda env list

# conda activate epsdev  # Fails on Bemo in shell srcipt (although works in terminal)
#             Still fails after running "sudo ln -s /home/femtolab/anaconda3/etc/profile.d/conda.sh /etc/profile.d/conda.sh" to set conda for all users.
# source activate epsdev  # This seems to work in script... BUT BOTH FAIL VIA FABRIC (on Bemo)

# Another method from https://stackoverflow.com/questions/34534513/calling-conda-source-activate-from-bash-script
# eval "$(conda shell.bash hook)"  # This also doesn't work on Bemo via Fabric, and throws conda errors when script run directly.
# conda activate epsdev

echo $PATH

conda env list
