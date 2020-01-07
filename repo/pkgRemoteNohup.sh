#!/bin/bash

# Nohup wrapper for jobs packaging for remote run with Fabric
# 03/01/20
#
# Passed ags {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {self.hostDefn[self.host]['pkgDir'].as_posix()} {self.nbDetails['proc']['archLog']}

echo Starting pkg run with nohup

# Try setting env here, but may fail. Should be OK if set by Fabric call.
# conda activate ePSproc-v1.2

# stdoutTxt=$2/archLog_nohup.log
stdoutTxt=$6
nohup python $1 $2 $3 $4 $5 > $stdoutTxt &
