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

def runNotebooks(self, subDirs = True, template = 'nb-tpl-JR', scp = 'nb-sh-JR'):
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

    To do
    -----
    - Templates dir from module?  Should be able to get with inspect... not sure if templates included in install?

    """

    #*** Set env
    if 'nbProcDir' not in self.hostDefn[self.host].keys():
        self.hostDefn[self.host]['nbProcDir'] = self.hostDefn[self.host]['systemDir']

    print('*** Post-processing with Jupyter-runner for ', self.hostDefn[self.host]['nbProcDir'])

    if 'nbTemplateDir' not in self.hostDefn[self.host].keys():
        self.hostDefn[self.host]['nbTemplateDir'] = self.hostDefn[self.host]['scpdir']

    self.hostDefn[self.host]['nbTemplate'] = Path(self.hostDefn[self.host]['nbTemplateDir'], self.scrDefn[template])
    print('Using template: ', self.hostDefn[self.host]['nbTemplate'])

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
            if result.ok:
                print("Template file uploaded.")
            else:
                print("Failed to push file to host.")


    # Get job list
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
        # Actually no need to separate this as above, aside from that code was already tested.
        if subDirs:
            Result = self.c.run('ls -R ' + self.hostDefn[self.host]['nbProcDir'].as_posix() + ' | grep \.out$', warn = True, hide = True)
        else:
            Result = self.c.run('ls ' + self.hostDefn[self.host]['nbProcDir'].as_posix() + '*.out', warn = True, hide = True)

        self.jobList = Result.stdout.split()


    print(f'\nJob List (from {self.host}):')
    print(*self.jobList, sep='\n')


    #*** Write to file - set for local then push to remote.

    # Write params file for Jupyter Runner
    paramsFile = 'JR-params.txt'
    self.JRParams = Path(self.hostDefn['localhost']['wrkdir'], paramsFile)
    with open(self.JRParams, 'w') as f:
        for item in self.jobList:
            f.write(f"DATAFILE='{Path(self.hostDefn[self.host]['nbProcDir'], item).as_posix()}'\n")

    print(f'\nJupyter-runner params set in local file: {self.JRParams}')

    # Push to host
    print(f'Pushing file to host: {self.host}')
    logResult = self.c.put(self.JRParams.as_posix(), remote = self.hostDefn[self.host]['nbProcDir'].as_posix())

    #*** Run post-processing with Jupyter-runner script
    # Set number of processors == job size
    # TODO: add error checking and upper limit here, if proc > number of physical processors.
    proc = len(self.jobList)

    # With nohup wrapper script to allow job to run independently of terminal.
    # Turn warnings off, and set low timeout, to ensure hangup... probably...
    result = self.c.run(Path(self.hostDefn[self.host]['scpdir'], self.scrDefn[scp]).as_posix() + f" {self.hostDefn[self.host]['nbProcDir'].as_posix()} {proc} {paramsFile} {self.hostDefn[self.host]['nbTemplate'].as_posix()}", warn = True, timeout = 1)
