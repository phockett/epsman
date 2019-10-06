"""
ePSman run functions
--------------------

03/10/19    First attempt.

"""

from pathlib import Path
import numpy as np
from itertools import compress

# Run a set of jobs
# Not sure if nohup will work as expected here...
def runJobs(self):
    """Basic wrapper for running ePS jobs remotely."""

    result = self.c.run('nohup ' + Path(self.hostDefn[self.host]['jobPath'], 'ePS_batch_job.sh').as_posix())


# Tidy up job files
def tidyJobs(self, mvFlag = True, tol = 0.05):
    """
    Check files for job completion (crudely). Move completed jobs to main job folder.

    Parameters
    ----------
    mvFlag : bool, optional, default = True
        Move files from completed to job dir if True.

    tol : float, optional, default = 0.05
        Tolerance (%age) for filesize tests.

    """

    # Grab list of files from jobs completed folder
    print("Output file list:")
    Result = self.c.run('ls ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '*.out')

    self.fileList = Result.stdout.split()

    #*** Check number of files, .out should be equal to number of .inp, or 3x for stem check only.
    if (len(self.fileList)) == (self.Elist.shape[1]):
        print(f'Found {len(self.fileList)} files OK.')
    else:
        print(f'*** Warning: Expected {self.Elist.shape[1]}, found {len(self.fileList)} files.')

    #*** Check file sizes are (roughly) consistent
    print('Checking files...')
    # Query with -ll to get file sizes
    Result = self.c.run('ls -ll ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '*.out', hide = True)
    tempList = Result.stdout.split()
    fSize = np.array(tempList[4:-1:9]).astype(int)  # Grab file sizes

    if fSize.min() < (fSize.max() - fSize.max() * tol):
        print(f'*** Warning: Output file sizes vary by >{tol*100}%.')

    #*** Check files based on final line + compile runtime list + check if destination exists.
    self.fTails = []
    destTest = []
    for f in self.fileList:
        result = self.c.run('tail ' +  f, hide = True)
        # temp.append(result.stdout)
        self.fTails.append(result.stdout.split('\n')[-2])

        result = self.c.run('[ -f "' + f + '" ]', warn = True, hide = True)  # Test for destination file, will return True if exists
        destTest.append(result.ok)

    # Check for Finalize statement (could merge into above loop)
    fTest = [fLine.endswith("Finalize") for fLine in self.fTails]

    # Compile final lines from temp.
    # tailList = [fTail.split('\n')[-2] for fTail in temp]
    # tailList

    # Issue warning if abrupt file endings found
    self.fAbrupt = []
    if fTest.count(False):
        print(f'*** Warning: {fTest.count(False)} files end abruptly.')
        self.fAbrupt = list(compress(self.fileList, (np.array(finalize))))    # Slightly ugly... could also flip with list comprehension to avoid np use here.
        print(self.fAbrupt)

        # Rerun incomplete jobs?
        rerunFlag = input('Rerun failed jobs? (y/n) ')
        if rerunFlag == 'y':
            for f in self.fAbrupt:
                self.c.run('mv ' + f[0:-4] + ' ' + self.hostDefn[self.host]['jobPath'].as_posix())

            print('Failed .inp files returned to ' + self.hostDefn[self.host]['jobPath'].as_posix())

    # Issue warning if destination file(s) exist
    if destTest.count(True):
        print(f'*** Warning: {destTest.count(True)} files exist in destination dir.')
        # Print formatted list of existing items.
        print(*list(compress(self.fileList, (np.array(destTest)))), sep = "\n")    # Slightly ugly... could also flip with list comprehension to avoid np use here.

        # Check whether to continue moving files
        mv = input('Continue file move? (y/n) ')
        if mv == 'y':
            mvFlag = True
        else:
            mvFlag = False


    #*** Move files to jobDir
    if mvFlag:
        Result = self.c.run('mv ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '* ' + self.hostDefn[self.host]['jobDir'].as_posix())
        if Result.ok:
            print(Result.command + ' returned OK')
