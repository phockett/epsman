#!/bin/bash

# Nohup wrapper for jobs packaging for remote run with Fabric
# 09/01/20
#
# Passed ags:
# 1: {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['uploadNohup']).as_posix()}
# 2: {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['upload']).as_posix()}
# 3: {self.hostDefn[self.host]['nbProcDir']/self.jsonProcFile.name}
# 4: {ACCESS_TOKEN}",

echo Starting repo upload run with nohup

stdoutTxt=$2.nohup.log
nohup python $1 $2 $3 > $stdoutTxt &
