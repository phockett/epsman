"""
ePSman post-processing functions
--------------------------------

Functions for post-processing with ePSproc, including file sorting.

12/11/19    v1, based on test notebook ePSprocman_Jake_Jupyter-runner_tests_071119.ipynb
                http://localhost:8888/notebooks/ePS/aniline/epsman/ePSprocman_Jake_Jupyter-runner_tests_071119.ipynb


"""

# import inspect
from pathlib import Path

# This will work in notebook...  but not sure what modeule equivalent is.
# temp = Path(inspect.getfile(em))
# temp.parent
# temp2 = Path(temp.parent, 'templates')

def getNotebookJobList(self, subDirs=True, verbose = True):
    """Get job list from host - scan nbProcDir for ePS .out files.

    Mainly for use by `runNotebooks()`, but can call separately to reconstuct job list.

    Parameters
    ----------
    subDirs : bool, optional, default = True
        Include subDirs in processing.

    verbose : bool, optional, default = True
        Print jobList to screen.

    """

    if self.host == 'localhost':
        # Python version with Glob - ok for local jobs
        if subDirs:
            # List ePS files in jobDir, including subDirs
            self.jobList = list(self.hostDefn[self.host]['nbProcDir'].glob('**/*.out'))
        else:
            # Exclude subDirs
            self.jobList = list(self.hostDefn[self.host]['nbProcDir'].glob('*.out'))
    else:
        # Use remote shell commands
        self.jobList = self.getFileList(scanDir=self.hostDefn[self.host]['nbProcDir'].as_posix(), fileType = 'out', subDirs = subDirs, verbose = verbose)

    #     # Actually no need to separate this as above, aside from that code was already tested.
    #     if subDirs:
    #         # This works, but only returns file names, not full paths.
    #         # Result = self.c.run('ls -R ' + self.hostDefn[self.host]['nbProcDir'].as_posix() + ' | grep \.out$', warn = True, hide = True)
    #
    #         # From https://stackoverflow.com/questions/3528460/how-to-list-specific-type-of-files-in-recursive-directories-in-shell
    #         # Will be recursive if globstar active - may need to .sh this.
    #         # Globstar: shopt -s globstar
    #         Result = self.c.run(f"shopt -s globstar; ls -d -1 '{self.hostDefn[self.host]['nbProcDir'].as_posix()}/'**/* | grep \.out$", warn = True, hide = True)
    #     else:
    #         Result = self.c.run('ls ' + self.hostDefn[self.host]['nbProcDir'].as_posix() + '*.out', warn = True, hide = True)
    #
    #     self.jobList = Result.stdout.split()
    #
    # if verbose:
    #     print(f'\nJob List (from {self.host}):')
    #     print(*self.jobList, sep='\n')


def getNotebookList(self, subDirs = True, verbose = True):
    """Get notebook list from host - scan nbProcDir for ePS .ipynb files.

    Use to generate/reconstuct notebook list. If list is already set, old and new lists will be displayed, and user prompted for overwrite.

    Parameters
    ----------
    subDirs : bool, optional, default = True
        Include subDirs in processing.

    verbose : bool, optional, default = True
        Print jobList to screen.

    """

    if hasattr(self, 'nbFileList'):
        print('***Notebook file list already set:')
        print(*self.nbFileList, sep='\n')
        verbose = True  # Force verbose in this case.

    # Use remote shell commands
    nbFileList = self.getFileList(self.hostDefn[self.host]['nbProcDir'].as_posix(), fileType = 'ipynb', subDirs = subDirs, verbose = verbose)

    if hasattr(self, 'nbFileList'):
        overwriteFlag = input('Overwrite existing list with new? (y/n) ')
    else:
        overwriteFlag = 'y'

    if overwriteFlag == 'y':
        self.nbFileList = nbFileList

    # Alternatively, can set from existing jobList.
    # job.nbFileList = []
    # for item in job.jobList:
    #     newFile = Path(f"{Path(job.hostDefn[job.host]['nbProcDir'], Path(Path(item).stem).stem)}.ipynb")
    #     job.nbFileList.append(newFile)
    #
    # job.nbFileList


def setNotebookTemplate(self, template = 'nb-tpl-JR-v4'):
    """Set post-processing job template

    Mainly for use by `runNotebooks()`, but can call separately to reconstuct settings.

    Parameters
    ----------
    template : str, optional, default = 'nb-tpl-JR-v4'
        Jupyter notebook template file for post-processing.
        File list set in self.scrDefn, assumed to be in self.hostDefn[self.host]['scpdir'] unless self.hostDefn[self.host]['nbTemplateDir'] is defined.

    """

    if 'nbProcDir' not in self.hostDefn[self.host].keys():
        self.hostDefn[self.host]['nbProcDir'] = self.hostDefn[self.host]['systemDir']

    # print('*** Post-processing with Jupyter-runner for ', self.hostDefn[self.host]['nbProcDir'])

    if 'nbTemplateDir' not in self.hostDefn[self.host].keys():
        self.hostDefn[self.host]['nbTemplateDir'] = self.hostDefn[self.host]['scpdir']

    self.hostDefn[self.host]['nbTemplate'] = Path(self.hostDefn[self.host]['nbTemplateDir'], self.scrDefn[template])
    print('Set template: ', self.hostDefn[self.host]['nbTemplate'])

    # Test if template exists
    test = self.c.run('[ -f "' + self.hostDefn[self.host]['nbTemplate'].as_posix() + '" ]', warn = True)
    if test.ok:
        pass
    else:
        pFlag = input('Template missing on remote, push from local? (y/n) ')

        if pFlag == 'y':
            if 'nbTemplate' not in self.hostDefn['localhost'].keys():
                tplInput = input('Local template file not set, please specify: ')
                self.hostDefn['localhost']['nbTemplate'] = Path(tplInput)

            result = self.c.put(self.hostDefn['localhost']['nbTemplate'].as_posix(), remote = self.hostDefn[self.host]['nbTemplate'].as_posix())
            # if result.ok:
            #     print("Template file uploaded.")
            # else:
            #     print("Failed to push file to host.")
            print(f"Pushed notebook {result.remote} to {result.local}")
            # print(result)

def runNotebooks(self, subDirs = True, template = 'nb-tpl-JR-v4', scp = 'nb-sh-JR', multiEChunck = False):
    """
    Set up and run batch of ePSproc notebooks using Jupyter-runner.

    - Create job list for directory.
    - Set params list for jupyter-runner
    - Run on remote.

    Parameters
    ----------
    self : epsJob structure
        Contains path and job settings:

        - 'nbProcDir' used for post-processing.
            Defaults to 'systemDir' if not set.
        - 'templateDir' for Jupyter-runner template notebook.
            Defaults to 'scpdir' if not set.

    subDirs : bool, optional, default = True
        Include subDirs in processing.

    template : str, optional, default = 'nb-tpl-JR'
        Jupyter notebook template file for post-processing.
        File list set in self.scrDefn, assumed to be in self.hostDefn[self.host]['scpdir'] unless self.hostDefn[self.host]['nbTemplateDir'] is defined.

    scp : str, optional, default = 'nb-sh-JR'
        Script for running batch job on remote.
        TODO: should set scp and template relations in input dict.

    multiEChunck : bool, optional, default = False
        Set to true for consolidated handling of E-chuncked jobs. In this case, process batch of files in a single notebook.
        NOTE: this also requires a compatible template file.
        NOTE: no error checking here yet, should add checks rather than manual setting.

    To do
    -----
    - Templates dir from module?  Should be able to get with inspect... not sure if templates included in install?

    """

    #*** Set env
    # Set template
    self.setNotebookTemplate(template = template)
    print('*** Post-processing with Jupyter-runner for ', self.hostDefn[self.host]['nbProcDir'])
    print('Using template: ', self.hostDefn[self.host]['nbTemplate'])

    # Get jobList, ePS output files to run  template for.
    self.getNotebookJobList(subDirs = subDirs)

    #*** Write to file - set for local then push to remote.

    # Write params file for Jupyter Runner
    paramsFile = self.hostDefn[self.host]['nbProcDir'].name + '_' + self.host + '_JR-params.txt'
    self.JRParams = Path(self.hostDefn['localhost']['wrkdir'], paramsFile)
    with open(self.JRParams, 'w') as f:
        if multiEChunck:
            # For multi-E case, just pass first file
            f.write(f"DATAFILE='{Path(self.hostDefn[self.host]['nbProcDir'], self.jobList[0]).as_posix()}'\n")

        else:
            # For general case, pass list of files and execute one notebook/process per file.
            for item in self.jobList:
                f.write(f"DATAFILE='{Path(self.hostDefn[self.host]['nbProcDir'], item).as_posix()}'\n")

    print(f'\nJupyter-runner params set in local file: {self.JRParams}')

    # Push to host
    # print(f'Pushing file to host: {self.host}')
    # logResult = self.c.put(self.JRParams.as_posix(), remote = self.hostDefn[self.host]['nbProcDir'].as_posix())
    logResult = self.pushFile(self.JRParams, self.hostDefn[self.host]['nbProcDir'])

    #*** Run post-processing with Jupyter-runner script
    # Set number of processors == job size
    # TODO: add error checking and upper limit here, if proc > number of physical processors.
    proc = len(self.jobList)

    # With nohup wrapper script to allow job to run independently of terminal.
    # Turn warnings off, and set low timeout, to ensure hangup after jobs started (note: if too short, this will throw an error even if successful)
    # 07/03/20 - added conda wrapper.
    with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
        print(f"Running Notebooks with conda env {self.hostDefn[self.host]['condaEnv']}")
        print(f"CMD: {Path(self.hostDefn[self.host]['scpdir'], self.scrDefn[scp]).as_posix()} {self.hostDefn[self.host]['nbProcDir'].as_posix()} {proc} {paramsFile} {self.hostDefn[self.host]['nbTemplate'].as_posix()}")
        result = self.c.run(Path(self.hostDefn[self.host]['scpdir'], self.scrDefn[scp]).as_posix() + f" {self.hostDefn[self.host]['nbProcDir'].as_posix()} {proc} {paramsFile} {self.hostDefn[self.host]['nbTemplate'].as_posix()}", warn = True, timeout = 40)


# Tidy up auto-generated notebook files on remote.
def tidyNotebooks(self, rename = True, overrideFlag = False, cp = True, dryRun = False, multiEChunck = False):
    """
    Tidy up autogenerated notebooks from Jupyter-runner (from :py:func:`epsman._epsProc.py`).

    Assumes numerical ordering matches current self.jobList.

    Parameters
    ----------
    rename : bool, default = True
        Flag for file renaming to match ePS job file.

    overrideFlag : bool, optional, default = False
        Set to true to confirm/override autoset notebook names.

    cp : bool, default = True
        If true, make copy of notebook file in ePS job directory.

    dryRun : bool, default = False
        Set to True for dry run, print file commands but don't execute.

    multiEChunck : bool, optional, default = False
        Set to true for consolidated handling of E-chuncked jobs. In this case, process batch of files in a single notebook.
        NOTE: no error checking here yet, should add checks rather than manual setting.

    TODO
    -----
    - Add options for tidy/move/delete processing results from original dirs.

    """

    # Tidy up output notebooks
    print("*** Tidying processed notebooks\n")

    if dryRun:
        print("*** Dry run only")

    # Currently set to move to item (job) dir.
    self.nbFileList = []
    self.nbFileFail = []

    if multiEChunck:
        jobs = [self.genFile.stem]  # Single output
    else:
        jobs = self.jobList  # Notebook per job


    for n, item in enumerate(jobs):
        # Set file name for jupyter-runner output (full path)
        JRFile = f"{Path(self.hostDefn[self.host]['nbProcDir'], self.hostDefn[self.host]['nbTemplate'].stem)}_{n+1}.ipynb"
        if multiEChunck:
            newFile = f"{Path(self.hostDefn[self.host]['nbProcDir'], Path(item))}.ipynb"
        else:
            newFile = f"{Path(self.hostDefn[self.host]['nbProcDir'], Path(Path(item).stem).stem)}.ipynb"

        # Override default naming scheme if desired.
        if overrideFlag:
            test = input(f"Suggested filename: {newFile} (y/n)")

            if test == 'y':
                pass
            else:
                newName = input("New filename (name only)? ")
                newFile = f"{Path(self.hostDefn[self.host]['nbProcDir'], newName}.ipynb"
                print(f"Set filename: {newFile}")



# TODO: change logic here to set nbFileList in cases where files are already renamed - NOW set independently by getNotebookList()

        # Check file exists
        result = self.c.run('[ -f "' + JRFile + '" ]', warn = True, hide = True)  # Test for destination file, will return True if exists
        destTest = result.ok

        if destTest:
            self.nbFileList.append(newFile)

            if rename:
                if not dryRun:
                    Result = self.c.run(f"mv {JRFile} {newFile}")
                if dryRun or Result.ok:
                    print(f"mv {JRFile} {newFile}")
                else:
                    print(f"mv {JRFile} {newFile} fail")


            if cp:
                if not dryRun:
                    Result = self.c.run(f"cp {newFile} {Path(item).parent}")
                if dryRun or Result.ok:
                    print(f"cp {newFile} {Path(item).parent}")
                else:
                    print(f"cp {newFile} {Path(item).parent} fail")

        else:
            print(f"*** Missing notebook {JRFile} -> {newFile}")
            self.nbFileFail.append([JRFile, newFile])

    print(f'\nProcessed Notebook List:')
    print(*self.nbFileList, sep='\n')

    if self.nbFileFail:
        print(f'\n\nMissing Notebook List:')
        print(*self.nbFileFail, sep='\n')


# Pull auto-generated notebook files from remote
def getNotebooks(self):
    """Get remote notebook files."""

    print('*** Pulling notebook files from remote')
    for item in self.nbFileList:
        result = self.c.get(item)
        print(f"Pulled notebook {result.remote} to {result.local}")

# Kill all running notebooks on remote
def killNotebooks(self, jobName = "ZMQbg/1"):
    """
    Run pkill on remote to stop running notebooks.

    Parameters
    -----------
    jobName : str, default "ZMQbg/1"
        Jobs to kill, will be passed to remote machine as `pkill {jobName}`.
        Default corresponds to background tasks started with nohup script.

    """

    print(f'\n***Killing remote jobs {jobName}')
    # Kill all jobs on remote...
    result = self.c.run(f'pkill {jobName}')

    if result.ok:
        print("OK")
