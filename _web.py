"""
ePSman web methods
-----------------------

Code for web management from Jupyter notebooks and ePS jobs.

"""

from pathlib import Path

def buildSite(self):
    """
    Run existing scripts to build index.rst and build HTML (Sphinx).

    NOTE: currently requires `git push` to be run manually.

    """

    # self.hostDefn[self.host]['webDir'] = Path(self.hostDefn[self.host]['home'], 'github/ePSdata')

    # with job.c.prefix(f"source {job.hostDefn[job.host]['condaPath']} webDev"):
    #   job.c.run(f"python /home/femtolab/python/epsman/web/buildSphinxHTML.py {job.hostDefn[job.host]['webDir'].as_posix()}")
    print(f"Building index in {self.hostDefn[self.host]['webDir']}")
    print(f"Running cmd: {Path(self.hostDefn[self.host]['webScpPath'], self.scpDefnWeb['buildIndex']).as_posix()} \
           {self.hostDefn[self.host]['webDir'].as_posix()}")

    with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
        self.c.run(f"python {Path(self.hostDefn[self.host]['webScpPath'], self.scpDefnWeb['buildIndex']).as_posix()} \
                    {self.hostDefn[self.host]['webDir'].as_posix()}")

    print(f"Building Sphinx HTML in {self.hostDefn[self.host]['webDir']}")
    with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
        self.c.run(f"{Path(self.hostDefn[self.host]['webScpPath'], self.scpDefnWeb['buildHTML']).as_posix()} \
                    {self.hostDefn[self.host]['webDir'].as_posix()}")

    print('HTML updated, run `git push` at command line to upload.')


def updateWebNotebookFiles(self):
    """
    Update web dir with new notebooks.

    """

    #*** Copy notebooks to web/source/mol

    # Check if (remote) dir exists
    test = self.c.run('[ -d "' + self.hostDefn[self.host]['webSystemDir'].as_posix() + '" ]', warn = True)  # Run remote command and return exit value without raising exit errors if dir doesn't exist

    # Alternatively can skip checking here and just use 'mkdir -p' below.

    # Build dir tree
    if test.ok == False:
        self.c.run('mkdir ' + self.hostDefn[self.host]['webSystemDir'].as_posix())
        print('Dir tree built, ', self.hostDefn[self.host]['webSystemDir'].as_posix())

    # Copy files to webDir
    for item in self.nbFileList:
        Result = self.c.run(f"cp {item} {self.hostDefn[self.host]['webSystemDir'].as_posix()}")

        if Result.ok:
            print(f"cp {item} {self.hostDefn[self.host]['webSystemDir'].as_posix()}")
        else:
            print(f"cp {item} {self.hostDefn[self.host]['webSystemDir'].as_posix()} fail")
