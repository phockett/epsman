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
from .nbHeaderPost import constructHeader

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
def buildArch(self, localLoop = True):
    """
    Build archives/packages for job.

    Wrapper for repo/pkgFiles.py, which runs on host machine.

    """

    # make pkg dir on host
    print(f"***Building archives for {self.hostDefn[self.host]['pkgDir']}")
    self.c.run('mkdir -p ' + job.hostDefn[job.host]['pkgDir'].as_posix())

    # Loop over Notebooks locally and package corresponding files.
    # Useful for testing, but not good for large jobs.
    if localLoop:
        zipList = []
        failList = []
        for item in self.nbFileList:  # Local file list

            # Job keys
            item = Path(item)
            jRoot = item.stem.rsplit(sep='_', maxsplit=2)
            archName = Path(self.hostDefn[self.host]['pkgDir'], item.stem + '.zip')

            # Generate filelist - based on code in getNotebookJobList()
            # Glob for files matching job, inc. subdirs, skip any zip files found.
        #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/* | grep {jRoot[1]}_{jRoot[2]}", warn = True, hide = True)
        #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/* | grep --include=${jRoot[1]}_{jRoot[2]} --exclude=pkg", warn = True, hide = True)
        #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/*[!zip] | grep {jRoot[1]}_{jRoot[2]}", warn = True, hide = True)
        #     fileOut = shutil.make_archive('/home/femtolab/temp/shutiltest', 'zip', '/home/femtolab/python/epsman/repo/')

            # For remote run, call python code on host machine,
            # Do this once per item in nbFileList (although could set loop on remote too). Might get issues for large archives...?
            with job.c.prefix(f"source {job.hostDefn[job.host]['condaPath']} {job.hostDefn[job.host]['condaEnv']}"):
                # job.c.run('/home/femtolab/python/epsman/shell/conda_test.sh')  # Still have issues here, due to code in script
                # result = job.c.run('python /home/femtolab/python/epsman/nbHeaderPost.py ' + f'{fileIn} {doi}')
                result = job.c.run('python /home/femtolab/python/epsman/repo/pkgFiles.py' + f" {job.hostDefn[job.host]['pkgDir'].as_posix()} {jRoot[1]}_{jRoot[2]} {archName}")

    else:
        with job.c.prefix(f"source {job.hostDefn[job.host]['condaPath']} {job.hostDefn[job.host]['condaEnv']}"):
            # job.c.run('/home/femtolab/python/epsman/shell/conda_test.sh')  # Still have issues here, due to code in script
            # result = job.c.run('python /home/femtolab/python/epsman/nbHeaderPost.py ' + f'{fileIn} {doi}')
            result = job.c.run('python /home/femtolab/python/epsman/repo/pkgFiles.py' + f" {job.hostDefn[job.host]['pkgDir'].as_posix()} {jRoot[1]}_{jRoot[2]} {archName}")


# Get E points from jobInfo
def getEpoints(jobInfo):
    """Parse notebook header text for energy points"""
    for line in jobInfo:
        if line.strip().startswith("E="):
            print(line)
            P=line

    return parseLineDigits(P)

# Build notebook list & info
def buildUploads(self, Emin = 3, repo = 'Zenodo'):
    """Build notebook file list + details & sort.

    Parameters
    ----------
    Emin : int, optional, default = 3
        Minimum number of E points for job packaging.

    repo : str, default = 'Zenodo'
        Set repo for uploading. Currenly only supports Zenodo.

    """

    # Check if notebook file list is set, set if missing.
    if not hasattr(self, 'nbFileList'):
        self.getNotebookList()

    # Get header info and build dictionary
    # Currently using nbWriteHeader for this, will skip file writing if DOI not set.
    self.nbWriteHeader()

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
                              'date':datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

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
            result = self.c.run('python ' + Path(self.hostDefn[self.host]['scpdir'], self.scrDefn['nb-post-doi']).as_posix() + f' {nb} {doi}')

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
