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
def runJobs(self, runScript = None):
    """
    Basic wrapper for running ePS jobs remotely.

    Parameters
    ----------
    runScript : str, optional, default = None
        Set script to use on remote machine.
        If None, use self.runScript if set, or set as 'ePS_batch_nohup.sh'.

    """

    # Set default runner
    if runScript is None:
        if self.runScript is None:
            runScript = self.scpDefnRunners['batchNohup']   # Default to 'ePS_batch_nohup.sh'
            self.runScript = runScript
        else:
            runScript = self.runScript


    # With nohup
    # result = self.c.run('nohup ' + Path(self.hostDefn[self.host]['jobPath'], 'ePS_batch_job.sh').as_posix())

    # With nohup wrapper script to allow job to run independently of terminal.
    # Turn warnings off, and set low timeout, to ensure hangup... probably...
    # result = self.c.run(Path(self.hostDefn[self.host]['jobPath'], 'ePS_batch_nohup.sh').as_posix(), warn = True, timeout = 10)

    # 09/09/21 - updated to fix hangup issues & for new scripts (using .conf file supplied paths)
    # Note Fabric/ssh redirect output (see See https://stackoverflow.com/a/27600071)
    # Nohup file output now set in script as $jobConfFile.nohup.log
    # Further notes: https://github.com/phockett/epsman/issues/17#issuecomment-916352658
    cmd = f" {self.hostDefn[self.host]['genFile'].as_posix()} &> /dev/null &"
    result = self.c.run(Path(self.hostDefn[self.host]['scpdir'], runScript).as_posix() + cmd,
                        warn = True, timeout = 10, pty=False)

    # Log result for reference
    job.result = result

    if self.verbose:
        print(f"*** Running ePolyScat with {result} \n\n Host {self.host}. \nLog file: {self.hostDefn[self.host]['genFile'].as_posix()}.nohup.log \nOutput file dest: {self.hostDefn[self.host]['jobComplete']}")




# Tidy up job files
def tidyJobs(self, chkFlag = True, mvFlag = True, cpFlag = False, owFlag = None, tol = 0.05):
    """
    Check files for job completion (crudely). Move completed jobs to main job folder.

    Parameters
    ----------
    chkFlag : bool, optional, default = True
        Perform basic job file batch check for completeness.

    mvFlag : bool, optional, default = True
        Move files from completed to job dir if True.

    cpFlag : bool, optional, default = False
        Make a local copy of job files if True.

    owFlag : bool, optional, default = None
        Overwrite local files on get.
        If set to None, user will be prompted if local files exist.

    tol : float, optional, default = 0.05
        Tolerance (%age) for filesize tests.

    TODO
    ----
    - Lots of repetitive logic and boiler-plate here, should do better.
    - Better logic for check & move - at the moment all files are moved, even if they fail checks.

    """

    # Grab list of files from jobs completed folder - note choice of job root name here.
    # With genFile as root
    Result = self.c.run('ls ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '*.out', warn = True, hide = True)
    # With job.batch_job.orb as root.
    # Result = self.c.run('ls ' + Path(self.hostDefn[self.host]['jobComplete'], self.jobRoot).as_posix() + '*.out', warn = True, hide = True)
    self.fileList = Result.stdout.split()

    #*** Check number of files, .out should be equal to number of .inp, or 3x for stem check only.
    if (len(self.fileList)) == (self.Elist.shape[1]):
        print(f'Found {len(self.fileList)} files OK.')
        print("Output file list:")
        print(*self.fileList, sep = '\n')

    elif len(self.fileList) == 0:
        print(f'*** Warning: no files found in ' + self.hostDefn[self.host]['jobComplete'].as_posix())
        print('File checks and move will be skipped.')
        chkFlag = False
        mvFlag = False

    else:
        print(f'*** Warning: Expected {self.Elist.shape[1]}, found {len(self.fileList)} files.')
        print("Output file list:")
        print(*self.fileList, sep = '\n')


    #*** Check file sizes are (roughly) consistent
    if chkFlag:
        print('\nChecking files...')
        # Query with -ll to get file sizes
        Result = self.c.run('ls -ll ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '*.out', hide = True)
        tempList = Result.stdout.split()
        fSize = np.array(tempList[4:-1:9]).astype(int)  # Grab file sizes

        if fSize.min() < (fSize.max() - fSize.max() * tol):
            print(f'*** Warning: Output file sizes vary by >{tol*100}%.')
        else:
            print(f'File sizes OK, mean = {fSize.mean()} bytes')

        #*** Check files based on final line + compile runtime list.
        self.fTails = []
        # destTest = []
        for f in self.fileList:
            result = self.c.run('tail ' +  f, hide = True)
            # temp.append(result.stdout)
            # self.fTails.append(result.stdout.split('\n')[-2])

            # Version with error checking (will drop out in some cases otherwise)
            # Specifically, some files will have blank lines which will gives index errors at .split.
            try:
                self.fTails.append(result.stdout.split('\n')[-2])
            except IndexError as e:
                if e.args[0] != 'list index out of range':
                    raise
                # print(e.args[0])
                self.fTails.append(result.stdout)

            # result = self.c.run('[ -f "' + f + '" ]', warn = True, hide = True)  # Test for destination file, will return True if exists
            # destTest.append(result.ok)

        # Check for Finalize statement (could merge into above loop)
        fTest = [fLine.endswith("Finalize") for fLine in self.fTails]

        # Compile final lines from temp.
        # tailList = [fTail.split('\n')[-2] for fTail in temp]
        # tailList

        # Issue warning if abrupt file endings found
        self.fAbrupt = []
        if fTest.count(False):
            print(f'*** Warning: {fTest.count(False)} files end abruptly.')
            self.fAbrupt = list(compress(self.fileList, np.logical_not(np.array(fTest))))    # Slightly ugly... could also flip with list comprehension to avoid np use here.
            print(*self.fAbrupt, sep = '\n')

            # Rerun incomplete jobs?
            rerunFlag = input('Rerun failed jobs? (y/n) ')
            if rerunFlag == 'y':
                for f in self.fAbrupt:
                    self.c.run('mv ' + f[0:-4] + ' ' + self.hostDefn[self.host]['jobPath'].as_posix())

                print('Failed .inp files returned to ' + self.hostDefn[self.host]['jobPath'].as_posix())

        else:
            print('All files finalised OK.\n')
            print(*self.fTails, sep = '\n')

    #*** Move files to jobDir
    if mvFlag:
        print('\nMoving completed files on remote...')
        print('Checking destination files in ' + self.hostDefn[self.host]['jobDir'].as_posix())

        # Check for existing results
        destTest = []
        destFileList = []
        for f in self.fileList:
            destFile = Path(self.hostDefn[self.host]['jobDir'], Path(f).name)
            result = self.c.run('[ -f "' + destFile.as_posix() + '" ]', warn = True, hide = True)  # Test for destination file, will return True if exists
            destTest.append(result.ok)
            destFileList.append(destFile)

        # Issue warning if destination file(s) exist
        if destTest.count(True):
            print(f'*** Warning: {destTest.count(True)} files exist in destination dir.')
            # Print formatted list of existing items.
            print(*list(compress(self.fileList, (np.array(destTest)))), sep = "\n")    # Slightly ugly... could also flip with list comprehension to avoid np use here.

            # Check whether to continue moving files
            mv = input('Continue file move? (y/n) ')
            if mv == 'y':
                pass
            else:
                mvFlag = False

    # Move files
    if mvFlag:
        Result = self.c.run('mv ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '* ' + self.hostDefn[self.host]['jobDir'].as_posix())
        if Result.ok:
            print(Result.command + ' returned OK')


    #*** Make a local copy
    if cpFlag:
        print('\nMaking local copies...')
        # Check if local path exists, create if not.
        if not Path.is_dir(self.hostDefn['localhost']['systemDir']):
            Path.mkdir(self.hostDefn['localhost']['systemDir'])
            print('Created local dir ' + self.hostDefn['localhost']['systemDir'].as_posix())
        if not Path.is_dir(self.hostDefn['localhost']['jobDir']):
            Path.mkdir(self.hostDefn['localhost']['jobDir'], parents=True)  # Set parents to force full path creation.
            print('Created local dir ' + self.hostDefn['localhost']['jobDir'].as_posix())

        #*** Check for files in completed dir, or grab from final job dir

        # Check fileList has items, and they are still present - if so, copy from completed dir, otherwise try job dir and reset fileList.
        if len(self.fileList) > 0:
            Result = self.c.run('[ -f "' + self.fileList[0] + '" ]', warn = True, hide = True)  # Test for destination file, will return True if exist
            if Result.ok:
                print('Getting files from ' + self.hostDefn[self.host]['jobComplete'].as_posix())
        else:
            Result = self.c.run('ls ' + Path(self.hostDefn[self.host]['jobDir']).as_posix() + '/*.out', warn = True, hide = True)
            self.fileList = Result.stdout.split()
            print('Getting files from ' + self.hostDefn[self.host]['jobDir'].as_posix())
            print('Updated file list:')
            print(*self.fileList, sep = '\n')


        for f in self.fileList:
            # Set full local file path for writing, c.get issues dir complaint otherwise
            # Passing a dir as destination should work http://docs.fabfile.org/en/2.5/api/transfer.html#fabric.transfer.Transfer.get
            # ... maybe a formatting issue...?
            localPath = Path(self.hostDefn['localhost']['jobDir'], Path(f).name)

            # Check if file exists, and whether to overwrite (applies to all files)
            if Path.is_file(localPath) and owFlag is None:
                temp = input('*** Local files already exists, overwrite? (y/n) ')
                if temp == 'y':
                    owFlag = True
                else:
                    owFlag = False

            if owFlag:
                Result = self.c.get(f, local = localPath.as_posix())
                # if Result.ok:
                #     print(Result.command + ' returned OK')
                print(f'Got file {localPath}')



            # Result = self.c.run('ls ' + Path(self.hostDefn[self.host]['jobDir']).as_posix() + '/*.out', warn = True, hide = True)
            # fileList = Result.stdout.split()
            # print(*fileList, sep = '\n')
            #
            # for f  in fileList:
            #     Result = self.c.get(f, local = self.hostDefn['localhost']['jobDir'].as_posix())
            #     # if Result.ok:
            #     #     print(Result.command + ' returned OK')
            #



# Result = self.c.run('ls ' + Path(self.hostDefn[self.host]['jobComplete'], self.genFile.stem).as_posix() + '*.out')
#
# self.fileList = Result.stdout.split()
