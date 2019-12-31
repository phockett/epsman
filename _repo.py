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

#*** Functions to package job for repo

# Zenodo API interface
def initRepo(self):
    """Basic API calls for repo uploading"""

    return 'Not implemented'




# Package job files for repo


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
        self.getNotebookJobList()

    # Get header info and build dictionary
    # Currently using nbWriteHeader for this, will skip file writing if DOI not set.
    self.nbWriteHeader()

    # Reformat header data (as per notebook header) & set additional info.
    # This is written to file, and used for repo.
    for key in self.nbDetails:
        # Set var for packaging - set to True below.
        self.nbDetails[key]['pkg'] = False
        self.nbDetails[key]['procDate'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        if '***Missing' in self.nbDetails[key]['jobInfo'][2]:
            self.nbDetails[key]['jobText'] = None

        else:
            # Use function from nbHeaderWrite.py for consistency with notebook IO code.
            self.nbDetails[key]['jobText'] = constructHeader(self.nbDetails[key]['jobInfo'], self.nbDetails[key]['file'], self.nbDetails[key]['doi'])

            if int(self.nbDetails[key]['E'][-1]) > Emin:
                self.nbDetails[key]['pkg'] = True
                self.nbDetails[key]['repo'] = repo
                self.nbDetails[key]['repoInfo'] = self.initRepo()

    # Write to json file
    # Follow previous file IO scheme: set locally, and push to host
    self.jsonProcFile = self.hostDefn[self.host]['nbProcDir'].name + '_' + self.host + '_nbProc.json'

    # TODO: add some additional metadata here. Note Path() objects won't serialize.
    with open(Path(self.hostDefn['localhost']['wrkdir'], self.jsonProcFile).as_posix(), 'w') as f:
        json.dump(self.nbDetails, f, indent=2)

    # Push to host


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
