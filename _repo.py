"""
ePSman repo interfacing
-----------------------

Code for:
- Scanning ePS results directories
- Scanning ePSproc notebooks
- Catalogue & sort
- Package and upload to repo

Aim to do this as a stand-alone task, so grab info from files rather than existing epsman job.

To do:
- Output details to database
- HTML page generation from packaged notebooks

10/12/19    Init... plan to test for OSF, Figshare and Zenodo.

For dev codes see notebooks:
- http://localhost:8888/notebooks/python/epsman/tests/Notebook_mod_testing_161219.ipynb
- http://localhost:8888/notebooks/python/epsman/tests/Repo_pkg_tests_181219.ipynb
- http://localhost:8888/notebooks/python/epsman/repo/Zenodo_API_tests_Dec2019.ipynb

"""
# Imports
import json
import datetime
from pathlib import Path
from ._util import parseLineDigits
from .repo.nbHeaderPost import constructHeader
from .repo.pkgFiles import setJobRoot

# Import from /repo
# from repo.pkgFiles import

#*** Functions to package job for repo

# Zenodo API interface
def initRepo(self):
    """Basic API calls for repo uploading"""

    return 'Not implemented'


# Package job files for repo
# May need to do this as a separate local function for Fabric calls?
# TODO:
# - Add optional elec structure file to pkg.
# - Add this function & integrate with epsman code
# - Check if arch exists before running
# - Consider moving main loop to remote code - what are the dependecies here?  Should just be able to pass a dir path, or maybe write list to file and push to host?
def buildArch(self, localLoop = True, dryRun = True):
    """
    Build archives/packages for job.

    Wrapper for repo/pkgFiles.py, which runs on host machine.

    Parameters
    ----------
    localLoop : bool, default = True
        Run version of code with job loop on local machine - one Fabric call per job to pkg.
        This is useful for dryRun, but not for packaging large dirs on remote.
        If false, run all code on remote.

    dryRun : bool, default = True
        Get fileLists to be archived, but don't build.
        Most useful for localLoop = True case.

    To do
    -----
    - Search logic for electronic structure files.

    """

    # make pkg dir on host
    print(f"\n***Building archives for {self.hostDefn[self.host]['nbProcDir']}")
    if dryRun:
        print("***DryRun only")
    else:
        self.c.run('mkdir -p ' + self.hostDefn[self.host]['pkgDir'].as_posix())

    print(f"Pkg dir: {self.hostDefn[self.host]['pkgDir']}")

    # Loop over Notebooks locally and package corresponding files.
    # Useful for testing, but not good for large jobs.
    if localLoop:
        zipList = []
        failList = []

        # for item in self.nbFileList:  # Local file list, from nbFileList
        for key in self.nbDetails:
            # Skip metadata key if present
            if key!='proc':
                # Job keys
                item = Path(self.nbDetails[key]['file'])
                # dirBase = Path(self.nbDetails[key]['file']).parent  # Could set dirBase here instead of nbProcDir

                # if self.hostDefn[self.host]['jobSchema'] == '2016':
                #     jRoot = item.stem.rsplit(sep='_', maxsplit=3)
                #     self.nbDetails[key]['jRoot'] = f"{jRoot[1]}_{jRoot[2]}_{jRoot[3]}"
                # elif self.hostDefn[self.host]['jobSchema'] == '2019':
                #     jRoot = item.stem.rsplit(sep='_', maxsplit=2)
                #     self.nbDetails[key]['jRoot'] = f"{jRoot[1]}_{jRoot[2]}"

                # Define using function  in pkgFiles.py
                jRoot = setJobRoot(item, self.hostDefn[self.host]['jobSchema'])
                self.nbDetails[key]['jRoot'] = jRoot

                archName = Path(self.hostDefn[self.host]['pkgDir'], item.stem + '.zip')

                # Generate filelist - based on code in getNotebookJobList()
                # Glob for files matching job, inc. subdirs, skip any zip files found.
            #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/* | grep {jRoot[1]}_{jRoot[2]}", warn = True, hide = True)
            #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/* | grep --include=${jRoot[1]}_{jRoot[2]} --exclude=pkg", warn = True, hide = True)
            #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/*[!zip] | grep {jRoot[1]}_{jRoot[2]}", warn = True, hide = True)
            #     fileOut = shutil.make_archive('/home/femtolab/temp/shutiltest', 'zip', '/home/femtolab/python/epsman/repo/')

                # For remote run, call python code on host machine,
                # Do this once per item in nbFileList, and grab output.
                with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
                    # job.c.run('/home/femtolab/python/epsman/shell/conda_test.sh')  # Still have issues here, due to code in script
                    # result = job.c.run('python /home/femtolab/python/epsman/nbHeaderPost.py ' + f'{fileIn} {doi}')
                    # result = job.c.run('python /home/femtolab/python/epsman/repo/pkgFiles.py' + f" {job.hostDefn[job.host]['pkgDir'].as_posix()} {jRoot[1]}_{jRoot[2]} {archName}")
                    result = self.c.run(f"python {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} \
                                        {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {archName} {self.hostDefn[self.host]['jobSchema']} {jRoot}")

                if dryRun:
                    self.nbDetails[key]['result'] = result
                    self.nbDetails[key]['pkgFileList'] = result.stdout.splitlines()
                else:
                    self.nbDetails[key]['archName'] = archName
                    self.nbDetails[key]['archBuilt'] = result.stdout

    else:
        # For remote run, call python code on host machine,
        # In this case, do this for full build dir, and loop on remote machine.
        with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
            # Vanilla version - will wait for script execution
            # result = self.c.run(f"python {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {self.hostDefn[self.host]['pkgDir'].as_posix()}")

            # Nohup version to allow for lengthy remote
            result = self.c.run(f"{Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkgNohup']).as_posix()} {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} \
                                        {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {self.hostDefn[self.host]['pkgDir'].as_posix()} {self.hostDefn[self.host]['jobSchema']}",
                                        warn = True, timeout = 10)

        # TODO: Logic for handling stdout here.
        # May want to change to writing to remote file for nohup use.
        # NOW set in pkgRemoteNohup.sh, writes to local log file. self.hostDefn[self.host]['nbProcDir']/archLog_nohup.log
        # Use getArchLogs() to retrieve

        return result


def cpESFiles(self, dryRun = True, eSourceDir = None):
    print('\n***Copying electronic structure files')
    if dryRun:
        print('***Dry run only')

    for key in self.nbDetails:
        # Skip metadata key if present
        if key!='proc':
            # Check and set electronic structure file for packaging.
            if '***Missing' in self.nbDetails[key]['jobInfo'][2]:
                pass
            else:
                if eSourceDir is not None:
                    # Copy electronic structure files to package using supplied path
                     fileName = Path(self.nbDetails[key]['jobInfo'][-1].split()[-1].strip("'"))
                     self.nbDetails[key]['elecStructure'] = Path(eSourceDir, fileName.name).as_posix()

                else:
                    # Copy electronic structure files to package, based on full path from original job
                    self.nbDetails[key]['elecStructure'] = self.nbDetails[key]['jobInfo'][-1].split()[-1].strip("'")

                checkList = self.checkFiles(self.nbDetails[key]['elecStructure'])

                # Make job dir and copy file(s)
                eDir = Path(self.hostDefn[self.host]['nbProcDir'], f"{self.nbDetails[key]['jRoot']}_elec_struc")

                # If file exists, copy to job dir
                if checkList[0] and not dryRun:
                    result = self.c.run('mkdir -p ' + eDir.as_posix())
                    result = self.c.run(f"cp {self.nbDetails[key]['elecStructure']} {eDir}")

                else:
                    print(f"Skipping command: cp {self.nbDetails[key]['elecStructure']} {eDir}")
                # Path(job.nbDetails[2]['elecStructure'][0]).with_suffix('.inp')


# Get arch logs
# Use this for cases where large pkg jobs were left running on remote.
# May also want to run archive checks independently here?
def getArchLogs(self):
    """Get archive logs from host (for remote run with nohup)"""

    # Implement checkFiles() for archs?

    # Pull log file
    if self.nbDetails['proc']['archLog'] is not None:
        result = self.c.get(self.nbDetails['proc']['archLog'])
        print(f"Pulled archive creation log {result.remote} to {result.local}")
    else:
        print(f"Archives not yet written.")


# Get E points from jobInfo
def getEpoints(jobInfo):
    """Parse notebook header text for energy points"""
    for line in jobInfo:
        if line.strip().startswith("E="):
            print(line)
            P=line

    return parseLineDigits(P)

# Build notebook list & info
def buildUploads(self, Emin = 3, repo = 'Zenodo', dryRun = False, eStructCp = True, eSourceDir = None, nbSubDirs = False, schema = '2016'):
    """
    Build notebook file list + details + archives.

    Note this will process & package all jobs in nbProcDir.

    Parameters
    ----------
    Emin : int, optional, default = 3
        Minimum number of E points for job packaging.

    repo : str, default = 'Zenodo'
        Set repo for uploading. Currenly only supports Zenodo.

    dryRun : bool, default = False
        Set to True to get file info etc, but skip writing archives.

    eStructCp : bool, default = True
        Copy electronic structure file(s) to job dirs.
        Currently only set for single file, should add search logic here.

    eSourceDir : str or path object, optional, default = None
        If supplied, use this as the source path for electronic structure files instead of original job definition.

    nbSubDirs : bool, default = False
        Search for notebooks in subdirs.
        Default is to search in root dir only, as set in self.hostDefn[self.host]['nbProcDir']
        Note this is only used if reconstructing nbFileList.

    """

    # Check if notebook file list is set, set if missing.
    if not hasattr(self, 'nbFileList'):
        self.getNotebookList(subDirs = nbSubDirs)

    # Get header info and build dictionary
    # Currently using nbWriteHeader for this, will skip file writing if DOI not set.
    self.nbWriteHeader()

    # Pkg dry run - use this to create file list etc.
    # This will be called again later to build archives for upload.
    self.buildArch()

    # If eStructCp = True this will copy electronic structure files to job dirs.
    # If dryRun = True will just display commands.
    if eStructCp:
        self.cpESFiles(dryRun = dryRun, eSourceDir =  eSourceDir)

    # Reformat header data (as per notebook header) & set additional info.
    # This is written to file, and used for repo.
    for key in self.nbDetails:
        # Skip metadata key if present
        if key!='proc':
            # Set var for packaging - set to True below.
            self.nbDetails[key]['pkg'] = False

            if '***Missing' in self.nbDetails[key]['jobInfo'][2]:
                self.nbDetails[key]['jobText'] = None

            else:
                # Use function from nbHeaderWrite.py for consistency with notebook IO code.
                # Note that jobInfo here has additional lines from version in nbHeaderWrite.py, so drop start.
                self.nbDetails[key]['jobText'] = constructHeader(self.nbDetails[key]['jobInfo'][2:], self.nbDetails[key]['file'], self.nbDetails[key]['doi'])

                if int(self.nbDetails[key]['E'][-1]) > Emin:
                    self.nbDetails[key]['pkg'] = True
                    self.nbDetails[key]['repo'] = repo
                    self.nbDetails[key]['repoInfo'] = self.initRepo()




    # Set dir metadata
    self.nbDetails['proc'] = {'host':self.host,
                              'nbProcDir':self.hostDefn[self.host]['nbProcDir'].as_posix(),
                              'date':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                              'archLog':None
                              }

    # Pkg files - build archives for all jobs on remote
    if not dryRun:
        print('\n***Running archive creation on remote.')
        result = self.buildArch(localLoop = False, dryRun = dryRun)
        self.nbDetails['proc']['archLog'] = f"{Path(self.hostDefn[self.host]['nbProcDir'], 'archLog_nohup.log').as_posix()}"

    # if result.stduout ==
    # print(result.stdout)

    # Write to json file
    # Follow previous file IO scheme: set locally, and push to host
    jsonProcFile = self.hostDefn[self.host]['nbProcDir'].name + '_' + self.host + '_nbProc.json'
    self.jsonProcFile = Path(self.hostDefn['localhost']['wrkdir'], jsonProcFile)

    # Write to JSON.  Note Path() objects won't serialize.
    with open(self.jsonProcFile.as_posix(), 'w') as f:
        json.dump(self.nbDetails, f, indent=2)

    print(f'\n***nbDetails written to local JSON file: {self.jsonProcFile}')

    # Push to host
    pushResult = self.pushFile(self.jsonProcFile, self.hostDefn[self.host]['nbProcDir'])


# Processed job file header creation
def nbWriteHeader(self):
    """
    Read job info and set header cell for ePSproc Notebooks for repo upload.
    """
    # Init empty dictionary if not set, or use existing details.
    if not hasattr(self, 'nbDetails'):
        self.nbDetails = {}
        writeDict = True
    else:
        writeDict = False

    # Load notebook, write header & save
    # NOTE - this requires doi to be preset.
    for n, nb in enumerate(self.nbFileList):
        # Register job with repo - to do.
        # For now just check for doi setting here, pass None if not set (to read header only).
        if n in self.nbDetails.keys():
            if 'doi' in self.nbDetails[n]:
                doi = self.nbDetails[n]['doi']
        else:
            doi = None

        # Run python script for notebook post-process, with Anaconda env set (requires python3 and nbformat)
        # See https://stackoverflow.com/questions/54268390/how-to-deploy-my-conda-env-to-a-vps-using-fabric-or-othervise
        with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
            # job.c.run('/home/femtolab/python/epsman/shell/conda_test.sh')  # Still have issues here, due to code in script
            # result = job.c.run('python /home/femtolab/python/epsman/nbHeaderPost.py ' + f'{fileIn} {doi}')
            result = self.c.run('python ' + Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['nb-post-doi']).as_posix() + f' {nb} {doi}')

        # Store job info locally
        if writeDict:
            jobInfo = result.stdout.splitlines()

            if '***Missing' in jobInfo[2]:
                Elist = None
            else:
                Elist = getEpoints(jobInfo)

            self.nbDetails.update({n:{'file':nb,  # Path(nb),  # Setting Path object here gives issues with json seralization later!
                                     'doi':doi,
                                     'jobInfo':jobInfo,
                                     'E':Elist
                                    }})


#*** Repo uploader

# Upload package
